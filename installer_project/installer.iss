; Inno Setup Script for Nova Studio AI Professional Installer

[Setup]
AppName=Nova Studio AI
AppVersion=1.0.0
AppPublisher=Nova Studio AI Team
DefaultDirName=C:\NovaStudioAI
DefaultGroupName=Nova Studio AI
OutputDir=.
OutputBaseFilename=NovaStudioAI_Setup
Compression=lzma2/max
SolidCompression=yes
SetupIconFile=app_icons.ico
WizardStyle=modern
PrivilegesRequired=admin

[Tasks]
Name="desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Pack the compiled launchers and configuration helpers
Source: "dist\Launcher.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\setup_helper.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\uninstall_helper.exe"; DestDir: "{app}"; Flags: ignoreversion
; Pack application source code files
Source: "..\app.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\core\*"; DestDir: "{app}\core"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\plugins\*"; DestDir: "{app}\plugins"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\workflows\*"; DestDir: "{app}\workflows"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Nova Studio AI"; Filename: "{app}\Launcher.exe"
Name: "{userdesktop}\Nova Studio AI"; Filename: "{app}\Launcher.exe"; Tasks: desktopicon

[Run]
; Run setup helper to construct venv, check system specs and download libraries post copy
Filename: "{app}\setup_helper.exe"; Parameters: "setup_project ""{app}"""; StatusMsg: "Configuring local workspace directory and installing Python packages (this may take a few minutes)..."; Flags: runhidden

[UninstallRun]
; Run uninstall helper to prompt projects preservation
Filename: "{app}\uninstall_helper.exe"; Parameters: """{app}"" --keep-projects --keep-models"; StatusMsg: "Cleaning local folders and cache registries..."; Flags: runhidden
