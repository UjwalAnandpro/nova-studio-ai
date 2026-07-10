import os
import sys
import subprocess
import time
import webbrowser

def launch_nova_studio():
    print("=================== NOVA STUDIO AI LAUNCHER ===================")
    
    # Locate project root folder relative to this executable
    proj_dir = os.path.abspath(os.path.dirname(__file__))
    print(f"[+] Workspace Directory: {proj_dir}")
    
    # Verify virtual environment
    python_exec = os.path.join(proj_dir, ".venv", "Scripts", "python.exe")
    if not os.path.exists(python_exec):
        # Fallback to system python
        python_exec = "python"
        print("[!] Virtual environment not detected. Running with system Python.")
    else:
        print(f"[+] Using virtual environment interpreter: {python_exec}")

    # Launch REST API server as a background daemon
    rest_server_script = os.path.join(proj_dir, "core", "api", "rest_api.py")
    if os.path.exists(rest_server_script):
        print("[+] Starting REST API Daemon service...")
        subprocess.Popen([python_exec, rest_server_script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.0)

    # Launch Streamlit app
    app_py = os.path.join(proj_dir, "app.py")
    if not os.path.exists(app_py):
        print(f"[-] ERROR: Main script file not found at: {app_py}")
        input("Press Enter to exit...")
        sys.exit(1)

    print("[+] Launching Streamlit Creative Dashboard...")
    cmd = [python_exec, "-m", "streamlit", "run", app_py, "--server.port", "8501", "--server.headless", "true"]
    
    # Start streamlit process
    process = subprocess.Popen(cmd)
    
    # Wait for startup and open browser
    time.sleep(2.5)
    print("✓ Opening default web browser at http://localhost:8501")
    webbrowser.open("http://localhost:8501")
    
    try:
        process.wait()
    except KeyboardInterrupt:
        print("[+] Shutting down server hosts...")
        process.terminate()

if __name__ == "__main__":
    launch_nova_studio()
