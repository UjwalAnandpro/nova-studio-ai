import os
import time
from typing import Dict, Any, List
from core.agents.base import BaseAgent
from core.projects.manager import project_manager
from core.plugins.loader import plugin_loader
from core.config.manager import settings_manager

class VideoAgent(BaseAgent):
    """
    Agent responsible for generating video sequences from static storyboard frames.
    Integrates with the default configured Video plugin (ComfyUI SVD, text-to-video, etc.).
    """
    def __init__(self):
        super().__init__("VideoAgent")

    def run(self, project_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        storyboard = context.get("storyboard", [])
        if not storyboard:
            return context

        proj_dir = project_manager.get_project_dir(project_id)
        video_provider = settings_manager.settings.video_provider
        plugin = plugin_loader.get_plugin("video", video_provider)
        
        self.log("GenerateVideos", "INFO", 0.0, f"Generating {len(storyboard)} video clips using '{video_provider}'...")
        
        # Ensure target folder exists
        videos_dir = os.path.join(proj_dir, "videos")
        os.makedirs(videos_dir, exist_ok=True)
        
        generated_assets = []
        
        for idx, scene in enumerate(storyboard):
            target_path_rel = scene.get("video_path")
            target_path_abs = os.path.join(proj_dir, target_path_rel)
            
            # Source image path for Image-To-Video mapping
            img_rel = scene.get("image_path")
            img_abs = os.path.join(proj_dir, img_rel)
            
            # In case image generation failed, use prompt text directly
            src_input = img_abs if os.path.exists(img_abs) else scene.get("prompt", "")
            duration = scene.get("duration", 4.0)

            # Sub-execution task for retry engine wrapper
            def generate_task():
                if plugin:
                    plugin.generate_video(src_input, target_path_abs, duration=duration)
                else:
                    # Mock: compile a silent 4s video using FFmpeg color source if no plugin
                    ffmpeg_path = settings_manager.settings.ffmpeg_path
                    cmd = [
                        ffmpeg_path, "-y",
                        "-f", "lavfi", "-i", f"color=c=black:s=1024x576:d={duration}",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        target_path_abs
                    ]
                    import subprocess
                    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                    
            try:
                self.execute_with_retry(f"GenerateVideo_Scene_{scene['scene_number']}", generate_task)
                generated_assets.append(target_path_rel)
            except Exception as e:
                self.log(f"GenerateVideo_Scene_{scene['scene_number']}", "FAILED", 0.0, f"Failed video render: {str(e)}")

        context["generated_videos"] = generated_assets
        return context
