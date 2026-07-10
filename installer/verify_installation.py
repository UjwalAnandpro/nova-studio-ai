import subprocess
import json
import sys
import os

def run_command(cmd: list) -> str:
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
        return output.strip().split("\n")[0]
    except Exception:
        return "Not Found"

def verify_all_installations() -> dict:
    report = {
        "Python": run_command([sys.executable, "--version"]),
        "Git": run_command(["git", "--version"]),
        "FFmpeg": run_command(["ffmpeg", "-version"]),
        "Streamlit": run_command(["streamlit", "version"]),
    }
    
    # Check pip list
    try:
        pip_list = subprocess.check_output([sys.executable, "-m", "pip", "list"], text=True)
        report["Pip List Length"] = len(pip_list.splitlines()) - 2
    except Exception:
        report["Pip List Length"] = "Failed"

    return report

def generate_report_logs(report: dict):
    print("=================== INSTALLATION REPORT ===================")
    for k, v in report.items():
        status = "🟢 Installed" if v != "Not Found" and v != "Failed" else "🔴 Missing"
        print(f"{k}: {v} | {status}")
    print("===========================================================")

if __name__ == "__main__":
    rep = verify_all_installations()
    generate_report_logs(rep)
