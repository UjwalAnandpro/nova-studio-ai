import logging
import os
import time
from typing import Optional

# Setup the log directory and file path
LOG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "logs"))
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE_PATH = os.path.join(LOG_DIR, "nova_studio.log")

class NovaStudioFormatter(logging.Formatter):
    """
    Custom formatter that formats logs in a structured way:
    Timestamp | Module | Action | Status | Duration | Message
    """
    def format(self, record):
        # We look for custom attributes on the record
        module = getattr(record, "module_name", record.name)
        action = getattr(record, "action", "GENERAL")
        status = getattr(record, "status", "INFO")
        duration = getattr(record, "duration", 0.0)
        
        duration_str = f"{duration:.3f}s" if isinstance(duration, (int, float)) else str(duration)
        timestamp = self.formatTime(record, self.datefmt)
        
        return f"{timestamp} | {module} | {action} | {status} | {duration_str} | {record.getMessage()}"

def setup_logger() -> logging.Logger:
    logger = logging.getLogger("nova_studio")
    logger.setLevel(logging.DEBUG)
    
    # Avoid duplicate handlers if setup is called multiple times
    if not logger.handlers:
        # File Handler
        fh = logging.FileHandler(LOG_FILE_PATH, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        
        # Console Handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # Formatter
        formatter = NovaStudioFormatter(datefmt="%Y-%m-%d %H:%M:%S")
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        logger.addHandler(fh)
        logger.addHandler(ch)
        
    return logger

logger = setup_logger()

def log_action(module: str, action: str, status: str, duration: float = 0.0, message: str = ""):
    """
    Utility function to log an action with timing and status.
    """
    extra = {
        "module_name": module,
        "action": action,
        "status": status,
        "duration": duration
    }
    
    level = logging.INFO
    if status.upper() in ("ERROR", "FAILED", "CRITICAL"):
        level = logging.ERROR
    elif status.upper() in ("WARNING", "WARN"):
        level = logging.WARNING
    elif status.upper() in ("DEBUG",):
        level = logging.DEBUG
        
    logger.log(level, message, extra=extra)

def get_log_file_path() -> str:
    return LOG_FILE_PATH
