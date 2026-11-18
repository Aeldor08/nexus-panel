; Installeur NEXUS (Inno Setup 6).
; Construire l'exe avec outils/build_native.py, puis :
;   ISCC.exe /DMyVersion=1.6.0 installer.iss
; L'installeur est par utilisateur (pas besoin d'administrateur), installe les
; fichiers dans %LOCALAPPDATA%\Programs\NEXUS et laisse les donnÃ©es dans
; %LOCALAPPDATA%\NEXUS (jamais supprimÃ©es par la dÃ©sinstallation).

#ifndef MyVersion
  #define MyVersion "1.6.0"
#endif

#define MyAppName "NEXUS"
#define MyAppExeName "NEXUS.exe"
#define MyAppPublisher "NEXUS"
#define MyAppId "{{8F1E2B9A-7C4D-4F1A-9B2E-6D3C5A7E1B42}"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyVersion}
AppVerName={#MyAppName} {#MyVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL=https://github.com/Aeldor08/nexus-panel
AppSupportURL=https://github.com/Aeldor08/nexus-panel
AppUpdatesURL=https://github.com/Aeldor08/nexus-panel
DefaultDirName={localappdata}\Programs\NEXUS
DefaultGroupName=NEXUS
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
OutputDir=dist
OutputBaseFilename=NEXUS-{#MyVersion}-Setup
SetupIconFile=panel.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
UsePreviousAppDir=yes
UsePreviousTasks=yes
SetupLogging=yes
LicenseFile=LICENSE
VersionInfoVersion={#MyVersion}.0
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=NEXUS â€” tableau de bord du PC

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "CrÃ©er un raccourci NEXUS sur le Bureau"; GroupDescription: "Raccourcis :"
Name: "autostart"; Description: "Lancer NEXUS au dÃ©marrage de Windows (dans la zone de notification)"; GroupDescription: "DÃ©marrage :"; Flags: unchecked

[InstallDelete]
; Mise Ã  jour propre : les anciens fichiers de _internal ne doivent pas rester.
; En cas d'Ã©chec, le helper natif remet la sauvegarde complÃ¨te en place.
Type: filesandordirs; Name: "{app}\_internal"
Type: files; Name: "{app}\NEXUS.exe"

[Files]
Source: "dist\NEXUS\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\NEXUS"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\Configurer NEXUS"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--configure"; WorkingDir: "{app}"
Name: "{group}\DÃ©sinstaller NEXUS"; Filename: "{uninstallexe}"
Name: "{autodesktop}\NEXUS"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "NEXUS"; ValueData: """{app}\{#MyAppExeName}"" --minimized"; Flags: uninsdeletevalue; Tasks: autostart

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Lancer NEXUS"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Les donnÃ©es personnelles sont dans {localappdata}\NEXUS et ne sont jamais supprimÃ©es ici.

[Code]
const
  WebView2Key = 'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';
  WebView2Key64 = 'SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';
  WebView2KeyUser = 'Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';

function WebView2Installed(): Boolean;
var
  Value: String;
begin
  Result :=
    RegQueryStringValue(HKLM, WebView2Key, 'pv', Value) or
    RegQueryStringValue(HKLM, WebView2Key64, 'pv', Value) or
    RegQueryStringValue(HKCU, WebView2KeyUser, 'pv', Value);
end;

procedure InitializeWizard();
begin
  if not WebView2Installed() then
  begin
    MsgBox('Microsoft Edge WebView2 Runtime est introuvable.' + #13#10#13#10 +
           'NEXUS a besoin de WebView2 pour sa fenÃªtre native. Installe-le depuis :' + #13#10 +
           'https://developer.microsoft.com/microsoft-edge/webview2/' + #13#10#13#10 +
           'Windows 11 et la plupart des Windows 10 le possÃ¨dent dÃ©jÃ .',
           mbInformation, MB_OK);
  end;
end;

