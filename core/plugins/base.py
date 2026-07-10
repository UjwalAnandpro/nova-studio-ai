from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BasePlugin(ABC):
    """Base class for all Nova Studio AI plugins."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique plugin name (e.g. 'Ollama', 'Kokoro', 'ComfyUI')."""
        pass
        
    @property
    @abstractmethod
    def description(self) -> str:
        """Brief description of what the plugin does."""
        pass
        
    @property
    @abstractmethod
    def version(self) -> str:
        """Plugin version string."""
        pass
        
    @property
    @abstractmethod
    def plugin_type(self) -> str:
        """Type of plugin (llm, tts, image, video, music)."""
        pass

    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initializes plugin with its specific config dictionary."""
        return True

    def is_healthy(self) -> bool:
        """Checks if the external API, dependency or provider is online/accessible."""
        return True


class LLMPlugin(BasePlugin):
    """Interface for text script generators."""
    
    @property
    def plugin_type(self) -> str:
        return "llm"

    @abstractmethod
    def generate_text(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        """Generates text from prompt."""
        pass


class TTSPlugin(BasePlugin):
    """Interface for text-to-speech voice generators."""

    @property
    def plugin_type(self) -> str:
        return "tts"

    @abstractmethod
    def generate_speech(self, text: str, output_path: str, voice_settings: Optional[Dict[str, Any]] = None) -> str:
        """Generates speech file from text and saves to output_path. Returns the output_path."""
        pass


class ImagePlugin(BasePlugin):
    """Interface for image generators."""

    @property
    def plugin_type(self) -> str:
        return "image"

    @abstractmethod
    def generate_image(self, prompt: str, output_path: str, size: Optional[str] = None, **kwargs) -> str:
        """Generates image file from prompt and saves to output_path. Returns the output_path."""
        pass


class VideoPlugin(BasePlugin):
    """Interface for video generators."""

    @property
    def plugin_type(self) -> str:
        return "video"

    @abstractmethod
    def generate_video(self, prompt_or_image_path: str, output_path: str, duration: float = 4.0, **kwargs) -> str:
        """Generates video clip from prompt/image and saves to output_path. Returns the output_path."""
        pass


class MusicPlugin(BasePlugin):
    """Interface for background music generators."""

    @property
    def plugin_type(self) -> str:
        return "music"

    @abstractmethod
    def generate_music(self, prompt: str, output_path: str, duration: float = 10.0, **kwargs) -> str:
        """Generates music audio file from prompt and saves to output_path. Returns the output_path."""
        pass
