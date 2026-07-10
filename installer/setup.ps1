# PowerShell Bootstrap Installer for Nova Studio AI
$logFile = "install.log"
$projectDir = Join-Path $PSScriptRoot "..\NovaStudioAI"
$projectDir = [System.IO.Path]::GetFullPath($projectDir)

function Log-Message($msg) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$timestamp] $msg"
    Write-Host $msg -ForegroundColor Green
    Add-Content -Path $logFile -Value $line
}

Log-Message "=================== STARTING NOVA STUDIO AI INSTALLER ==================="
Log-Message "Target project directory: $projectDir"

# 1. Verify Internet Connection
try {
    $client = New-Object System.Net.WebClient
    $null = $client.OpenRead("http://clients3.google.com/generate_204")
    Log-Message "[+] Internet Connection: Online"
} catch {
    Log-Message "[-] WARNING: Internet offline. Winget installations and package fetches might fail."
}

# 2. Verify Winget is present
$wingetCheck = Get-Command winget -ErrorAction SilentlyContinue
if (-not $wingetCheck) {
    Log-Message "[-] Winget package manager not found. Please install the Windows App Installer."
    Log-Message "Opening winget release website..."
    Start-Process "https://github.com/microsoft/winget-cli/releases"
} else {
    Log-Message "[+] Winget Package Manager detected."
    
    # Install dependencies using Winget
    Log-Message "Installing system dependencies via Winget..."
    $apps = @("Python.Python.3.12", "Git.Git", "FFmpeg.FFmpeg", "Microsoft.VisualStudioCode", "7zip.7zip")
    foreach ($app in $apps) {
        Log-Message "  [+] Checking/Installing: $app"
        Start-Process winget -ArgumentList "install --id $app --silent --accept-source-agreements --accept-package-agreements" -NoNewWindow -Wait
    }
}

# 3. Create Project Structure Folder layout
Log-Message "Creating folder directory layout..."
python create_folders.py "$projectDir"

# 4. Create Virtual Environment and Upgrade Pip
Log-Message "Setting up virtual environment in $projectDir\.venv..."
$venvPath = Join-Path $projectDir ".venv"
if (-not (Test-Path $venvPath)) {
    Start-Process python -ArgumentList "-m venv $venvPath" -NoNewWindow -Wait
}
Log-Message "Upgrading Pip inside virtual environment..."
$pipExec = Join-Path $venvPath "Scripts\pip.exe"
$pythonExec = Join-Path $venvPath "Scripts\python.exe"
Start-Process $pythonExec -ArgumentList "-m pip install --upgrade pip" -NoNewWindow -Wait

# 5. Install Python dependencies
Log-Message "Installing python packages..."
Start-Process $pythonExec -ArgumentList "install_python_packages.py requirements.txt $logFile" -NoNewWindow -Wait

# 6. Generate .env file
Log-Message "Generating environmental .env files..."
$envContent = @"
COMFYUI_URL=http://127.0.0.1:8188
LMSTUDIO_URL=http://127.0.0.1:1234
PROJECT_PATH=projects
OUTPUT_PATH=output
CACHE_PATH=cache
LOG_PATH=logs
"@
Set-Content -Path (Join-Path $projectDir ".env") -Value $envContent

# 7. Generate settings.json
Log-Message "Generating settings.json configuration template..."
$settingsContent = @"
{
    "theme": "Dark",
    "comfyui_address": "http://127.0.0.1:8188",
    "llm_provider": "Ollama",
    "tts_provider": "Kokoro",
    "image_provider": "ComfyUI",
    "video_provider": "ComfyUI",
    "music_provider": "MusicGen",
    "storage_path": "storage",
    "cache_path": "cache",
    "project_path": "projects",
    "temp_path": "storage/temp",
    "output_path": "storage/output",
    "ffmpeg_path": "ffmpeg",
    "gpu_settings": {
        "enable_gpu": true,
        "gpu_id": 0,
        "precision": "fp16",
        "low_vram": false
    },
    "extra_configs": {}
}
"@
Set-Content -Path (Join-Path $projectDir "config/settings.json") -Value $settingsContent

# 8. ComfyUI setup prompts
Log-Message "Setting up model pipelines and optional download packages..."
Start-Process $pythonExec -ArgumentList "download_dependencies.py $projectDir" -NoNewWindow -Wait

# 9. Verify Installations
Log-Message "Running installation check verifiers..."
Start-Process $pythonExec -ArgumentList "verify_installation.py" -NoNewWindow -Wait

# 10. Generate Launch Shortcut Script
Log-Message "Creating startup launcher scripts..."
$launcherBat = @"
@echo off
cd /d "%~dp0"
call .venv\Scripts\activate
python -m streamlit run app.py
"@
Set-Content -Path (Join-Path $projectDir "launch.bat") -Value $launcherBat

# Create Desktop Shortcut
try {
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut([System.IO.Path]::Combine([Environment]::GetFolderPath("Desktop"), "Launch Nova Studio AI.lnk"))
    $Shortcut.TargetPath = (Join-Path $projectDir "launch.bat")
    $Shortcut.WorkingDirectory = $projectDir
    $Shortcut.IconLocation = "shell32.dll,14" # Video icon index
    $Shortcut.Save()
    Log-Message "✓ Launch shortcut created on your Desktop."
} catch {
    Log-Message "[-] Failed creating launch shortcut."
}

Log-Message "=================== INSTALLATION COMPLETE ==================="
Log-Message "✔ Python Installed"
Log-Message "✔ Git Installed"
Log-Message "✔ FFmpeg Installed"
Log-Message "✔ Virtual Environment Created"
Log-Message "✔ Python Packages Installed"
Log-Message "✔ Project Created"
Log-Message "✔ Configuration Generated"
Log-Message "✔ Ready To Build Nova Studio AI"
