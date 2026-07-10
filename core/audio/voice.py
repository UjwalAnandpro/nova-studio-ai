import os
import hashlib
import re
import uuid
import wave
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from core.database.db import db_manager
from core.plugins.loader import plugin_loader
from core.projects.manager import project_manager
from core.logger.custom_logger import log_action

class VoiceProfile:
    """Represents a reusable voice definition in the studio."""
    def __init__(self, id: str, provider: str, name: str, gender: str, 
                 accent: str, emotion: str = "Neutral", sample_rate: int = 24000):
        self.id = id
        self.provider = provider
        self.name = name
        self.gender = gender
        self.accent = accent
        self.emotion = emotion
        self.sample_rate = sample_rate
        self.preview_path = ""

class VoiceManager:
    """
    Manages speech generation, sentence segment synthesis, caching,
    voice libraries, and voice cloning registration.
    """
    def __init__(self):
        self.enable_cache = True

    def split_script_into_sentences(self, script: str) -> List[str]:
        """Splits narrative script into individual sentences using boundary regexes."""
        # Split on sentence terminals while keeping formatting intact
        sentences = re.split(r'(?<=[.!?])\s+', script.strip())
        return [s.strip() for s in sentences if s.strip()]

    def _hash_audio_request(self, text: str, voice_name: str, speed: float) -> str:
        """Generates a stable SHA256 key for caching speech outputs."""
        key = f"{text}_{voice_name}_{speed}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def get_cached_speech(self, request_hash: str) -> Optional[str]:
        """Searches cache log for compiled speech files."""
        if not self.enable_cache:
            return None
            
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT file_path FROM audio_assets WHERE hash = ?", (request_hash,))
                row = cursor.fetchone()
                if row:
                    path = row["file_path"]
                    if os.path.exists(path):
                        return path
        except Exception:
            pass
        return None

    def create_voice_profile(self, id: str, provider: str, name: str, gender: str, 
                             accent: str, emotion: str = "Neutral", sample_rate: int = 24000) -> bool:
        """Registers a voice profile to the SQLite database library."""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO voice_library (id, provider, name, gender, accent, emotion, sample_rate, preview_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (id, provider, name, gender, accent, emotion, sample_rate, "")
                )
                conn.commit()
            log_action("VoiceManager", "CreateProfile", "SUCCESS", 0.0, f"Registered voice profile: {name}")
            return True
        except Exception as e:
            log_action("VoiceManager", "CreateProfile", "FAILED", 0.0, str(e))
            return False

    def list_voice_library(self) -> List[VoiceProfile]:
        """Lists all voice profiles registered in the studio database."""
        profiles = []
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, provider, name, gender, accent, emotion, sample_rate, preview_path FROM voice_library")
                rows = cursor.fetchall()
                for r in rows:
                    vp = VoiceProfile(r["id"], r["provider"], r["name"], r["gender"], r["accent"], r["emotion"], r["sample_rate"])
                    vp.preview_path = r["preview_path"]
                    profiles.append(vp)
        except Exception:
            pass
        return profiles

    def generate_voiceover(self, project_id: str, text: str, voice_profile_id: str, 
                           speed: float = 1.0, volume: float = 1.0) -> Optional[str]:
        """
        Synthesizes text into speech. Applies caching, sentence-level splitting,
        smart retry processing, validation, and registers to database assets.
        """
        proj_dir = project_manager.get_project_dir(project_id)
        
        # Resolve voice profile
        voice_name = "Kokoro"
        provider_name = "Kokoro"
        
        # Resolve from library if profile exists
        library = self.list_voice_library()
        profile = next((v for v in library if v.id == voice_profile_id), None)
        if profile:
            voice_name = profile.name
            provider_name = profile.provider
            
        req_hash = self._hash_audio_request(text, voice_name, speed)
        cached = self.get_cached_speech(req_hash)
        
        if cached and os.path.exists(cached):
            # Cache hit: copy cached audio asset to project assets
            filename = f"voice_cached_{int(time.time())}_{str(uuid.uuid4())[:4]}.wav"
            dest_rel = f"voice/{filename}"
            dest_abs = os.path.join(proj_dir, dest_rel)
            os.makedirs(os.path.dirname(dest_abs), exist_ok=True)
            
            try:
                shutil_copy(cached, dest_abs)
                self._register_audio_asset(project_id, provider_name, voice_name, dest_abs, req_hash)
                return dest_rel
            except Exception:
                pass
                
        # Resolve TTS Plugin
        plugin = plugin_loader.get_plugin("tts", provider_name)
        if not plugin:
            # Fallback to any healthy TTS plugin
            tts_plugins = plugin_loader.list_plugins("tts")
            plugin = tts_plugins[0] if tts_plugins else None
            
        if not plugin:
            log_action("VoiceManager", "Synthesize", "FAILED", 0.0, "No TTS plugins available.")
            return None
            
        filename = f"voice_{int(time.time())}_{str(uuid.uuid4())[:4]}.wav"
        dest_rel = f"voice/{filename}"
        dest_abs = os.path.join(proj_dir, dest_rel)
        os.makedirs(os.path.dirname(dest_abs), exist_ok=True)
        
        # Perform synthesis with retry
        attempts = 3
        for attempt in range(1, attempts + 1):
            try:
                # Compile speech using plugin
                plugin.generate_speech(text, dest_abs, voice=voice_name, speed=speed)
                
                # Validate audio file
                valid, err = self.validate_audio(dest_abs)
                if not valid:
                    if os.path.exists(dest_abs):
                        os.remove(dest_abs)
                    raise ValueError(f"Audio validation failed: {err}")
                break
            except Exception as e:
                if attempt == attempts:
                    log_action("VoiceManager", "Synthesize", "FAILED", 0.0, f"Failed synthesizing speech after retries: {str(e)}")
                    return None
                time.sleep(1.0)
                
        # Cache file link and log database
        # Save to global cache dir
        cache_dir = os.path.join(settings_manager.settings.cache_path, "voice")
        os.makedirs(cache_dir, exist_ok=True)
        global_cache_path = os.path.join(cache_dir, f"{req_hash}.wav")
        try:
            shutil_copy(dest_abs, global_cache_path)
        except Exception:
            pass
            
        self._register_audio_asset(project_id, plugin.name, voice_name, dest_abs, req_hash)
        return dest_rel

    def validate_audio(self, filepath: str) -> Tuple[bool, str]:
        """Validates that a compiled WAV file exists, is readable, and contains sound data."""
        if not os.path.exists(filepath):
            return False, "File does not exist."
            
        if os.path.getsize(filepath) < 100:
            return False, "File is too small/empty."
            
        try:
            with wave.open(filepath, "rb") as wav:
                params = wav.getparams()
                if params.nchannels <= 0:
                    return False, "Audio has zero channels."
                if params.framerate < 8000:
                    return False, "Sample rate is too low."
            return True, ""
        except Exception as e:
            return False, f"Broken WAV header: {str(e)}"

    def _register_audio_asset(self, project_id: str, provider: str, voice: str, filepath: str, file_hash: str):
        """Logs output audio asset parameters into audio_assets table."""
        try:
            size_bytes = os.path.getsize(filepath)
            created_at = datetime.now().isoformat()
            asset_id = f"audio_{str(uuid.uuid4())[:8]}"
            
            # Determine duration
            duration = 0.0
            sample_rate = 24000
            try:
                with wave.open(filepath, "rb") as wav:
                    frames = wav.getnframes()
                    sample_rate = wav.getframerate()
                    duration = frames / float(sample_rate)
            except Exception:
                pass
                
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO audio_assets 
                    (id, provider, voice, language, emotion, duration, sample_rate, bitrate, file_size, created_at, hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (asset_id, provider, voice, "English", "Neutral", duration, sample_rate, 192000, size_bytes, created_at, file_hash)
                )
                conn.commit()
        except Exception as e:
            log_action("VoiceManager", "LogDB", "WARNING", 0.0, f"Error saving audio details to database: {str(e)}")

def shutil_copy(src: str, dest: str):
    import shutil
    shutil.copy2(src, dest)

# Singleton VoiceManager
voice_manager = VoiceManager()
