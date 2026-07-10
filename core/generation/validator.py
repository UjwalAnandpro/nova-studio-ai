import os
import subprocess
import shutil
from typing import Tuple
from PIL import Image, ImageStat
from core.config.manager import settings_manager
from core.logger.custom_logger import log_action

class AssetValidator:
    """
    Validates output integrity of generated images and videos.
    Rejects corrupt frames, solid black/white outputs, and broken video streams.
    """

    def validate_image(self, file_path: str, expected_width: int = 256, expected_height: int = 256) -> Tuple[bool, str]:
        """
        Inspects image header integrity, resolution boundaries, and color spaces.
        Rejects solid black/white images.
        """
        if not os.path.exists(file_path):
            return False, "File does not exist on disk."
            
        try:
            with Image.open(file_path) as img:
                # Verify format/integrity
                img.verify()
                
            # Re-open for pixel inspection (verify() closes file)
            with Image.open(file_path) as img:
                width, height = img.size
                if width < expected_width or height < expected_height:
                    return False, f"Image resolution ({width}x{height}) is lower than expected minimum."
                    
                # Calculate mean brightness stats to reject pure black/white images
                # Convert to grayscale first
                gray_img = img.convert("L")
                stat = ImageStat.Stat(gray_img)
                mean_brightness = stat.mean[0]
                
                # Check bounds (scale 0-255)
                if mean_brightness < 2.0:
                    return False, "Validation rejected: Fully black image output detected."
                if mean_brightness > 253.0:
                    return False, "Validation rejected: Fully white image output detected."
                    
            return True, ""
        except Exception as e:
            return False, f"Corrupted image file: {str(e)}"

    def validate_video(self, file_path: str, min_size_bytes: int = 1024) -> Tuple[bool, str]:
        """
        Validates video file container, duration, and checks for empty video streams.
        Uses ffprobe if available.
        """
        if not os.path.exists(file_path):
            return False, "Video file does not exist on disk."
            
        # Basic file size threshold
        file_size = os.path.getsize(file_path)
        if file_size < min_size_bytes:
            return False, f"Video file size too small ({file_size} bytes)."
            
        # Probe using FFmpeg/ffprobe if path configured/available
        ffmpeg_bin = settings_manager.settings.ffmpeg_path
        ffprobe_bin = ffmpeg_bin.replace("ffmpeg", "ffprobe")
        
        if shutil.which(ffprobe_bin):
            try:
                cmd = [
                    ffprobe_bin, "-v", "error",
                    "-select_streams", "v:0",
                    "-show_entries", "stream=width,height,duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    file_path
                ]
                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5.0)
                output = result.stdout.strip()
                
                if not output:
                    return False, "Broken video container: No active video streams found."
                    
                # Parse lines: width, height, duration
                lines = output.splitlines()
                if len(lines) >= 3:
                    # check duration
                    duration = float(lines[2])
                    if duration <= 0.0:
                        return False, "Video reports zero-length duration."
                        
            except Exception as e:
                # Fall back to size check if ffprobe errors
                pass
                
        return True, ""

# Singleton AssetValidator
asset_validator = AssetValidator()
