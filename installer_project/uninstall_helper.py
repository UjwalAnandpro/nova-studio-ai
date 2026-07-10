import os
import sys
import shutil

def log(msg: str):
    print(f"[UNINSTALL] {msg}")

def run_uninstall(target_dir: str, keep_projects: bool, keep_models: bool, keep_cache: bool):
    log(f"Starting uninstallation cleanup at: {target_dir}")
    
    if not os.path.exists(target_dir):
        log("Target directory does not exist. Nothing to uninstall.")
        return

    # Subfolders to optionally preserve
    optional_preserves = {
        "projects": keep_projects,
        "models": keep_models,
        "cache": keep_cache
    }

    for item in os.listdir(target_dir):
        item_path = os.path.join(target_dir, item)
        
        # Check if we should preserve it
        if item in optional_preserves:
            if optional_preserves[item]:
                log(f"Preserved: {item}/")
                continue

        try:
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
                log(f"Removed directory: {item}/")
            else:
                os.remove(item_path)
                log(f"Removed file: {item}")
        except Exception as e:
            log(f"[-] Failed removing {item}: {str(e)}")

    # Try removing base dir if empty
    try:
        os.rmdir(target_dir)
        log("Removed root directory C:\\NovaStudioAI")
    except Exception:
        log("Preserved root directory folder due to retained elements.")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "C:\\NovaStudioAI"
    
    # Check flags
    keep_proj = "--keep-projects" in sys.argv
    keep_mods = "--keep-models" in sys.argv
    keep_cch = "--keep-cache" in sys.argv
    
    run_uninstall(target, keep_proj, keep_mods, keep_cch)
