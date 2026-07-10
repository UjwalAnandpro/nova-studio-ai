import json
import threading
import socketserver
from http.server import BaseHTTPRequestHandler
from typing import Dict, Any
from core.projects.manager import project_manager
from core.api.event_bus import event_bus
from core.utils.system import get_disk_usage, get_gpu_status, check_ffmpeg
from core.config.manager import settings_manager
from core.logger.custom_logger import log_action

class RESTRequestHandler(BaseHTTPRequestHandler):
    """
    Lightweight built-in HTTP request router responding with JSON metrics
    to support local third-party API automation scripts.
    """

    def log_message(self, format, *args):
        # Silence default standard logger outputs to avoid terminal clutter
        pass

    def do_GET(self):
        # Routing endpoints
        if self.path == "/api/projects":
            self._send_json_response(200, self._get_projects_payload())
        elif self.path == "/api/system":
            self._send_json_response(200, self._get_system_payload())
        elif self.path == "/api/history":
            self._send_json_response(200, self._get_history_payload())
        elif self.path == "/api/settings":
            self._send_json_response(200, settings_manager.settings.model_dump())
        else:
            self._send_json_response(404, {"error": "Endpoint not found."})

    def _send_json_response(self, status_code: int, data: Any):
        try:
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))
        except Exception:
            pass

    def _get_projects_payload(self) -> List[Dict[str, Any]]:
        projects = project_manager.list_projects()
        return [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "status": p.status,
                "duration": p.duration,
                "size_mb": round(p.size_bytes / (1024 * 1024), 2)
            }
            for p in projects
        ]

    def _get_system_payload(self) -> Dict[str, Any]:
        gpu = get_gpu_status()
        disk = get_disk_usage(settings_manager.settings.storage_path)
        return {
            "gpu_name": gpu["name"],
            "gpu_available": gpu["available"],
            "vram_used": gpu.get("vram_used_mb", 0),
            "disk_free_gb": disk["free_gb"],
            "disk_used_pct": disk["percentage_used"],
            "ffmpeg_available": check_ffmpeg(settings_manager.settings.ffmpeg_path)
        }

    def _get_history_payload(self) -> List[Dict[str, Any]]:
        history = event_bus.get_history()
        return [e.to_dict() for e in history]

def List(type_hint):
    return type_hint

class RESTServer:
    """Launches the built-in HTTP server on a daemon thread."""
    def __init__(self, port: int = 9000):
        self.port = port
        self.server: Optional[socketserver.TCPServer] = None
        self.thread: Optional[threading.Thread] = None

    def start(self):
        # Prevent socket address reuse locks
        socketserver.TCPServer.allow_reuse_address = True
        
        class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
            pass
            
        try:
            self.server = ThreadedTCPServer(("127.0.0.1", self.port), RESTRequestHandler)
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True, name="RESTServerThread")
            self.thread.start()
            log_action("RESTServer", "Start", "SUCCESS", 0.0, f"Local REST API listening at http://127.0.0.1:{self.port}/api")
        except Exception as e:
            log_action("RESTServer", "Start", "FAILED", 0.0, f"Port {self.port} binding blocked: {str(e)}")

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()

# Singleton RESTServer
rest_server = RESTServer()
