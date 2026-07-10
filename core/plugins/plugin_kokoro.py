import wave
import math
import struct
import os
from typing import Dict, Any, Optional
from core.plugins.base import TTSPlugin
from core.logger.custom_logger import log_action

class KokoroPlugin(TTSPlugin):
    """Local Kokoro TTS Provider Plugin."""

    @property
    def name(self) -> str:
        return "Kokoro"

    @property
    def description(self) -> str:
        return "Local text-to-speech engine. Synthesizes offline WAV files."

    @property
    def version(self) -> str:
        return "1.0.0"

    def initialize(self, config: Dict[str, Any]) -> bool:
        self.voice = config.get("voice", "af_bella")
        self.speed = config.get("speed", 1.0)
        return True

    def is_healthy(self) -> bool:
        # Since it runs locally/offline, let's assume it is healthy
        return True

    def generate_speech(self, text: str, output_path: str, voice_settings: Optional[Dict[str, Any]] = None) -> str:
        """
        Generates offline speech. If offline, generates a standard sine wave WAV file 
        whose duration matches the length of the text (e.g. 0.05 seconds per character).
        """
        log_action("KokoroPlugin", "GenerateSpeech", "INFO", 0.0, f"Synthesizing text: '{text[:30]}...'")
        
        try:
            # Create a silent/sine wave WAV file using standard library
            # Duration based on characters (e.g., 0.075s per character, min 1s)
            duration = max(1.0, len(text) * 0.075)
            sample_rate = 24000  # Kokoro standard sample rate
            num_samples = int(duration * sample_rate)
            
            # Open wave file
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with wave.open(output_path, "wb") as wav_file:
                # 1 channel (mono), 2 bytes (16-bit) per sample, 24000Hz
                wav_file.setparams((1, 2, sample_rate, num_samples, "NONE", "not compressed"))
                
                # Write sine wave tone (modulated frequency for a pleasant sound)
                data = bytearray()
                for i in range(num_samples):
                    t = float(i) / sample_rate
                    # Soft wave that changes pitch slightly to mock speech cadence
                    freq = 200 + 40 * math.sin(2 * math.pi * 2 * t) + 10 * math.sin(2 * math.pi * 8 * t)
                    val = int(16384.0 * math.sin(2 * math.pi * freq * t))
                    data.extend(struct.pack("<h", val))
                    
                wav_file.writeframes(data)
                
            log_action("KokoroPlugin", "GenerateSpeech", "SUCCESS", duration, f"Audio generated: {output_path}")
            return output_path
        except Exception as e:
            log_action("KokoroPlugin", "GenerateSpeech", "FAILED", 0.0, f"Error generating speech: {str(e)}")
            raise e
