# Nova Studio AI - One-Click Bootstrap Installer

This folder contains a professional, automated one-click bootstrap installer to prepare a complete local AI development environment on Windows 10 or Windows 11.

## 📖 Table of Contents
1. [Overview](#overview)
2. [Included Installer Files](#included-installer-files)
3. [How to Use the Installer](#how-to-use-the-installer)
4. [Troubleshooting FAQs](#troubleshooting-faqs)

---

## Overview

The bootstrap installer checks for required dependencies, configures runtime paths, clones ComfyUI, initializes configuration settings files, and installs all core Python package requirements inside a localized virtual environment (`.venv`).

---

## Included Installer Files

| Filename | Purpose |
| -------- | ------- |
| `setup.bat` | The main execution entry point (checks for Admin rights). |
| `setup.ps1` | The orchestrator script checking Winget, Git, Python, and paths. |
| `create_folders.py` | Automatically sets up standard directories structures. |
| `environment_check.py` | Gathers GPU parameters, RAM size, disk stats, and recommendations. |
| `download_dependencies.py` | Clones ComfyUI and prompts for optional HuggingFace models. |
| `install_python_packages.py` | Installs libraries inside the `.venv` sandbox. |
| `verify_installation.py` | Verifies version details for python, git, and ffmpeg. |

---

## How to Use the Installer

1. Open this folder in your File Explorer.
2. Right-click **`setup.bat`** and select **"Run as administrator"**.
3. Accept the user account control (UAC) prompt if it appears.
4. Follow the interactive prompts in the terminal console (e.g. choose whether to clone ComfyUI and open model download pages).
5. Once completed, double-click the **"Launch Nova Studio AI"** shortcut on your Desktop to boot the Streamlit dashboard workspace!

---

## Troubleshooting FAQs

### 1. PowerShell Script Execution is Disabled Check
If Windows blocks PowerShell scripts, open PowerShell as administrator and execute:
```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
```

### 2. Winget package manager not found
If winget is missing (often on older Windows 10 versions), the installer will open the Microsoft winget CLI release pages. Please download and install the App Installer package, then rerun `setup.bat`.
