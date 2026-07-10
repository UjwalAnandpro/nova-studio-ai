# Nova Studio AI Professional Installer Build Environment

This directory contains the configurations and helper assets to compile **`NovaStudioAI_Setup.exe`**, a professional, one-click Windows installation wizard.

## 📖 Developer Prerequisites

To build the setup package, you must install:
1. **PyInstaller**:
   ```bash
   pip install pyinstaller psutil
   ```
2. **Inno Setup 6**:
   Download and install the official [Inno Setup 6 compiler package](https://jrsoftware.org/isdl.php).

---

## 📂 Source Code and Files

- **`launcher.py` / `.spec`**: Compiled startup target that automatically activates the local `.venv`, verifies backend REST servers and registers Streamlit on port `8501`.
- **`setup_helper.py` / `.spec`**: Gathers system RAM/GPU specifications, configures target directory folders, initializes default settings, and executes pip installations.
- **`uninstall_helper.py` / `.spec`**: Prompts the user to retain or purge local projects/models/caches.
- **`installer.iss`**: Inno Setup definition script defining wizard pages, components, and desktop shortcuts.
- **`build.bat`**: Build script automation.

---

## 🛠️ How to Compile the Installer

Run the automated compiler script:
```powershell
.\build.bat
```
Upon execution, PyInstaller will bundle the Python executables inside the `dist/` directory. If Inno Setup is detected on your machine, the script will automatically compile **`NovaStudioAI_Setup.exe`** ready for distribution!
