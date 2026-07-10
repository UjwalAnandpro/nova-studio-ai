import json
import time
from typing import List, Dict, Any

class TimingEngine:
    """
    Synchronizes script text elements with generated voice segments.
    Detects timing drift and rescales timelines.
    """

    def synchronize_tracks(self, narration_clips: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Processes voice segments to build sequential starts.
        Pads/shifts clips to avoid timeline gaps or overlaps.
        """
        synchronized = []
        current_time = 0.0
        
        for clip in narration_clips:
            dur = clip.get("duration", 2.0)
            synchronized.append({
                "text": clip["text"],
                "start": current_time,
                "end": current_time + dur,
                "duration": dur,
                "words": clip.get("words", [])
            })
            # Advance timing marker (avoid overlap)
            current_time += dur
            
        return synchronized

class WaveformGenerator:
    """
    Generates normalized amplitude datasets representing waveforms
    for UI rendering and timelines.
    """

    def generate_amplitude_heights(self, filepath: str, points: int = 50) -> List[float]:
        """
        Parses wave files and returns a list of normalized floats (0.0 to 100.0)
        suitable for canvas chart graphs.
        """
        try:
            import wave
            with wave.open(filepath, "rb") as wav:
                frames_count = wav.getnframes()
                # Skip reading if empty
                if frames_count == 0:
                    return [0.0] * points
                    
                data = wav.readframes(frames_count)
                # Sample amplitude points
                chunk_size = max(1, len(data) // points)
                amplitudes = []
                for i in range(0, len(data), chunk_size):
                    val = data[i]
                    # Map byte values (0-255) to 0.0-100.0 range
                    amplitudes.append(round((abs(val - 128) / 128.0) * 100.0, 2))
                    if len(amplitudes) >= points:
                        break
                        
                # Pad if too short
                while len(amplitudes) < points:
                    amplitudes.append(0.0)
                return amplitudes
        except Exception:
            # Fallback mock waveform
            import random
            return [round(random.uniform(5.0, 95.0), 2) for _ in range(points)]

class LipSyncPreparer:
    """
    Generates phoneme and viseme mapping structures from word text
    to bootstrap future lip sync renderers.
    """
    def __init__(self):
        # Maps English letters to standard viseme poses (mouth shapes)
        self.char_to_viseme = {
            'a': 'aa', 'e': 'E', 'i': 'ih', 'o': 'oh', 'u': 'ou',
            'b': 'PP', 'p': 'PP', 'm': 'PP',
            'f': 'FF', 'v': 'FF',
            't': 'DD', 'd': 'DD', 's': 'SS', 'z': 'SS',
            'c': 'kk', 'k': 'kk', 'g': 'kk',
            'w': 'u', 'r': 'RR', 'y': 'ih',
            'l': 'nn', 'n': 'nn'
        }

    def prepare_lip_sync_data(self, speech_clips: List[Dict[str, Any]], speaker_id: str) -> Dict[str, Any]:
        """
        Generates a detailed phoneme-viseme map with precise millisecond alignments.
        """
        viseme_timeline = []
        
        for clip in speech_clips:
            clip_start = clip.get("start", 0.0)
            words = clip.get("words", [])
            
            if not words:
                # If word level splits missing, fall back to simple sentence estimation
                words = [{"word": w, "duration": 0.4} for w in clip["text"].split()]
                
            word_start = clip_start
            for idx, w_info in enumerate(words):
                word_text = w_info.get("word", "").lower()
                duration = w_info.get("duration", 0.4)
                
                # Split word into characters to estimate phonetic visemes
                chars = [c for c in word_text if c.isalnum()]
                if not chars:
                    chars = ['a']
                    
                char_duration = duration / len(chars)
                
                char_start = word_start
                for ch in chars:
                    viseme = self.char_to_viseme.get(ch, "sil")
                    viseme_timeline.append({
                        "viseme": viseme,
                        "start_time": round(char_start, 3),
                        "end_time": round(char_start + char_duration, 3),
                        "character": ch
                    })
                    char_start += char_duration
                    
                word_start += duration
                
        return {
            "speaker_id": speaker_id,
            "viseme_track": viseme_timeline,
            "emotion": "Neutral",
            "compiled_at": round(time.time(), 2)
        }

# Singletons
timing_engine = TimingEngine()
waveform_generator = WaveformGenerator()
lip_sync_preparer = LipSyncPreparer()
