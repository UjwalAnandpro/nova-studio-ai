import json
import urllib.request
import threading
from typing import List, Dict, Any
from core.api.event_bus import event_bus, Event
from core.config.manager import settings_manager
from core.logger.custom_logger import log_action

class WebhookDispatcher:
    """Manages outgoing webhooks and broadcasts EventBus messages to URL endpoints."""
    def __init__(self):
        self.lock = threading.Lock()
        self.targets: List[str] = []
        
        # Subscribe to wildcard event bus to forward everything
        event_bus.subscribe("*", self._on_event)

    def register_url(self, url: str):
        with self.lock:
            if url not in self.targets:
                self.targets.append(url)
                log_action("Webhook", "Register", "SUCCESS", 0.0, f"Registered webhook target: {url}")

    def list_urls(self) -> List[str]:
        with self.lock:
            return list(self.targets)

    def remove_url(self, url: str):
        with self.lock:
            if url in self.targets:
                self.targets.remove(url)
                log_action("Webhook", "Remove", "SUCCESS", 0.0, f"Removed webhook target: {url}")

    def _on_event(self, evt: Event):
        # Dispatch in background threads to avoid blocking EventBus execution
        with self.lock:
            urls = list(self.targets)
            
        for url in urls:
            t = threading.Thread(target=self._post_webhook, args=(url, evt.to_dict()), daemon=True)
            t.start()

    def _post_webhook(self, url: str, payload: Dict[str, Any]):
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            # Timeout set to 3 seconds to prevent background thread hangs
            with urllib.request.urlopen(req, timeout=3.0) as response:
                response.read()
            log_action("Webhook", "Post", "SUCCESS", 0.0, f"Dispatched webhook payload to {url}")
        except Exception as e:
            log_action("Webhook", "Post", "FAILED", 0.0, f"Failed pushing webhook to {url}: {str(e)}")

# Singleton dispatcher
webhook_dispatcher = WebhookDispatcher()
