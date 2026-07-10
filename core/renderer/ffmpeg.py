import subprocess
from typing import List, Dict, Any
from core.config.manager import settings_manager
from core.logger.custom_logger import log_action

class FFmpegRenderer:
    """
    Handles lower-level video compile and audio integration processes using FFmpeg.
    """
    def __init__(self):
        self.ffmpeg_path = settings_manager.settings.ffmpeg_path

    def run_cmd(self, args: List[str]) -> bool:
        """Executes a generic FFmpeg command."""
        cmd = [self.ffmpeg_path] + args
        try:
            log_action("Renderer", "RunCommand", "INFO", 0.0, f"Executing: {' '.join(cmd[:10])}...")
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            return result.returncode == 0
        except Exception as e:
            log_action("Renderer", "RunCommand", "FAILED", 0.0, f"FFmpeg execution failed: {str(e)}")
            return False
            
    def merge_audio_video(self, video_path: str, audio_path: str, output_path: str) -> bool:
        """Merges a video file and an audio file together."""
        args = [
            "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            output_path
        ]
        return self.run_cmd(args)
