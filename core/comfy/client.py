import aiohttp
import json
from typing import Dict, Any, Optional
from core.logger.custom_logger import log_action

class ComfyClient:
    """
    Asynchronous client wrapper for ComfyUI REST API.
    Provides methods to submit prompt workflows, poll status, and get history.
    """
    def __init__(self, server_address: str):
        self.server_address = server_address.rstrip('/')

    async def queue_prompt(self, workflow_json: Dict[str, Any], client_id: str) -> Optional[str]:
        """Queues a prompt workflow to ComfyUI."""
        url = f"{self.server_address}/prompt"
        payload = {
            "prompt": workflow_json,
            "client_id": client_id
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        prompt_id = data.get("prompt_id")
                        log_action("ComfyClient", "QueuePrompt", "SUCCESS", 0.0, f"Queued ComfyUI prompt: {prompt_id}")
                        return prompt_id
                    else:
                        text = await response.text()
                        log_action("ComfyClient", "QueuePrompt", "FAILED", 0.0, f"ComfyUI HTTP {response.status}: {text}")
        except Exception as e:
            log_action("ComfyClient", "QueuePrompt", "FAILED", 0.0, f"Connection error: {str(e)}")
            
        return None

    async def get_history(self, prompt_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves history metadata for a finished prompt."""
        url = f"{self.server_address}/history/{prompt_id}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
        except Exception as e:
            log_action("ComfyClient", "GetHistory", "FAILED", 0.0, f"Error getting history: {str(e)}")
        return None
