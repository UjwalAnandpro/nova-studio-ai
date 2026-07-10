import sqlite3
import os
import threading
from contextlib import contextmanager
from typing import Generator
from core.config.manager import settings_manager
from core.logger.custom_logger import log_action

class DatabaseManager:
    """
    Manages the application's SQLite database connection and schema.
    Thread-safe connection pool/context manager using a threading lock.
    """
    def __init__(self):
        self.lock = threading.Lock()
        # Database file location in the storage directory
        self.db_path = os.path.join(settings_manager.settings.storage_path, "nova_studio.db")
        self.initialized = False
        self.initialize_db()

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Provides a thread-safe connection to the SQLite database."""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()

    def initialize_db(self):
        """Initializes database tables if they do not exist."""
        if self.initialized:
            return
            
        try:
            # Ensure parent storage directory exists
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Projects Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS projects (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        description TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        path TEXT NOT NULL,
                        duration REAL DEFAULT 0.0,
                        status TEXT DEFAULT 'draft'
                    )
                """)
                
                # Cache Index Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS cache_index (
                        key_hash TEXT PRIMARY KEY,
                        asset_type TEXT NOT NULL,
                        file_path TEXT NOT NULL,
                        size_bytes INTEGER NOT NULL,
                        created_at TEXT NOT NULL,
                        hit_count INTEGER DEFAULT 0
                    )
                """)
                
                # Plugin Registry Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS plugin_registry (
                        name TEXT PRIMARY KEY,
                        type TEXT NOT NULL,
                        description TEXT,
                        enabled INTEGER DEFAULT 1,
                        config TEXT
                    )
                """)
                
                # Prompt History Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS prompt_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        project_id TEXT,
                        workflow_name TEXT,
                        prompt_text TEXT NOT NULL,
                        variables TEXT,
                        seed INTEGER,
                        created_at TEXT NOT NULL,
                        favorite INTEGER DEFAULT 0
                    )
                """)

                # Workflow Favorites Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS workflow_favorites (
                        workflow_name TEXT PRIMARY KEY,
                        pinned INTEGER DEFAULT 0,
                        favorite INTEGER DEFAULT 0,
                        last_used TEXT
                    )
                """)

                # Asset Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS assets (
                        id TEXT PRIMARY KEY,
                        project_id TEXT NOT NULL,
                        workflow_name TEXT NOT NULL,
                        prompt TEXT,
                        seed INTEGER,
                        model_used TEXT,
                        file_path TEXT NOT NULL,
                        file_size INTEGER NOT NULL,
                        resolution TEXT,
                        created_at TEXT NOT NULL
                    )
                """)
                
                # Character Profiles Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS character_profiles (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        gender TEXT,
                        age INTEGER,
                        hair TEXT,
                        eyes TEXT,
                        skin_tone TEXT,
                        clothing TEXT,
                        accessories TEXT,
                        reference_images TEXT,
                        expression_library TEXT,
                        style TEXT
                    )
                """)

                # Style Profiles Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS style_profiles (
                        name TEXT PRIMARY KEY,
                        base_prompt TEXT NOT NULL,
                        negative_prompt TEXT,
                        cfg REAL DEFAULT 7.5,
                        sampler TEXT DEFAULT 'euler',
                        steps INTEGER DEFAULT 20
                    )
                """)

                # Generation Cache Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS generation_cache (
                        prompt_hash TEXT PRIMARY KEY,
                        asset_path TEXT NOT NULL,
                        seed INTEGER,
                        created_at TEXT NOT NULL
                    )
                """)

                # Audio Assets Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS audio_assets (
                        id TEXT PRIMARY KEY,
                        provider TEXT NOT NULL,
                        voice TEXT NOT NULL,
                        language TEXT NOT NULL,
                        emotion TEXT,
                        duration REAL,
                        sample_rate INTEGER,
                        bitrate INTEGER,
                        file_size INTEGER,
                        created_at TEXT NOT NULL,
                        hash TEXT NOT NULL
                    )
                """)

                # Voice Library Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS voice_library (
                        id TEXT PRIMARY KEY,
                        provider TEXT NOT NULL,
                        name TEXT NOT NULL,
                        gender TEXT,
                        accent TEXT,
                        emotion TEXT,
                        sample_rate INTEGER,
                        preview_path TEXT
                    )
                """)

                # Project Notes Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS project_notes (
                        project_id TEXT PRIMARY KEY,
                        notes TEXT NOT NULL
                    )
                """)
                
                conn.commit()
                self.initialized = True
                log_action("Database", "InitDB", "SUCCESS", 0.0, f"Database initialized at {self.db_path}")
        except Exception as e:
            log_action("Database", "InitDB", "FAILED", 0.0, f"Database initialization failed: {str(e)}")

    def optimize_database(self) -> bool:
        """Runs SQLite vacuum, index analyze and integrity diagnostics checks."""
        try:
            with self.get_connection() as conn:
                conn.execute("VACUUM")
                conn.execute("ANALYZE")
                cursor = conn.execute("PRAGMA integrity_check")
                res = cursor.fetchone()[0]
                if res == "ok":
                    log_action("Database", "OptimizeDB", "SUCCESS", 0.0, "Database optimized successfully.")
                    return True
                else:
                    log_action("Database", "OptimizeDB", "WARNING", 0.0, f"Integrity status reported warning: {res}")
                    return False
        except Exception as e:
            log_action("Database", "OptimizeDB", "FAILED", 0.0, f"Database optimization failed: {str(e)}")
            return False

# Singleton instance of DatabaseManager
db_manager = DatabaseManager()
