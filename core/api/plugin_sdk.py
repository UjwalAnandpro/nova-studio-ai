from typing import List, Dict, Any, Tuple
from core.plugins.base import BasePlugin

class PluginPermissions:
    """Explicit declaration of system capabilities requested by the plugin."""
    def __init__(self, filesystem: bool = False, network: bool = False, 
                 gpu: bool = False, external_processes: bool = False):
        self.filesystem = filesystem
        self.network = network
        self.gpu = gpu
        self.external_processes = external_processes

    def to_dict(self) -> Dict[str, bool]:
        return {
            "filesystem": self.filesystem,
            "network": self.network,
            "gpu": self.gpu,
            "external_processes": self.external_processes
        }

class SDKPlugin(BasePlugin):
    """
    Standard base class representing plugins registered via the SDK.
    Defines sandboxing permissions and full lifecycles.
    """
    def __init__(self, name: str, version: str, plugin_type: str, description: str = ""):
        self._name = name
        self._version = version
        self._plugin_type = plugin_type
        self._description = description
        self.permissions = PluginPermissions()
        self.enabled = True

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def version(self) -> str:
        return self._version

    @property
    def plugin_type(self) -> str:
        return self._plugin_type

    def initialize(self) -> bool:
        """Called upon first registration loader boot."""
        return True

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False

    def unload(self):
        """Called prior to plugin removal."""
        pass

# Category Specific Provider Abstractions
class VoiceProvider(SDKPlugin):
    def __init__(self, name: str, version: str, description: str = ""):
        super().__init__(name, version, "tts", description)

    def generate_speech(self, text: str, output_path: str, voice: str = "Default", speed: float = 1.0):
        raise NotImplementedError("Plugins must override generate_speech method.")

class ImageProvider(SDKPlugin):
    def __init__(self, name: str, version: str, description: str = ""):
        super().__init__(name, version, "image", description)

    def generate_image(self, prompt: str, output_path: str, size: str = "1024x1024"):
        raise NotImplementedError("Plugins must override generate_image method.")

class MusicProvider(SDKPlugin):
    def __init__(self, name: str, version: str, description: str = ""):
        super().__init__(name, version, "music", description)

    def generate_music(self, prompt: str, output_path: str, duration: float = 10.0):
        raise NotImplementedError("Plugins must override generate_music method.")

class SubtitleProvider(SDKPlugin):
    def __init__(self, name: str, version: str, description: str = ""):
        super().__init__(name, version, "subtitle", description)

    def compile_subtitles(self, dialogue_clips: List[Dict[str, Any]], format_type: str) -> str:
        raise NotImplementedError("Plugins must override compile_subtitles method.")
