import os
import sys
import json
import time
import traceback
import platform
from typing import Dict, Any

class CrashManager:
    """Catches unexpected failures and writes diagnostic logs to recover corrupt sessions."""
    def __init__(self):
        self.reports_dir = os.path.join("storage", "crash_reports")

    def generate_report(self, exc_type, exc_value, exc_traceback) -> str:
        """Writes detailed stack trace and hardware snapshot to json report."""
        os.makedirs(self.reports_dir, exist_ok=True)
        report_id = f"crash_{int(time.time())}"
        report_path = os.path.join(self.reports_dir, f"{report_id}.json")

        tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        
        # Build environment statistics
        report_data = {
            "report_id": report_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "os": platform.system(),
            "os_release": platform.release(),
            "python_version": sys.version,
            "error_type": exc_type.__name__ if exc_type else "Unknown",
            "error_message": str(exc_value),
            "stack_trace": tb_lines,
            "loaded_modules": list(sys.modules.keys())[:100], # Cap to prevent huge files
            "environment_vars": {k: v for k, v in os.environ.items() if "KEY" not in k and "SECRET" not in k} # Filter sensitive keys
        }

        try:
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report_data, f, indent=4)
        except Exception:
            pass

        return report_path

    def list_reports(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.reports_dir):
            return []
        reports = []
        for f in os.listdir(self.reports_dir):
            if f.endswith(".json"):
                path = os.path.join(self.reports_dir, f)
                try:
                    with open(path, "r", encoding="utf-8") as file:
                        reports.append(json.load(file))
                except Exception:
                    pass
        return sorted(reports, key=lambda x: x.get("timestamp", ""), reverse=True)

def List(type_hint):
    return type_hint

# Singleton CrashManager
crash_manager = CrashManager()
