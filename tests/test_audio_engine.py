import unittest
import os
import sys
import wave

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.projects.manager import project_manager
from core.audio.voice import voice_manager
from core.audio.music import audio_mixer
from core.audio.subtitles import subtitle_engine
from core.audio.timing import timing_engine, waveform_generator, lip_sync_preparer

class TestAudioEngine(unittest.TestCase):

    def setUp(self):
        # Create a mock project for testing
        self.proj_name = "Audio Test Proj"
        self.meta = project_manager.create_project(self.proj_name, "Testing voiceover, mixing and visemes")
        self.proj_dir = project_manager.get_project_dir(self.meta.id)
        
        # Build mock dialogue clips
        self.clips = [
            {
                "start": 0.0,
                "end": 2.5,
                "text": "Hello world.",
                "words": [
                    {"word": "Hello", "duration": 1.2},
                    {"word": "world", "duration": 1.3}
                ]
            },
            {
                "start": 3.0,
                "end": 6.5,
                "text": "This is a timing sync test.",
                "words": [
                    {"word": "This", "duration": 0.7},
                    {"word": "is", "duration": 0.5},
                    {"word": "a", "duration": 0.4},
                    {"word": "timing", "duration": 0.8},
                    {"word": "sync", "duration": 0.5},
                    {"word": "test", "duration": 0.6}
                ]
            }
        ]

    def tearDown(self):
        # Clean up
        project_manager.delete_project(self.meta.id)

    def test_sentence_script_splitting(self):
        """Verifies script splitting handles basic punctuation correctly."""
        text = "Hello! This is a test. Is this correct? Yes."
        sentences = voice_manager.split_script_into_sentences(text)
        self.assertEqual(len(sentences), 4)
        self.assertEqual(sentences[0], "Hello!")
        self.assertEqual(sentences[1], "This is a test.")

    def test_audio_validator(self):
        """Tests the WAV structure validator detects corrupt files."""
        bad_path = os.path.join(self.proj_dir, "bad.wav")
        
        # Write dummy corrupt file
        with open(bad_path, "w") as f:
            f.write("corrupted data" * 15)
            
        valid, err = voice_manager.validate_audio(bad_path)
        self.assertFalse(valid)
        self.assertIn("WAV", err)
        
        # Write valid silence wav file
        good_path = os.path.join(self.proj_dir, "good.wav")
        with wave.open(good_path, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(24000)
            # Write 1 second of silence
            wav.writeframes(b"\x00" * 48000)
            
        valid_good, err_good = voice_manager.validate_audio(good_path)
        self.assertTrue(valid_good)

    def test_subtitle_compilation(self):
        """Tests compiling SRT, VTT, and ASS dialogue strings."""
        # Test SRT
        srt = subtitle_engine.generate_srt(self.clips)
        self.assertIn("00:00:00,000 --> 00:00:02,500", srt)
        self.assertIn("Hello world.", srt)
        
        # Test VTT
        vtt = subtitle_engine.generate_vtt(self.clips)
        self.assertIn("WEBVTT", vtt)
        self.assertIn("00:00:03.000 --> 00:00:06.500", vtt)
        
        # Test ASS with styling presets (TikTok style)
        ass = subtitle_engine.generate_ass(self.clips, style_preset="TikTok")
        self.assertIn("[Script Info]", ass)
        self.assertIn("Default,Montserrat,28", ass)
        # Check karaoke tag output: \k
        self.assertIn("\\k120Hello", ass)

    def test_audio_ducking_filter_builder(self):
        """Tests dynamic creation of FFmpeg sidechain volume expression check strings."""
        intervals = [(1.0, 4.0), (6.2, 9.5)]
        duck_expr = audio_mixer.build_ducking_filter(intervals, duck_ratio=0.15, default_vol=0.8)
        
        self.assertIn("between(t,1.00,4.00)", duck_expr)
        self.assertIn("between(t,6.20,9.50)", duck_expr)
        # Ducked level calculation: default_vol * duck_ratio = 0.8 * 0.15 = 0.12
        self.assertIn("0.120", duck_expr)
        self.assertIn("0.800", duck_expr)

    def test_lip_sync_visemes(self):
        """Tests compilation of phoneme character alignments into visemes."""
        data = lip_sync_preparer.prepare_lip_sync_data(self.clips, speaker_id="Bella")
        
        self.assertEqual(data["speaker_id"], "Bella")
        self.assertGreater(len(data["viseme_track"]), 0)
        
        # Check that 'h' resolves to 'sil' or character mappings, e.g. first char of hello 'h'
        first_item = data["viseme_track"][0]
        self.assertIn("start_time", first_item)
        self.assertIn("viseme", first_item)

if __name__ == "__main__":
    unittest.main()
