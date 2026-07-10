import os
import hashlib
import subprocess
from PIL import Image, ImageDraw
from core.config.manager import settings_manager
from core.projects.manager import project_manager
from core.logger.custom_logger import log_action

class ThumbnailGenerator:
    """
    Extracts frame screenshots from videos and scales images to compile lightweight
    thumbnails for the timeline preview track.
    """

    def get_thumbnail(self, project_id: str, media_rel_path: str) -> str:
        """
        Retrieves path to a cached thumbnail. Generates it if missing.
        Returns the absolute filepath.
        """
        proj_dir = project_manager.get_project_dir(project_id)
        media_abs_path = os.path.join(proj_dir, media_rel_path)
        
        # Fallback if file does not exist
        if not os.path.exists(media_abs_path):
            return self._create_fallback_thumbnail(project_id, media_rel_path, "Missing File")
            
        # Compute stable hash based on filepath and modification time
        mtime = os.path.getmtime(media_abs_path)
        hash_key = hashlib.md5(f"{media_abs_path}_{mtime}".encode("utf-8")).hexdigest()
        
        # Setup cached thumbnail file path
        thumb_dir = os.path.join(proj_dir, "cache", "thumbnails")
        os.makedirs(thumb_dir, exist_ok=True)
        
        thumb_filename = f"{hash_key}.png"
        thumb_filepath = os.path.join(thumb_dir, thumb_filename)
        
        if os.path.exists(thumb_filepath):
            return thumb_filepath
            
        # Compile new thumbnail based on extension
        ext = os.path.splitext(media_abs_path)[1].lower()
        
        try:
            if ext in (".png", ".jpg", ".jpeg", ".webp"):
                # Scale image with Pillow
                with Image.open(media_abs_path) as img:
                    img.thumbnail((160, 90))
                    img.save(thumb_filepath, "PNG")
                return thumb_filepath
                
            elif ext in (".mp4", ".mov", ".mkv", ".webm", ".avi"):
                # Extract frame at 1s (or 0s if clip short) using FFmpeg
                ffmpeg_path = settings_manager.settings.ffmpeg_path
                cmd = [
                    ffmpeg_path, "-y",
                    "-ss", "0.5",  # grab frame at 0.5 seconds
                    "-i", media_abs_path,
                    "-frames:v", "1",
                    "-vf", "scale=160:90:force_original_aspect_ratio=decrease,pad=160:90:(ow-iw)/2:(oh-ih)/2:black",
                    thumb_filepath
                ]
                subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=3.0)
                return thumb_filepath
                
            elif ext in (".wav", ".mp3", ".ogg", ".aac"):
                # Visual waveform placeholder for audio
                return self._create_fallback_thumbnail(project_id, media_rel_path, "🎵 Audio")
                
        except Exception as e:
            log_action("ThumbnailGenerator", "Generate", "WARNING", 0.0, f"Failed generating thumbnail for {media_rel_path}: {str(e)}")
            
        return self._create_fallback_thumbnail(project_id, media_rel_path, "Preview")

    def _create_fallback_thumbnail(self, project_id: str, label: str, title: str) -> str:
        """Generates a simple color-coded block image when media extraction fails."""
        proj_dir = project_manager.get_project_dir(project_id)
        thumb_dir = os.path.join(proj_dir, "cache", "thumbnails")
        os.makedirs(thumb_dir, exist_ok=True)
        
        filename = f"fallback_{hashlib.md5(label.encode('utf-8')).hexdigest()}.png"
        filepath = os.path.join(thumb_dir, filename)
        
        if os.path.exists(filepath):
            return filepath
            
        try:
            img = Image.new("RGB", (160, 90), color="#2a2b3d")
            draw = ImageDraw.Draw(img)
            # Draw label text
            draw.text((10, 30), title, fill="#cdd6f4")
            draw.text((10, 50), os.path.basename(label)[:15], fill="#585b70")
            img.save(filepath, "PNG")
            return filepath
        except Exception:
            pass
        return ""

# Singleton ThumbnailGenerator
thumbnail_generator = ThumbnailGenerator()
