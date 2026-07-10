import os
import sys
import subprocess
import shutil
import platform
import psutil
import json

def log(msg: str):
    print(f"[LOG] {msg}")
    try:
        with open("install.log", "a", encoding="utf-8") as f:
            f.write(f"{msg}\n")
    except Exception:
        pass

def run_system_check():
    log("Starting system diagnostics check...")
    stats = {}
    stats["os"] = f"{platform.system()} {platform.release()}"
    stats["cpu"] = platform.processor()
    
    # RAM
    ram = psutil.virtual_memory()
    stats["ram_gb"] = round(ram.total / (1024**3), 2)
    
    # Disk Space
    disk = shutil.disk_usage("C:\\") if os.path.exists("C:\\") else shutil.disk_usage(".")
    stats["disk_free_gb"] = round(disk.free / (1024**3), 2)
    
    # GPU & CUDA check
    stats["gpu"] = "CPU Only"
    stats["cuda"] = False
    try:
        out = subprocess.check_output(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], text=True)
        stats["gpu"] = out.strip()
        stats["cuda"] = True
    except Exception:
        pass
        
    log(f"OS: {stats['os']}")
    log(f"RAM: {stats['ram_gb']} GB")
    log(f"Disk Free: {stats['disk_free_gb']} GB")
    log(f"GPU: {stats['gpu']}")
    
    return stats

def install_system_dependencies():
    log("Installing dependencies via winget...")
    dependencies = ["Git.Git", "FFmpeg.FFmpeg"]
    
    for dep in dependencies:
        try:
            log(f"Installing package: {dep}")
            subprocess.check_call(["winget", "install", "--id", dep, "--silent", "--accept-source-agreements", "--accept-package-agreements"])
            log(f"✓ Installed: {dep}")
        except Exception as e:
            log(f"[-] Winget failed on {dep}: {str(e)}")

def build_project_workspace(base_dir: str):
    log(f"Initializing project directories inside: {base_dir}")
    subfolders = [
        "config", "database", "projects", "cache", "models", "workflows",
        "plugins", "templates", "assets", "voices", "music", "images",
        "videos", "fonts", "logs", "exports", "output", "temp", "backups"
    ]
    
    for folder in subfolders:
        os.makedirs(os.path.join(base_dir, folder), exist_ok=True)
        
    # Write templates
    env_content = "COMFYUI_URL=http://127.0.0.1:8188\nLMSTUDIO_URL=http://127.0.0.1:1234\nPROJECT_PATH=projects\nOUTPUT_PATH=output\nCACHE_PATH=cache\nLOG_PATH=logs\n"
    with open(os.path.join(base_dir, ".env"), "w", encoding="utf-8") as f:
        f.write(env_content)
        
    settings_content = '{"theme": "Dark", "comfyui_address": "http://127.0.0.1:8188", "llm_provider": "Ollama", "tts_provider": "Kokoro", "image_provider": "ComfyUI", "video_provider": "ComfyUI", "music_provider": "MusicGen", "storage_path": "storage", "cache_path": "cache", "project_path": "projects", "temp_path": "storage/temp", "output_path": "storage/output", "ffmpeg_path": "ffmpeg", "gpu_settings": {"enable_gpu": true, "gpu_id": 0, "precision": "fp16", "low_vram": false}, "extra_configs": {}}'
    with open(os.path.join(base_dir, "config", "settings.json"), "w", encoding="utf-8") as f:
        f.write(settings_content)

def setup_python_venv(base_dir: str):
    log("Setting up virtual environment...")
    venv_dir = os.path.join(base_dir, ".venv")
    
    if not os.path.exists(venv_dir):
        subprocess.check_call([sys.executable, "-m", "venv", venv_dir])
        
    pip_exe = os.path.join(venv_dir, "Scripts", "pip.exe")
    python_exe = os.path.join(venv_dir, "Scripts", "python.exe")
    
    # Upgrade pip
    log("Upgrading Pip...")
    subprocess.check_call([python_exe, "-m", "pip", "install", "--upgrade", "pip"])
    
    # Install dependencies
    requirements_file = os.path.join(base_dir, "requirements.txt")
    if os.path.exists(requirements_file):
        log("Installing packages from requirements...")
        subprocess.check_call([pip_exe, "install", "-r", requirements_file])
        log("✓ Requirements installed successfully.")

if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "check"
    target = sys.argv[2] if len(sys.argv) > 2 else "C:\\NovaStudioAI"
    
    if action == "check":
        run_system_check()
    elif action == "install_deps":
        install_system_dependencies()
    elif action == "setup_project":
        build_project_workspace(target)
        setup_python_venv(target)
