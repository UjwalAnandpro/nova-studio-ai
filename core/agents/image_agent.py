import os
import shutil
import time
from typing import Dict, Any, List
from core.agents.base import BaseAgent
from core.projects.manager import project_manager
from core.plugins.loader import plugin_loader
from core.config.manager import settings_manager

class ImageAgent(BaseAgent):
    """
    Agent responsible for generating the visual storyboard frames.
    Integrates with the default configured Image plugin (ComfyUI, Flux, SDXL, etc.).
    """
    def __init__(self):
        super().__init__("ImageAgent")

    def run(self, project_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        storyboard = context.get("storyboard", [])
        if not storyboard:
            return context

        proj_dir = project_manager.get_project_dir(project_id)
        image_provider = settings_manager.settings.image_provider
        plugin = plugin_loader.get_plugin("image", image_provider)
        
        self.log("GenerateImages", "INFO", 0.0, f"Generating {len(storyboard)} image frames using '{image_provider}'...")
        
        # Ensure target folder exists
        images_dir = os.path.join(proj_dir, "images")
        os.makedirs(images_dir, exist_ok=True)
        
        generated_assets = []
        
        for idx, scene in enumerate(storyboard):
            prompt = scene.get("prompt", "")
            target_path_rel = scene.get("image_path")
            target_path_abs = os.path.join(proj_dir, target_path_rel)
            
            # Sub-execution method for auto-retry wrapper
            def generate_task():
                if plugin:
                    plugin.generate_image(prompt, target_path_abs, size="1024x1024")
                else:
                    # Fallback to direct mock Pillow write if no plugin exists
                    time.sleep(0.1)
                    from PIL import Image, ImageDraw
                    img = Image.new("RGB", (1024, 1024), color="#1e1e2e")
                    draw = ImageDraw.Draw(img)
                    draw.text((200, 500), f"Scene {scene['scene_number']}\n{prompt[:50]}", fill="#89b4fa")
                    img.save(target_path_abs)
                    
            try:
                self.execute_with_retry(f"GenerateImage_Scene_{scene['scene_number']}", generate_task)
                generated_assets.append(target_path_rel)
            except Exception as e:
                self.log(f"GenerateImage_Scene_{scene['scene_number']}", "FAILED", 0.0, f"Failed image render: {str(e)}")

        context["generated_images"] = generated_assets
        return context
