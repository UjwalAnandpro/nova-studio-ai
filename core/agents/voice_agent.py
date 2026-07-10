import os
from typing import Dict, Any, List
from core.agents.base import BaseAgent
from core.projects.manager import project_manager
from core.plugins.loader import plugin_loader
from core.config.manager import settings_manager

class VoiceAgent(BaseAgent):
    """
    Agent responsible for generating speech narrative files for each scene.
    Integrates with the default configured TTS plugin (Kokoro, XTTS, Edge, etc.).
    """
    def __init__(self):
        super().__init__("VoiceAgent")

    def run(self, project_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        storyboard = context.get("storyboard", [])
        if not storyboard:
            return context

        proj_dir = project_manager.get_project_dir(project_id)
        tts_provider = settings_manager.settings.tts_provider
        plugin = plugin_loader.get_plugin("tts", tts_provider)
        
        self.log("GenerateVoice", "INFO", 0.0, f"Synthesizing speech files using '{tts_provider}'...")
        
        # Ensure target folder exists
        voice_dir = os.path.join(proj_dir, "voice")
        os.makedirs(voice_dir, exist_ok=True)
        
        generated_assets = []
        
        for idx, scene in enumerate(storyboard):
            text = scene.get("voice_text", "")
            target_path_rel = scene.get("voice_path")
            target_path_abs = os.path.join(proj_dir, target_path_rel)
            
            def voice_task():
                if plugin:
                    plugin.generate_speech(text, target_path_abs)
                else:
                    # Fallback to write dummy WAV file using Kokoro mock logic directly
                    import wave, struct, math
                    duration = max(1.0, len(text) * 0.075)
                    sample_rate = 16000
                    num_samples = int(duration * sample_rate)
                    with wave.open(target_path_abs, "wb") as wav_file:
                        wav_file.setparams((1, 2, sample_rate, num_samples, "NONE", "not compressed"))
                        data = bytearray()
                        for i in range(num_samples):
                            t = float(i) / sample_rate
                            freq = 150 + 20 * math.sin(2 * math.pi * 3 * t)
                            val = int(8192.0 * math.sin(2 * math.pi * freq * t))
                            data.extend(struct.pack("<h", val))
                        wav_file.writeframes(data)
                        
            try:
                self.execute_with_retry(f"GenerateVoice_Scene_{scene['scene_number']}", voice_task)
                generated_assets.append(target_path_rel)
            except Exception as e:
                self.log(f"GenerateVoice_Scene_{scene['scene_number']}", "FAILED", 0.0, f"Failed voice synthesis: {str(e)}")

        context["generated_voices"] = generated_assets
        return context
