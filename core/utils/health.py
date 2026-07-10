import sys
import os
import platform
import subprocess
from typing import Dict, Any
from core.config.manager import settings_manager
from core.utils.system import check_ffmpeg, get_gpu_status, get_disk_usage
from core.comfy import comfy_connector

class HealthEngine:
    """Consolidated system diagnostic prober validating startup parameters."""
    
    def run_health_checks(self) -> Dict[str, Any]:
        gpu = get_gpu_status()
        disk = get_disk_usage(settings_manager.settings.storage_path)
        
        # Verify writing permissions
        storage_writeable = False
        try:
            probe_path = os.path.join(settings_manager.settings.storage_path, "health_probe.tmp")
            os.makedirs(os.path.dirname(probe_path), exist_ok=True)
            with open(probe_path, "w") as f:
                f.write("probe")
            os.remove(probe_path)
            storage_writeable = True
        except Exception:
            pass

        return {
            "operating_system": platform.system(),
            "os_release": platform.release(),
            "python_version": sys.version.split()[0],
            "gpu_name": gpu["name"],
            "gpu_available": gpu["available"],
            "vram_total_mb": gpu.get("vram_total_mb", 0),
            "disk_free_gb": disk["free_gb"],
            "disk_used_pct": disk["percentage_used"],
            "ffmpeg_available": check_ffmpeg(settings_manager.settings.ffmpeg_path),
            "comfyui_connected": comfy_connector.is_connected,
            "storage_writeable": storage_writeable
        }

# Singleton instance
health_engine = HealthEngine()
