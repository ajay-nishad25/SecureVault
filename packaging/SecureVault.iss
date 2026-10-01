; SecureVault — Inno Setup Installer Script
; Milestone M13 — Production Windows Packaging
;
; CRITICAL SECURITY & DATA RETENTION REQUIREMENT:
; This installer installs application binaries into {autopf}\SecureVault.
; User data strictly resides in %LOCALAPPDATA%\SecureVault.
; Under NO circumstances should uninstallation delete, modify, or purge
; %LOCALAPPDATA%\SecureVault or any .svault / init_state.json files.

#define MyAppName "SecureVault"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "SecureVault Team"
#define MyAppURL "https://github.com/ajay-nishad25/SecureVault"
#define MyAppExeName "SecureVault.exe"

[Setup]
; Unique application GUID for Windows installation tracking
AppId={{9F8E24D7-610B-4E38-B7AE-1520F3E5E3D8}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
; Application icon for installer and uninstaller
SetupIconFile=..\assets\SecureVault.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog commandline
OutputDir=..\dist_installer
OutputBaseFilename=SecureVault-Setup-{#MyAppVersion}
DisableProgramGroupPage=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Standalone compiled distribution from PyInstaller
Source: "..\dist\SecureVault\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\_internal\assets\SecureVault.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\_internal\assets\SecureVault.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

; NOTE:
; No [UninstallDelete] section is declared for %LOCALAPPDATA%\SecureVault.
; Inno Setup only removes files installed in {app}.
; All user vaults, credentials, and settings survive uninstallation completely intact.
