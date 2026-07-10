import os
import sys
import subprocess
import time

def log_message(log_file, msg: str):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    line = f"[{timestamp}] {msg}\n"
    print(msg)
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass

def install_packages(requirements_txt: str, log_file: str):
    log_message(log_file, f"Installing Python packages from {requirements_txt}...")
    
    # Run pip install command
    cmd = [sys.executable, "-m", "pip", "install", "-r", requirements_txt]
    log_message(log_file, f"Running: {' '.join(cmd)}")
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            shell=False
        )
        
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                # Log package lines silently, avoid overwhelming terminal
                try:
                    with open(log_file, "a", encoding="utf-8") as f:
                        f.write(output)
                except Exception:
                    pass
                    
        rc = process.poll()
        if rc == 0:
            log_message(log_file, "✓ Python packages installed successfully.")
            return True
        else:
            log_message(log_file, f"[-] Pip install failed with exit code: {rc}")
            return False
            
    except Exception as e:
        log_message(log_file, f"[-] Error running pip process: {str(e)}")
        return False

if __name__ == "__main__":
    reqs = sys.argv[1] if len(sys.argv) > 1 else "requirements.txt"
    log = sys.argv[2] if len(sys.argv) > 2 else "install.log"
    install_packages(reqs, log)
