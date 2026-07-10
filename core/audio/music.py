import os
import uuid
import time
from typing import List, Dict, Any, Optional
from core.plugins.loader import plugin_loader
from core.projects.manager import project_manager
from core.logger.custom_logger import log_action

class MusicEngine:
    """
    Synthesizes background music prompts or maps loops from local audio libraries.
    """

    def generate_bgm(self, project_id: str, prompt: str, duration: float, volume: float = 0.5) -> Optional[str]:
        """
        Triggers MusicGen plugins to generate custom theme track loops.
        """
        proj_dir = project_manager.get_project_dir(project_id)
        
        plugin = plugin_loader.get_plugin("music", "MusicGen")
        if not plugin:
            music_plugins = plugin_loader.list_plugins("music")
            plugin = music_plugins[0] if music_plugins else None
            
        if not plugin:
            log_action("MusicEngine", "Generate", "FAILED", 0.0, "No music plugins loaded.")
            return None
            
        filename = f"music_{int(time.time())}_{str(uuid.uuid4())[:4]}.wav"
        dest_rel = f"music/{filename}"
        dest_abs = os.path.join(proj_dir, dest_rel)
        os.makedirs(os.path.dirname(dest_abs), exist_ok=True)
        
        try:
            # Generate backing music loop
            plugin.generate_music(prompt, dest_abs, duration=duration)
            log_action("MusicEngine", "Generate", "SUCCESS", 0.0, f"Synthesized BGM loop: {dest_abs}")
            return dest_rel
        except Exception as e:
            log_action("MusicEngine", "Generate", "FAILED", 0.0, f"Failed rendering BGM loop: {str(e)}")
            return None

class AudioMixer:
    """
    Assembles speech narration and background music tracks, and
    compiles sidechain ducking volume curves.
    """

    def build_ducking_filter(self, speaking_intervals: List[tuple], duck_ratio: float = 0.2, default_vol: float = 0.6) -> str:
        """
        Dynamically constructs an FFmpeg volume filter expression that scales down
        music volume during active voice timestamps.
        
        Example output:
        volume='if(between(t,0,5)+between(t,10,15),0.12,0.6)':eval=frame
        """
        if not speaking_intervals:
            return f"volume={default_vol}"
            
        # Build logical checks for each interval: between(t, start, end)
        checks = []
        for start, end in speaking_intervals:
            checks.append(f"between(t,{start:.2f},{end:.2f})")
            
        check_expr = "+".join(checks)
        ducked_vol = default_vol * duck_ratio
        
        return f"volume='if({check_expr},{ducked_vol:.3f},{default_vol:.3f})':eval=frame"

# Singletons
music_engine = MusicEngine()
audio_mixer = AudioMixer()
