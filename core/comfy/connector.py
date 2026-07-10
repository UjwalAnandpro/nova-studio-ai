import requests
import time
import threading
from typing import Dict, Any, Optional, Tuple
from core.config.manager import settings_manager
from core.logger.custom_logger import log_action

class ComfyConnector:
    """
    Manages the network connection, auto-reconnect, status pinging and raw HTTP requests
    with the local or remote ComfyUI REST server.
    """
    def __init__(self):
        self.lock = threading.Lock()
        self._connected = False
        self._ping_thread: Optional[threading.Thread] = None
        self._stop_ping = threading.Event()
        
        # Load configs
        self.server_url = settings_manager.settings.comfyui_address.rstrip('/')
        self.timeout = 3.0  # seconds
        self.retry_count = 3
        self.reconnect_automatically = True
        
        # Start the background status checker
        self.start_ping_system()

    @property
    def is_connected(self) -> bool:
        with self.lock:
            return self._connected

    @is_connected.setter
    def is_connected(self, value: bool):
        with self.lock:
            self._connected = value

    def check_connection(self) -> bool:
        """Pings the ComfyUI server to check its connection status."""
        url = f"{self.server_url}/system_stats"
        try:
            r = requests.get(url, timeout=self.timeout)
            if r.status_code == 200:
                if not self.is_connected:
                    log_action("ComfyConnector", "CheckConnection", "SUCCESS", 0.0, "ComfyUI Connection established: 🟢 Connected")
                self.is_connected = True
                return True
        except Exception:
            pass
            
        if self.is_connected:
            log_action("ComfyConnector", "CheckConnection", "WARNING", 0.0, "ComfyUI connection lost: 🔴 Offline")
        self.is_connected = False
        return False

    def start_ping_system(self):
        """Starts the background ping monitor thread (runs every 10 seconds)."""
        self._stop_ping.clear()
        self._ping_thread = threading.Thread(target=self._ping_loop, daemon=True, name="ComfyUIPinger")
        self._ping_thread.start()

    def stop_ping_system(self):
        """Stops the background ping monitor."""
        self._stop_ping.set()
        if self._ping_thread:
            self._ping_thread.join(timeout=1.0)

    def _ping_loop(self):
        """Background thread loop to ping ComfyUI server."""
        while not self._stop_ping.is_set():
            self.check_connection()
            # Wait 10 seconds, checking stop event periodically
            for _ in range(10):
                if self._stop_ping.is_set():
                    break
                time.sleep(1.0)

    def post(self, endpoint: str, json_data: Optional[Dict[str, Any]] = None) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """Performs a POST request against the ComfyUI API with retries and timeout."""
        url = f"{self.server_url}{endpoint}"
        last_error = ""
        
        for attempt in range(self.retry_count):
            try:
                r = requests.post(url, json=json_data, timeout=self.timeout)
                if r.status_code == 200:
                    try:
                        return True, r.json(), ""
                    except Exception:
                        return True, None, ""
                else:
                    last_error = f"HTTP {r.status_code}: {r.text}"
            except Exception as e:
                last_error = str(e)
                
            time.sleep(0.5)
            
        log_action("ComfyConnector", "POST", "FAILED", 0.0, f"POST {endpoint} failed: {last_error}")
        return False, None, last_error

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, binary: bool = False) -> Tuple[bool, Any, str]:
        """Performs a GET request against the ComfyUI API with retries and timeout."""
        url = f"{self.server_url}{endpoint}"
        last_error = ""
        
        for attempt in range(self.retry_count):
            try:
                r = requests.get(url, params=params, timeout=self.timeout)
                if r.status_code == 200:
                    if binary:
                        return True, r.content, ""
                    try:
                        return True, r.json(), ""
                    except Exception:
                        return True, r.text, ""
                else:
                    last_error = f"HTTP {r.status_code}: {r.text}"
            except Exception as e:
                last_error = str(e)
                
            time.sleep(0.5)
            
        log_action("ComfyConnector", "GET", "FAILED", 0.0, f"GET {endpoint} failed: {last_error}")
        return False, None, last_error

# Singleton ComfyConnector instance
comfy_connector = ComfyConnector()
