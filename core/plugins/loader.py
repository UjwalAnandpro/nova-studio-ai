import os
import sys
import importlib.util
import inspect
from typing import Dict, List, Optional, Type, Any
from core.plugins.base import BasePlugin
from core.logger.custom_logger import log_action
from core.database.db import db_manager

class PluginLoader:
    """
    Dynamically loads and registers plugins from plugin files.
    Scans files that subclass BasePlugin.
    """
    def __init__(self, plugin_dirs: Optional[List[str]] = None):
        import json
        if plugin_dirs is None:
            # Default to core/plugins directory
            plugin_dirs = [os.path.dirname(os.path.abspath(__file__))]
            
        self.plugin_dirs = plugin_dirs
        self.root_plugins_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "plugins")
        self.plugins: Dict[str, Dict[str, BasePlugin]] = {
            "llm": {},
            "tts": {},
            "image": {},
            "video": {},
            "music": {}
        }
        self.load_all_plugins()

    def get_plugin(self, plugin_type: str, name: str) -> Optional[BasePlugin]:
        """Gets a loaded plugin by its type and name."""
        pt = plugin_type.lower()
        if pt in self.plugins:
            return self.plugins[pt].get(name)
        return None

    def list_plugins(self, plugin_type: Optional[str] = None) -> List[BasePlugin]:
        """Lists plugins, optionally filtered by type."""
        result = []
        if plugin_type:
            pt = plugin_type.lower()
            if pt in self.plugins:
                result.extend(self.plugins[pt].values())
        else:
            for pt_dict in self.plugins.values():
                result.extend(pt_dict.values())
        return result

    def register_plugin_instance(self, plugin: BasePlugin) -> bool:
        """Helper to register a plugin instance in-memory and database."""
        pt = plugin.plugin_type.lower()
        if pt not in self.plugins:
            self.plugins[pt] = {}
            
        self.plugins[pt][plugin.name] = plugin
        
        # Save to DB registry
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO plugin_registry (name, type, description, enabled, config)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (plugin.name, pt, plugin.description, 1, "{}")
                )
                conn.commit()
        except Exception as e:
            log_action("Plugins", "RegisterDB", "WARNING", 0.0, f"Could not sync plugin {plugin.name} to DB registry: {str(e)}")
            
        return True

    def load_all_plugins(self):
        """Scans plugin directories and loads Python files matching plugin_*.py."""
        import json
        log_action("Plugins", "LoadAll", "INFO", 0.0, "Starting dynamic plugin discovery...")
        
        # 1. Load legacy plugin_*.py files
        for directory in self.plugin_dirs:
            if not os.path.exists(directory):
                continue
                
            for filename in os.listdir(directory):
                if filename.startswith("plugin_") and filename.endswith(".py"):
                    file_path = os.path.join(directory, filename)
                    self._load_plugin_file(file_path)

        # 2. Load SDK folders with plugin.json
        if os.path.exists(self.root_plugins_dir):
            for folder in os.listdir(self.root_plugins_dir):
                folder_path = os.path.join(self.root_plugins_dir, folder)
                if not os.path.isdir(folder_path):
                    continue
                
                json_path = os.path.join(folder_path, "plugin.json")
                main_path = os.path.join(folder_path, "main.py")
                if os.path.exists(json_path) and os.path.exists(main_path):
                    self._load_sdk_plugin_folder(folder_path, json_path, main_path)

    def _load_sdk_plugin_folder(self, folder_path: str, json_path: str, main_path: str):
        import json
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            
            module_name = f"plugin_{os.path.basename(folder_path)}"
            spec = importlib.util.spec_from_file_location(module_name, main_path)
            if spec is None or spec.loader is None:
                return
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, BasePlugin) and obj is not BasePlugin and obj.__module__ == module_name:
                    instance = obj()
                    instance.permissions = meta.get("permissions", {})
                    if self.register_plugin_instance(instance):
                        log_action("Plugins", "LoadSDKFolder", "SUCCESS", 0.0, f"Loaded SDK folder plugin '{instance.name}' ({instance.plugin_type})")
                        break
        except Exception as e:
            log_action("Plugins", "LoadSDKFolder", "FAILED", 0.0, f"Failed loading SDK folder plugin: {str(e)}")

    def _load_plugin_file(self, file_path: str):
        module_name = os.path.splitext(os.path.basename(file_path))[0]
        try:
            # Setup spec and import module
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec is None or spec.loader is None:
                return
                
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # Inspect module to find BasePlugin subclasses
            plugin_classes_found = 0
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, BasePlugin) and obj is not BasePlugin:
                    # Exclude the direct abstract interfaces
                    if obj.__name__ in ("LLMPlugin", "TTSPlugin", "ImagePlugin", "VideoPlugin", "MusicPlugin"):
                        continue
                        
                    # Instantiate and register
                    try:
                        instance = obj()
                        if self.register_plugin_instance(instance):
                            plugin_classes_found += 1
                            log_action("Plugins", "LoadFile", "SUCCESS", 0.0, 
                                       f"Loaded plugin '{instance.name}' ({instance.plugin_type}) from {file_path}")
                    except Exception as inst_err:
                        log_action("Plugins", "LoadFile", "FAILED", 0.0, 
                                   f"Failed to instantiate plugin class {obj.__name__} in {file_path}: {str(inst_err)}")
                                   
            if plugin_classes_found == 0:
                log_action("Plugins", "LoadFile", "WARNING", 0.0, f"No valid plugins found in {file_path}")
                
        except Exception as e:
            log_action("Plugins", "LoadFile", "FAILED", 0.0, f"Failed to load plugin module {module_name} from {file_path}: {str(e)}")

# Singleton instance of PluginLoader
plugin_loader = PluginLoader()
