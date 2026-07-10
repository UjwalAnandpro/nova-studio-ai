import os
import time
import uuid
from typing import Dict, Any, List, Optional, Tuple
from core.logger.custom_logger import log_action
from core.config.manager import settings_manager
from core.comfy.connector import comfy_connector
from core.comfy.workflow import workflow_manager
from core.comfy.models_manager import models_manager
from core.comfy.queue_manager import queue_manager, Job
from core.comfy.downloader import download_manager
from core.comfy.asset_manager import asset_manager
from core.plugins.loader import plugin_loader

class ComfyWorkflowEngine:
    """
    Unified engine acting as the single gateway for all ComfyUI generation pipelines.
    Streamlit only speaks to this engine class.
    """
    
    def scan_models(self) -> Dict[str, List[Dict[str, Any]]]:
        """Triggers a filesystem scan for all installed models."""
        return models_manager.scan_models()

    def validate_workflow(self, workflow_name: str) -> Tuple[bool, List[str]]:
        """Validates that a workflow json is healthy and has required models."""
        return workflow_manager.validate_workflow(workflow_name, models_manager)

    def cancel_job(self, job_id: str) -> bool:
        """Stops rendering task queue for a given job."""
        return queue_manager.cancel_job(job_id)

    def run_workflow(self, workflow_name: str, variables: Dict[str, Any], project_id: str) -> str:
        """
        Executes a workflow. Injects variables, validates parameters, and sends to ComfyUI.
        Falls back to simulated pipelines with mock plugins if offline.
        """
        # Save prompt history
        prompt_text = variables.get("PROMPT", variables.get("prompt", "Default Generation"))
        seed = variables.get("SEED", variables.get("seed", int(time.time())))
        asset_manager.save_prompt(project_id, workflow_name, prompt_text, variables, seed)
        asset_manager.update_workflow_usage(workflow_name)

        if not comfy_connector.is_connected:
            # ComfyUI is offline - run simulated workspace thread
            log_action("WorkflowEngine", "RunWorkflow", "WARNING", 0.0, f"ComfyUI server offline. Booting mock simulation for '{workflow_name}'.")
            
            job = Job(workflow_name, project_id)
            queue_manager.add_job(job)
            
            # Setup offline execution callback to produce fake files
            def offline_callback():
                return self._execute_mock_generator(workflow_name, variables, project_id)
                
            queue_manager.simulate_offline_job(job.id, offline_callback)
            return job.id
            
        # ComfyUI is online - trigger HTTP REST workflow pipeline
        w_entry = workflow_manager.get_workflow(workflow_name)
        if not w_entry:
            raise ValueError(f"Workflow '{workflow_name}' not registered in library.")
            
        workflow_json = w_entry["workflow"]
        
        # Replace variable tokens recursively
        injected_workflow = workflow_manager.inject_variables(workflow_json, variables)
        
        # REST post
        log_action("WorkflowEngine", "RunWorkflow", "INFO", 0.0, f"Posting workflow '{workflow_name}' to ComfyUI REST...")
        success, response, err = comfy_connector.post("/prompt", json_data=injected_workflow)
        
        if success and response:
            prompt_id = response.get("prompt_id")
            if prompt_id:
                job = Job(workflow_name, project_id, prompt_id=prompt_id)
                queue_manager.add_job(job)
                log_action("WorkflowEngine", "RunWorkflow", "SUCCESS", 0.0, f"Job queued successfully. ComfyUI ID: {prompt_id}")
                return prompt_id
            else:
                raise Exception(f"ComfyUI response missing prompt_id: {response}")
        else:
            raise Exception(f"ComfyUI REST submission error: {err}")

    def generate_image(self, prompt: str, project_id: str, size: str = "1024x1024", **kwargs) -> str:
        """
        High-level wrapper to generate an image. Checks defaults and queues the request.
        """
        variables = {
            "PROMPT": prompt,
            "WIDTH": int(size.split("x")[0]),
            "HEIGHT": int(size.split("x")[1]),
            "SEED": kwargs.get("seed", int(time.time() * 1000) % 9999999999),
            "CFG": kwargs.get("cfg", 8.0),
            "STEPS": kwargs.get("steps", 20),
            "SAMPLER": kwargs.get("sampler", "euler")
        }
        
        # Use ComfyUI Image workflow if registered, else run standard runner
        workflow_name = "Image Generation"
        if not workflow_manager.get_workflow(workflow_name):
            # Fallback to create one in discovery if absent
            workflow_name = list(workflow_manager.workflows.keys())[0] if workflow_manager.workflows else "Image Generation"
            
        return self.run_workflow(workflow_name, variables, project_id)

    def generate_video(self, prompt_or_image: str, project_id: str, duration: float = 4.0, **kwargs) -> str:
        """
        High-level wrapper to generate a video clip.
        """
        variables = {
            "PROMPT": prompt_or_image,
            "IMAGE_PATH": prompt_or_image,
            "DURATION": duration,
            "SEED": kwargs.get("seed", int(time.time() * 1000) % 9999999999),
            "STEPS": kwargs.get("steps", 20)
        }
        
        workflow_name = "Text To Video"
        if os.path.exists(prompt_or_image):
            workflow_name = "Image To Video"
            
        if not workflow_manager.get_workflow(workflow_name):
            workflow_name = list(workflow_manager.workflows.keys())[0] if workflow_manager.workflows else "Text To Video"
            
        return self.run_workflow(workflow_name, variables, project_id)

    def download_assets(self, job_id: str) -> List[str]:
        """Downloads assets for a finished job and indexes them in SQLite."""
        job = queue_manager.get_job(job_id)
        if not job or job.status != "Completed":
            return []
            
        downloaded_paths = []
        for filename in job.output_files:
            # Download file from ComfyUI REST view server
            rel_path = download_manager.download_asset(filename, job.project_id)
            if rel_path:
                downloaded_paths.append(rel_path)
                
                # Fetch absolute path & size for db index
                proj_dir = os.path.join(settings_manager.settings.project_path, job.project_id)
                abs_path = os.path.join(proj_dir, rel_path)
                size_bytes = os.path.getsize(abs_path) if os.path.exists(abs_path) else 0
                
                # Register in Asset DB
                asset_id = f"asset_{str(uuid.uuid4())[:8]}"
                res = "1024x1024" if "png" in filename else "1080x1920"
                asset_manager.register_asset(
                    asset_id=asset_id,
                    project_id=job.project_id,
                    workflow_name=job.workflow_name,
                    prompt="",
                    seed=int(time.time()),
                    model_used=settings_manager.settings.models.image_model if "png" in filename else settings_manager.settings.models.video_model,
                    file_path=rel_path,
                    file_size=size_bytes,
                    resolution=res
                )
                
        return downloaded_paths

    def _execute_mock_generator(self, workflow_name: str, variables: Dict[str, Any], project_id: str) -> List[str]:
        """Runs the mock fallback plugins to write output assets offline."""
        proj_dir = os.path.join(settings_manager.settings.project_path, project_id)
        os.makedirs(os.path.join(proj_dir, "assets"), exist_ok=True)
        
        filename = f"gen_{int(time.time())}"
        prompt = variables.get("PROMPT", variables.get("prompt", "Local Scene"))
        
        # If it's video or image, run plugin mock
        if "video" in workflow_name.lower():
            out_fn = f"{filename}.mp4"
            out_abs = os.path.join(proj_dir, "assets", out_fn)
            
            plugin = plugin_loader.get_plugin("video", "ComfyUI Video")
            if plugin:
                plugin.generate_video(prompt, out_abs, duration=4.0)
            return [out_fn]
        else:
            out_fn = f"{filename}.png"
            out_abs = os.path.join(proj_dir, "assets", out_fn)
            
            plugin = plugin_loader.get_plugin("image", "ComfyUI Image")
            size_str = f"{variables.get('WIDTH', 1024)}x{variables.get('HEIGHT', 1024)}"
            if plugin:
                plugin.generate_image(prompt, out_abs, size=size_str)
            return [out_fn]

# Singleton ComfyWorkflowEngine
comfy_engine = ComfyWorkflowEngine()
