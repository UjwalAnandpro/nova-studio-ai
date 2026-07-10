import os
import sys

def create_project_structure(base_dir: str):
    """Creates the absolute directory trees required for Nova Studio AI."""
    subfolders = [
        "config",
        "projects",
        "models",
        "workflows",
        "plugins",
        "assets",
        "cache",
        "logs",
        "output",
        "exports",
        "temp",
        "database",
        "voices",
        "music",
        "images",
        "videos",
        "fonts",
        "templates",
        "backups"
    ]

    print(f"Creating project base folder layout at: {base_dir}")
    os.makedirs(base_dir, exist_ok=True)

    for folder in subfolders:
        folder_path = os.path.join(base_dir, folder)
        os.makedirs(folder_path, exist_ok=True)
        print(f"  [+] Created: {folder}/{'' if os.path.exists(folder_path) else ' (FAILED)'}")

    # Write a default app.py check stub if missing
    app_stub = os.path.join(base_dir, "app.py")
    if not os.path.exists(app_stub):
        try:
            with open(app_stub, "w", encoding="utf-8") as f:
                f.write("# Nova Studio AI Startup Stub\nimport streamlit as st\nst.title('Nova Studio AI Bootstrapper')\n")
            print("  [+] Created entry app.py stub file.")
        except Exception as e:
            print(f"  [-] Failed creating app.py stub: {str(e)}")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "NovaStudioAI"))
    create_project_structure(target)
