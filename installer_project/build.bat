@echo off
:: Build Automation Script for Nova Studio AI Professional Installer

echo ========================================================
echo       BUILDING NOVA STUDIO AI WINDOWS INSTALLER
echo ========================================================
echo.

:: Verify PyInstaller is installed
where pyinstaller >nul 2>&1
if %errorLevel% neq 0 (
    echo [-] ERROR: PyInstaller was not detected in your active environment path.
    echo Please install it using: pip install pyinstaller
    echo.
    pause
    exit /b 1
)

:: Compile Python executables using PyInstaller specifications
echo [+] Compiling Launcher.exe...
pyinstaller --clean --noconfirm launcher.spec

echo [+] Compiling setup_helper.exe...
pyinstaller --clean --noconfirm setup_helper.spec

echo [+] Compiling uninstall_helper.exe...
pyinstaller --clean --noconfirm uninstall_helper.spec

:: Locate Inno Setup compiler (ISCC)
set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist %ISCC% (
    set ISCC="C:\Program Files\Inno Setup 6\ISCC.exe"
)

:: Check if ISCC was found
if not exist %ISCC% (
    echo [!] WARNING: Inno Setup compiler (ISCC.exe) was not found in default paths.
    echo Exiting compilation phase. You can compile installer.iss manually inside Inno Setup UI.
    echo.
    pause
    exit /b 0
)

echo [+] Compiling Inno Setup installer package...
%ISCC% installer.iss

echo.
echo ✓ Build process completed! Installer binary generated at: installer_project\NovaStudioAI_Setup.exe
echo ========================================================
pause
