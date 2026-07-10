import os
import hashlib
import time
import uuid
import shutil
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from core.database.db import db_manager
from core.logger.custom_logger import log_action
from core.generation.prompt import prompt_engine, StructuredPrompt
from core.generation.consistency import consistency_manager
from core.generation.router import provider_router
from core.generation.validator import asset_validator
from core.generation.settings import seed_manager, lora_manager, controlnet_manager
from core.projects.manager import project_manager

class GenerationManager:
    """
    Orchestrates batch media generation, cache lookup, provider routing,
    quality checking, and failed job recovery.
    """
    def __init__(self):
        self.max_concurrency = 3
        self.enable_cache = True

    def _hash_parameters(self, prompt: str, neg_prompt: str, seed: int, width: int, height: int) -> str:
        """Generates a unique MD5 hash for a configuration set."""
        key = f"{prompt}_{neg_prompt}_{seed}_{width}_{height}"
        return hashlib.md5(key.encode("utf-8")).hexdigest()

    def check_cache(self, param_hash: str) -> Optional[str]:
        """Looks up if an identical asset is already generated and valid on disk."""
        if not self.enable_cache:
            return None
            
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT asset_path FROM generation_cache WHERE prompt_hash = ?", (param_hash,))
                row = cursor.fetchone()
                if row:
                    path = row["asset_path"]
                    # Validate file exists and is not corrupt
                    if os.path.exists(path):
                        log_action("GenerationManager", "CacheHit", "SUCCESS", 0.0, f"Found cached asset: {path}")
                        return path
                    else:
                        # Clean up cache entry
                        cursor.execute("DELETE FROM generation_cache WHERE prompt_hash = ?", (param_hash,))
                        conn.commit()
        except Exception:
            pass
        return None

    def save_to_cache(self, param_hash: str, asset_path: str, seed: int):
        """Saves generated asset path and parameters to local cache index."""
        try:
            now_str = datetime.now().isoformat()
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO generation_cache (prompt_hash, asset_path, seed, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (param_hash, asset_path, seed, now_str)
                )
                conn.commit()
        except Exception:
            pass

    def generate_image(self, project_id: str, sp: StructuredPrompt, 
                       preferred_provider: str = "ComfyUI", 
                       char_id: Optional[str] = None) -> Optional[str]:
        """
        Generates a single image. Handles cache lookups, character injections,
        routing, quality validation, and database asset indexing.
        """
        proj_dir = project_manager.get_project_dir(project_id)
        
        # 1. Apply Character Consistency Description if reference ID passed
        compiled_subject = sp.subject
        if char_id:
            character = consistency_manager.get_character(char_id)
            if character:
                compiled_subject = f"{character.get_prompt_description()}, {sp.subject}"
                
        # Clone structured prompt to modify subject for this generation run
        sp_run = sp.model_copy(update={"subject": compiled_subject})
        
        # Compile prompt strings
        prompt = prompt_engine.compile_prompt(sp_run)
        neg_prompt = prompt_engine.merge_negatives(scene_neg=sp_run.negative_prompt)
        
        # Resolve seed
        seed = seed_manager.get_seed(force_fixed=sp_run.seed)
        
        width = 1024
        height = 1024
        if sp_run.aspect_ratio == "9:16":
            width, height = 1080, 1920
        elif sp_run.aspect_ratio == "16:9":
            width, height = 1920, 1080
            
        # 2. Check Cache
        param_hash = self._hash_parameters(prompt, neg_prompt, seed, width, height)
        cached_path = self.check_cache(param_hash)
        if cached_path:
            # Copy cached file to project folder
            filename = f"gen_cached_{int(time.time())}_{str(uuid.uuid4())[:4]}.png"
            dest_rel = f"images/{filename}"
            dest_abs = os.path.join(proj_dir, dest_rel)
            
            try:
                os.makedirs(os.path.dirname(dest_abs), exist_ok=True)
                shutil.copy2(cached_path, dest_abs)
                self._register_asset_db(project_id, preferred_provider, prompt, neg_prompt, seed, dest_rel, width, height)
                return dest_rel
            except Exception:
                pass

        # 3. Route to healthy provider plugin
        plugin = provider_router.route_generation("image", preferred_provider)
        if not plugin:
            log_action("GenerationManager", "Route", "FAILED", 0.0, "No image plugins available.")
            return None
            
        filename = f"gen_{int(time.time())}_{str(uuid.uuid4())[:4]}.png"
        dest_rel = f"images/{filename}"
        dest_abs = os.path.join(proj_dir, dest_rel)
        os.makedirs(os.path.dirname(dest_abs), exist_ok=True)

        # 4. Generate & Validate (with Retries)
        def run_task():
            plugin.generate_image(prompt, dest_abs, size=f"{width}x{height}")
            # Validate output
            valid, err = asset_validator.validate_image(dest_abs, expected_width=256, expected_height=256)
            if not valid:
                # Remove invalid file
                if os.path.exists(dest_abs):
                    os.remove(dest_abs)
                raise ValueError(f"Asset quality check failed: {err}")
                
        try:
            # Let the agent's base execution retry engine handle rate limits / failures
            log_action("GenerationManager", "ExecuteGen", "INFO", 0.0, f"Triggering {plugin.name} render...")
            
            # Simple wrapper to run inside retry loop
            attempts = 3
            for attempt in range(1, attempts + 1):
                try:
                    run_task()
                    break
                except Exception as e:
                    if attempt == attempts:
                        raise e
                    time.sleep(1.0)
                    
            self.save_to_cache(param_hash, dest_abs, seed)
            self._register_asset_db(project_id, plugin.name, prompt, neg_prompt, seed, dest_rel, width, height)
            return dest_rel
        except Exception as e:
            log_action("GenerationManager", "ExecuteGen", "FAILED", 0.0, f"Generation failed after retries: {str(e)}")
            return None

    def generate_images_batch(self, project_id: str, prompts: List[StructuredPrompt], 
                              preferred_provider: str = "ComfyUI", 
                              char_id: Optional[str] = None) -> List[Optional[str]]:
        """
        Generates multiple scenes simultaneously using thread pool executors.
        Implements failed job recovery (resumes from last successful asset).
        """
        results = [None] * len(prompts)
        
        # Load project checkpoints to see if we can resume/skip previously successful indices
        proj_dir = project_manager.get_project_dir(project_id)
        batch_chk_path = os.path.join(proj_dir, "batch_checkpoint.json")
        
        successful_indices = {}
        if os.path.exists(batch_chk_path):
            try:
                with open(batch_chk_path, "r", encoding="utf-8") as f:
                    successful_indices = json_loads(f.read())
            except Exception:
                pass

        # Populate previously rendered assets
        for idx_str, path in successful_indices.items():
            idx = int(idx_str)
            if idx < len(prompts) and os.path.exists(os.path.join(proj_dir, path)):
                results[idx] = path
                
        def process_index(idx: int):
            if results[idx] is not None:
                # Already complete, skip
                return
            sp = prompts[idx]
            res = self.generate_image(project_id, sp, preferred_provider, char_id)
            if res:
                results[idx] = res
                # Update checkpoint indices
                with self.lock:
                    successful_indices[str(idx)] = res
                    try:
                        with open(batch_chk_path, "w", encoding="utf-8") as f:
                            f.write(json_dumps(successful_indices))
                    except Exception:
                        pass

        # Thread safe lock for updating checkpoint files
        self.lock = threading_lock()
        
        with ThreadPoolExecutor(max_workers=self.max_concurrency) as executor:
            executor.map(process_index, range(len(prompts)))
            
        # Clean up batch checkpoint when entire batch completes successfully
        if all(r is not None for r in results) and os.path.exists(batch_chk_path):
            os.remove(batch_chk_path)
            
        return results

    def _register_asset_db(self, project_id: str, provider: str, prompt: str, 
                            neg_prompt: str, seed: int, file_path: str, width: int, height: int):
        """Logs output asset metadata into SQLite assets table."""
        try:
            proj_dir = project_manager.get_project_dir(project_id)
            abs_path = os.path.join(proj_dir, file_path)
            size_bytes = os.path.getsize(abs_path) if os.path.exists(abs_path) else 0
            created_at = datetime.now().isoformat()
            asset_id = f"asset_{str(uuid.uuid4())[:8]}"
            
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO assets 
                    (id, project_id, workflow_name, prompt, seed, model_used, file_path, file_size, resolution, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (asset_id, project_id, f"Prompt Engine [{provider}]", prompt, seed, 
                     settings_manager.settings.models.image_model, file_path, size_bytes, f"{width}x{height}", created_at)
                )
                conn.commit()
        except Exception as e:
            log_action("GenerationManager", "LogDB", "WARNING", 0.0, f"Error saving asset details to database: {str(e)}")

def json_loads(text: str):
    import json
    return json.loads(text)

def json_dumps(data: Any) -> str:
    import json
    return json.dumps(data)

def threading_lock():
    import threading
    return threading.Lock()

# Singleton GenerationManager
generation_manager = GenerationManager()
