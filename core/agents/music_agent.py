import os
from typing import Dict, Any
from core.agents.base import BaseAgent
from core.projects.manager import project_manager
from core.plugins.loader import plugin_loader
from core.config.manager import settings_manager

class MusicAgent(BaseAgent):
    """
    Agent responsible for generating the background music track.
    Integrates with the default configured Music plugin (MusicGen, Stable Audio, etc.).
    """
    def __init__(self):
        super().__init__("MusicAgent")

    def run(self, project_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        storyboard = context.get("storyboard", [])
        if not storyboard:
            return context

        proj_dir = project_manager.get_project_dir(project_id)
        music_provider = settings_manager.settings.music_provider
        plugin = plugin_loader.get_plugin("music", music_provider)
        
        # Calculate total required duration of BGM
        total_duration = sum(float(scene.get("duration", 5.0)) for scene in storyboard)
        total_duration = max(5.0, total_duration)
        
        # Mood prompt from script description or first scene
        first_scene = storyboard[0]
        music_prompt = first_scene.get("music_prompt", "cinematic ambient music")
        
        target_path_rel = "music/background_theme.wav"
        target_path_abs = os.path.join(proj_dir, target_path_rel)
        
        self.log("GenerateMusic", "INFO", 0.0, f"Synthesizing {total_duration}s BGM themed: '{music_prompt}' using '{music_provider}'...")
        
        # Ensure target folder exists
        music_dir = os.path.join(proj_dir, "music")
        os.makedirs(music_dir, exist_ok=True)
        
        def music_task():
            if plugin:
                plugin.generate_music(music_prompt, target_path_abs, duration=total_duration)
            else:
                # Fallback: write rhythmic WAV loop
                import wave, struct, math
                sample_rate = 16000
                num_samples = int(total_duration * sample_rate)
                with wave.open(target_path_abs, "wb") as wav_file:
                    wav_file.setparams((1, 2, sample_rate, num_samples, "NONE", "not compressed"))
                    data = bytearray()
                    # Play an arpeggio sequence
                    freqs = [220.0, 277.18, 329.63, 440.0]
                    for i in range(num_samples):
                        t = float(i) / sample_rate
                        # switch note every 0.4 seconds
                        note_idx = int(t / 0.4) % len(freqs)
                        vol = 4000.0 * (1.0 - (t % 0.4) / 0.4)  # decay envelope
                        val = int(vol * math.sin(2 * math.pi * freqs[note_idx] * t))
                        data.extend(struct.pack("<h", val))
                    wav_file.writeframes(data)
                    
        try:
            self.execute_with_retry("GenerateMusicTrack", music_task)
            context["generated_music"] = target_path_rel
        except Exception as e:
            self.log("GenerateMusicTrack", "FAILED", 0.0, f"Failed music synthesis: {str(e)}")

        return context
