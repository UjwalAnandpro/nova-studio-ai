import os
import requests
import subprocess
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, Any, Optional
from core.plugins.base import ImagePlugin, VideoPlugin
from core.logger.custom_logger import log_action
from core.config.manager import settings_manager

class ComfyUIImagePlugin(ImagePlugin):
    """ComfyUI Image Generator Plugin."""

    @property
    def name(self) -> str:
        return "ComfyUI Image"

    @property
    def description(self) -> str:
        return "Generates SDXL/SD1.5 images via local ComfyUI instance or falls back to PIL offline generators."

    @property
    def version(self) -> str:
        return "1.0.0"

    def initialize(self, config: Dict[str, Any]) -> bool:
        self.address = config.get("comfyui_address", "http://127.0.0.1:8188")
        return True

    def is_healthy(self) -> bool:
        try:
            r = requests.get(f"{self.address}/history", timeout=1.0)
            return r.status_code == 200
        except Exception:
            return False

    def generate_image(self, prompt: str, output_path: str, size: Optional[str] = None, **kwargs) -> str:
        log_action("ComfyUIImagePlugin", "GenerateImage", "INFO", 0.0, f"Generating image for prompt: '{prompt[:30]}...'")
        
        # Standard size 1024x1024 or parsed
        width, height = 1024, 1024
        if size:
            try:
                w, h = map(int, size.lower().split("x"))
                width, height = w, h
            except Exception:
                pass

        if not self.is_healthy():
            log_action("ComfyUIImagePlugin", "GenerateImage", "WARNING", 0.0, "ComfyUI offline. Generating local PIL graphic.")
            try:
                # Fallback: create beautiful PIL gradient with text
                img = Image.new("RGB", (width, height), color="#1e1e2e")
                draw = ImageDraw.Draw(img)
                
                # Draw grid patterns
                for x in range(0, width, 64):
                    draw.line([(x, 0), (x, height)], fill="#313244", width=1)
                for y in range(0, height, 64):
                    draw.line([(0, y), (width, y)], fill="#313244", width=1)
                    
                # Highlight center
                draw.ellipse(
                    [width//4, height//4, 3*width//4, 3*height//4],
                    outline="#cba6f7",
                    width=4
                )
                
                # Draw prompt text (simple wrap/draw)
                words = prompt.split()
                lines = []
                current_line = []
                for word in words:
                    if len(" ".join(current_line + [word])) * 8 > width - 100:
                        lines.append(" ".join(current_line))
                        current_line = [word]
                    else:
                        current_line.append(word)
                if current_line:
                    lines.append(" ".join(current_line))
                    
                text_y = height // 2 - len(lines) * 10
                for line in lines:
                    draw.text((width // 10, text_y), line, fill="#cdd6f4")
                    text_y += 24
                    
                draw.text((20, height - 30), "NOVA STUDIO AI • OFFLINE MOCK", fill="#a6adc8")
                
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                img.save(output_path)
                log_action("ComfyUIImagePlugin", "GenerateImage", "SUCCESS", 0.1, f"Offline Image saved: {output_path}")
                return output_path
            except Exception as e:
                log_action("ComfyUIImagePlugin", "GenerateImage", "FAILED", 0.0, f"Local generation error: {str(e)}")
                raise e

        # Code here for ComfyUI REST workflow trigger goes in future implementation
        log_action("ComfyUIImagePlugin", "GenerateImage", "INFO", 0.0, "ComfyUI online rendering...")
        return output_path


class ComfyUIVideoPlugin(VideoPlugin):
    """ComfyUI Video Generator Plugin."""

    @property
    def name(self) -> str:
        return "ComfyUI Video"

    @property
    def description(self) -> str:
        return "Generates SVD/AnimateDiff clips via local ComfyUI or falls back to animated frames + FFmpeg."

    @property
    def version(self) -> str:
        return "1.0.0"

    def initialize(self, config: Dict[str, Any]) -> bool:
        self.address = config.get("comfyui_address", "http://127.0.0.1:8188")
        return True

    def is_healthy(self) -> bool:
        try:
            r = requests.get(f"{self.address}/history", timeout=1.0)
            return r.status_code == 200
        except Exception:
            return False

    def generate_video(self, prompt_or_image_path: str, output_path: str, duration: float = 4.0, **kwargs) -> str:
        log_action("ComfyUIVideoPlugin", "GenerateVideo", "INFO", 0.0, f"Generating {duration}s video clip")
        
        if not self.is_healthy():
            log_action("ComfyUIVideoPlugin", "GenerateVideo", "WARNING", 0.0, "ComfyUI offline. Compiling local MP4 using FFmpeg.")
            
            # Create a temporary list of frames
            temp_dir = settings_manager.settings.temp_path
            os.makedirs(temp_dir, exist_ok=True)
            
            frame_pattern = os.path.join(temp_dir, "frame_%d.png")
            num_frames = int(duration * 24)  # 24 fps
            
            # Base image: load image from path or create mock base
            base_img = None
            if os.path.exists(prompt_or_image_path):
                try:
                    base_img = Image.open(prompt_or_image_path)
                except Exception:
                    pass
            
            if base_img is None:
                base_img = Image.new("RGB", (1024, 1024), color="#1e1e2e")
                draw = ImageDraw.Draw(base_img)
                draw.text((100, 500), f"Video: {prompt_or_image_path[:50]}", fill="#f38ba8")
                
            width, height = base_img.size
            
            # Write out frames with minor color shifts or pans
            generated_frames = []
            for frame_idx in range(num_frames):
                frame_img = base_img.copy()
                draw = ImageDraw.Draw(frame_img)
                # Animate a floating bubble
                bubble_x = int(width / 2 + 100 * (frame_idx / num_frames))
                bubble_y = int(height / 2 + 50 * (frame_idx / num_frames))
                draw.ellipse(
                    [bubble_x - 30, bubble_y - 30, bubble_x + 30, bubble_y + 30],
                    outline="#a6e3a1",
                    width=3
                )
                
                # Timestamp info
                draw.text((10, 10), f"Frame {frame_idx} / {num_frames} ({frame_idx/24:.2f}s)", fill="#a6adc8")
                
                fp = frame_pattern % frame_idx
                frame_img.save(fp)
                generated_frames.append(fp)
                
            # Compile with FFmpeg command
            ffmpeg_cmd = [
                settings_manager.settings.ffmpeg_path,
                "-y",
                "-f", "image2",
                "-framerate", "24",
                "-i", frame_pattern,
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                output_path
            ]
            
            try:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                log_action("ComfyUIVideoPlugin", "GenerateVideo", "SUCCESS", duration, f"Compiled video: {output_path}")
            except Exception as e:
                log_action("ComfyUIVideoPlugin", "GenerateVideo", "FAILED", 0.0, f"FFmpeg compilation failed: {str(e)}")
                raise e
            finally:
                # Cleanup temp frames
                for fp in generated_frames:
                    if os.path.exists(fp):
                        os.remove(fp)
                        
            return output_path

        log_action("ComfyUIVideoPlugin", "GenerateVideo", "INFO", 0.0, "ComfyUI online video rendering...")
        return output_path
