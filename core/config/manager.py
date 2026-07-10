import os
import json
from typing import Optional
from core.models.settings import Settings
from core.logger.custom_logger import log_action

class SettingsManager:
    """
    Manages loading, validation, saving and paths translation of application settings.
    """
    def __init__(self, config_dir: Optional[str] = None):
        if config_dir is None:
            # Default to core/config
            config_dir = os.path.dirname(os.path.abspath(__file__))
            
        self.config_dir = config_dir
        self.settings_file = os.path.join(self.config_dir, "settings.json")
        self.settings: Settings = Settings()
        self.load_settings()

    def load_settings(self) -> Settings:
        """Loads settings from settings.json or initializes defaults if not found."""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.settings = Settings(**data)
                log_action("Config", "LoadSettings", "SUCCESS", 0.0, f"Settings loaded from {self.settings_file}")
            else:
                log_action("Config", "LoadSettings", "WARNING", 0.0, "Settings file not found. Creating default settings.")
                self.save_settings()
        except Exception as e:
            log_action("Config", "LoadSettings", "FAILED", 0.0, f"Error loading settings: {str(e)}. Using defaults.")
            self.settings = Settings()
            
        # Ensure all directory paths are resolved to absolute based on the app root directory
        app_root = os.path.abspath(os.path.join(self.config_dir, "..", ".."))
        self.settings.make_paths_absolute(app_root)
        self.ensure_dirs_exist()
        return self.settings

    def save_settings(self, settings: Optional[Settings] = None) -> bool:
        """Saves settings to settings.json."""
        if settings is not None:
            self.settings = settings
            
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            with open(self.settings_file, "w", encoding="utf-8") as f:
                # Use model_dump_json or model_dump
                f.write(self.settings.model_dump_json(indent=4))
            log_action("Config", "SaveSettings", "SUCCESS", 0.0, f"Settings saved to {self.settings_file}")
            return True
        except Exception as e:
            log_action("Config", "SaveSettings", "FAILED", 0.0, f"Error saving settings: {str(e)}")
            return False

    def ensure_dirs_exist(self):
        """Ensures all designated directories in the settings actually exist on disk."""
        dirs_to_create = [
            self.settings.storage_path,
            self.settings.cache_path,
            self.settings.project_path,
            self.settings.temp_path,
            self.settings.output_path
        ]
        for d in dirs_to_create:
            try:
                os.makedirs(d, exist_ok=True)
            except Exception as e:
                log_action("Config", "EnsureDirsExist", "FAILED", 0.0, f"Error creating directory {d}: {str(e)}")

# Singleton instance of SettingsManager
settings_manager = SettingsManager()
