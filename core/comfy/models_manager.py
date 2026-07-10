import os
from typing import Dict, Any, List, Optional
from core.config.manager import settings_manager
from core.logger.custom_logger import log_action

class ModelsManager:
    """
    Scans, indexes, and reports status of model weights and checkpoints across standard
    ComfyUI directories.
    """
    def __init__(self, models_dir: Optional[str] = None):
        if models_dir is None:
            # Default to core folder's parent workspace root 'models'
            app_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            models_dir = os.path.join(app_root, "models")
            
        self.models_dir = models_dir
        
        # Mapping of model category key to standard folder names
        self.folder_mapping = {
            "checkpoints": ["checkpoints"],
            "vae": ["vae"],
            "lora": ["loras", "lora"],
            "controlnet": ["controlnet"],
            "clip": ["clip"],
            "embeddings": ["embeddings"],
            "ipadapter": ["ipadapter"],
            "animatediff": ["animatediff", "animatediff_models"],
            "upscalers": ["upscale_models", "upscalers"],
            "video_models": ["video_models"],
            "gguf": ["gguf"]
        }
        
        self.installed_models: Dict[str, List[Dict[str, Any]]] = {}
        self.ensure_folders_exist()
        self.scan_models()

    def ensure_folders_exist(self):
        """Creates model subdirectories if they do not exist."""
        os.makedirs(self.models_dir, exist_ok=True)
        for cat, folders in self.folder_mapping.items():
            primary_folder = os.path.join(self.models_dir, folders[0])
            os.makedirs(primary_folder, exist_ok=True)

    def scan_models(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Scans all folders under the configured /models path and builds the database index.
        Classifies status: Installed, Corrupted (if size is 0), Unknown (unindexed folder).
        """
        self.installed_models.clear()
        
        log_action("ModelsManager", "Scan", "INFO", 0.0, f"Scanning models under {self.models_dir}...")
        
        for category, folders in self.folder_mapping.items():
            self.installed_models[category] = []
            
            for folder_name in folders:
                target_dir = os.path.join(self.models_dir, folder_name)
                if not os.path.exists(target_dir):
                    continue
                    
                for root, dirs, files in os.walk(target_dir):
                    for filename in files:
                        if filename.startswith(".") or filename.endswith(".txt"):
                            continue
                            
                        file_path = os.path.join(root, filename)
                        size_bytes = os.path.getsize(file_path)
                        rel_path = os.path.relpath(file_path, target_dir)
                        
                        # Determine status
                        status = "Installed"
                        if size_bytes == 0:
                            status = "Corrupted"
                        elif size_bytes < 1000:
                            status = "Corrupted"  # likely a mock or failed download
                            
                        self.installed_models[category].append({
                            "name": filename,
                            "relative_path": rel_path.replace("\\", "/"),
                            "absolute_path": file_path,
                            "size_bytes": size_bytes,
                            "size_gb": round(size_bytes / (1024**3), 3),
                            "status": status,
                            "category": category
                        })
                        
        log_action("ModelsManager", "Scan", "SUCCESS", 0.0, f"Scan complete. Indexed {sum(len(v) for v in self.installed_models.values())} files.")
        return self.installed_models

    def is_model_installed(self, model_type: str, model_name: str) -> bool:
        """
        Checks if a model matching model_name is installed in the given model_type folder.
        Uses fuzzy name matches for ease of use.
        """
        cat = model_type.lower()
        if cat not in self.installed_models:
            # Fallback mappings for synonyms
            if cat in ("checkpoint", "checkpoints"):
                cat = "checkpoints"
            elif cat in ("loras",):
                cat = "lora"
            else:
                return False
                
        # Check names
        models = self.installed_models.get(cat, [])
        for m in models:
            if m["name"].lower() == model_name.lower():
                return m["status"] == "Installed"
            # Fuzzy match (e.g. check if full required filename matches end or substring)
            if model_name.lower() in m["name"].lower():
                return m["status"] == "Installed"
                
        return False

    def list_models_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Lists all installed models within a specific category."""
        return self.installed_models.get(category.lower(), [])

# Singleton ModelsManager
models_manager = ModelsManager()
