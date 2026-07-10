@echo off
:: Nova Studio AI Bootstrap Installer Entrypoint
:: Verifies Administrator privileges and boots setup.ps1

title Nova Studio AI Bootstrap Installer

:: Check for Administrator Privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [!] ERROR: This installer requires Administrator privileges.
    echo Please right-click setup.bat and select "Run as administrator".
    echo.
    pause
    exit /b 1
)

echo [+] Administrator privileges verified.
echo [+] Checking for PowerShell execution policy...

:: Run PowerShell installer
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"

pause
