import requests
from typing import Dict, Any, Optional
from core.plugins.base import LLMPlugin
from core.logger.custom_logger import log_action

class OllamaPlugin(LLMPlugin):
    """Local Ollama LLM Provider Plugin."""

    @property
    def name(self) -> str:
        return "Ollama"

    @property
    def description(self) -> str:
        return "Offline local LLM text generator via Ollama endpoint."

    @property
    def version(self) -> str:
        return "1.0.0"

    def initialize(self, config: Dict[str, Any]) -> bool:
        self.address = config.get("address", "http://127.0.0.1:11434")
        self.model = config.get("model", "llama3")
        return True

    def is_healthy(self) -> bool:
        try:
            r = requests.get(f"{self.address}/api/tags", timeout=1.0)
            return r.status_code == 200
        except Exception:
            return False

    def generate_text(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        if not self.is_healthy():
            log_action("OllamaPlugin", "GenerateText", "WARNING", 0.0, "Ollama is offline. Returning local mock script.")
            return (
                "## Chapter 1: The Spark\n"
                "In a world where intelligence operates at local scale, Antigravity emerged.\n"
                "Visual: Sleek server rack flashing blue, transitions into a neural network graph.\n\n"
                "## Chapter 2: The Next Horizon\n"
                "Modular code bases, plugin-driven rendering, and direct GPU access.\n"
                "Visual: A developer writing code with an elegant dashboard showing 100% GPU workload.\n\n"
                "## Chapter 3: Infinite Creativity\n"
                "Offline synthesis of voice, video, and music in seconds.\n"
                "Visual: A beautiful final rendering completed popup in a clean dark UI."
            )
            
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False
            }
            if system_prompt:
                payload["system"] = system_prompt
                
            r = requests.post(f"{self.address}/api/generate", json=payload, timeout=30.0)
            if r.status_code == 200:
                return r.json().get("response", "")
            else:
                raise Exception(f"HTTP Status {r.status_code}: {r.text}")
        except Exception as e:
            log_action("OllamaPlugin", "GenerateText", "FAILED", 0.0, f"Ollama generation failed: {str(e)}")
            return "Failed to generate script via Ollama."
