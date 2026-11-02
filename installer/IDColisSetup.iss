; Inno Setup Script for ID Colis Support App
; This script creates a professional Windows installer with wizard UI

#define MyAppName "ID Colis Support App"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "ID Colis"
#define MyAppURL "https://example.com"

[Setup]
; Basic setup information
AppId={{8A3F4E2C-7B9D-4E5F-9C2A-1B5D3E7F8A9C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; Installation directories
DefaultDirName={localappdata}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=dist\installer
OutputBaseFilename=IDColisSetup

; Installer appearance and behavior
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest
WizardStyle=modern
ShowLanguageDialog=no
UninstallDisplayIcon={app}\launch.bat
LicenseFile=LICENSE.txt
InfoBeforeFile=BEFORE_INSTALL.txt
InfoAfterFile=AFTER_INSTALL.txt

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Source code files
Source: "..\app.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\setup.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\backend\*"; DestDir: "{app}\backend"; Flags: ignoreversion recursesubdirs
Source: "..\frontend\*"; DestDir: "{app}\frontend"; Flags: ignoreversion recursesubdirs
; Launcher script
Source: "launch.bat"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Start menu shortcut
Name: "{group}\{#MyAppName}"; Filename: "{app}\launch.bat"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
; Desktop shortcut
Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\launch.bat"; Tasks: desktopicon

[Run]
; Launch the application after installation
Filename: "{app}\launch.bat"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    MsgBox('ID Colis Support App has been installed successfully!' + #13#10 +
           'To run the application, use the Start Menu shortcut or launch.bat.' + #13#10 +
           'Make sure Python 3.12+ is installed on your system.', mbInformation, MB_OK);
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    MsgBox('ID Colis Support App has been uninstalled.', mbInformation, MB_OK);
  end;
end;


