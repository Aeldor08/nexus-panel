; Installeur NEXUS (Inno Setup 6). Fabriqué par outils\build.py (ou outils\build_native.py --installer) :
;   ISCC.exe /DMyVersion=X.Y.Z [/DLhmDir=<dossier LibreHardwareMonitor>] installer.iss
; - Installation par utilisateur (sans droits administrateur) dans %LOCALAPPDATA%\Programs\NEXUS : la mise à jour
;   intégrée peut remplacer les fichiers. Données de l'utilisateur dans %LOCALAPPDATA%\NEXUS.
; - Le nom NEXUS-X.Y.Z-Setup.exe est celui que cherchent les versions installées pour se mettre à jour : ne pas le changer.
; - Désinstallation : demande s'il faut garder les données (oui par défaut ; toujours gardées en mode silencieux).

#ifndef MyVersion
  #define MyVersion "0.0.0"
#endif

#define MyAppName "NEXUS"
#define MyAppExeName "NEXUS.exe"
#define MyAppPublisher "NEXUS (Aeldor08)"
#define MyAppURL "https://github.com/Aeldor08/nexus-panel"
#define MyAppId "{{8F1E2B9A-7C4D-4F1A-9B2E-6D3C5A7E1B42}"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyVersion}
AppVerName={#MyAppName} {#MyVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
AppCopyright=NEXUS, licence MIT
DefaultDirName={localappdata}\Programs\NEXUS
DefaultGroupName=NEXUS
DisableProgramGroupPage=yes
DisableDirPage=no
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
OutputDir=dist
OutputBaseFilename=NEXUS-{#MyVersion}-Setup
SetupIconFile=panel.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName} {#MyVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
CloseApplicationsFilter=NEXUS.exe
RestartApplications=no
UsePreviousAppDir=yes
UsePreviousTasks=yes
SetupLogging=yes
LicenseFile=LICENSE
VersionInfoVersion={#MyVersion}.0
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=NEXUS — tableau de bord du PC (installeur)
VersionInfoCopyright=NEXUS, licence MIT

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "Créer un raccourci NEXUS sur le Bureau"; GroupDescription: "Raccourcis :"
#ifdef LhmDir
Name: "lhm"; Description: "Installer LibreHardwareMonitor (températures du processeur, des disques, ventilateurs) — Windows demandera l'autorisation administrateur au lancement de NEXUS"; GroupDescription: "Capteurs :"
#endif
Name: "autostart"; Description: "Lancer NEXUS au démarrage de Windows (dans la zone de notification)"; GroupDescription: "Démarrage :"; Flags: unchecked

[InstallDelete]
; Mise à jour propre : les anciens fichiers de _internal ne doivent pas rester.
; En cas d'échec, le helper natif remet la sauvegarde complète en place.
Type: filesandordirs; Name: "{app}\_internal"
Type: files; Name: "{app}\NEXUS.exe"

[Files]
Source: "dist\NEXUS\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
#ifdef LhmDir
; LibreHardwareMonitor (MPL-2.0) : jamais remplacé s'il est déjà là (il tourne en administrateur, ses fichiers
; seraient verrouillés pendant une mise à jour) ; NEXUS le démarre et le configure (serveur web local 8085).
Source: "{#LhmDir}\*"; DestDir: "{app}\LibreHardwareMonitor"; Flags: recursesubdirs createallsubdirs onlyifdoesntexist; Tasks: lhm
#endif

[Icons]
Name: "{group}\NEXUS"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\Configurer NEXUS"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--configure"; WorkingDir: "{app}"
Name: "{group}\Désinstaller NEXUS"; Filename: "{uninstallexe}"
Name: "{autodesktop}\NEXUS"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "NEXUS"; ValueData: """{app}\{#MyAppExeName}"" --minimized"; Flags: uninsdeletevalue; Tasks: autostart

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Lancer NEXUS"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; NEXUS ouvert (zone de notification) : on le ferme avant de supprimer ses fichiers.
Filename: "{sys}\taskkill.exe"; Parameters: "/IM NEXUS.exe /F"; Flags: runhidden; RunOnceId: "FermerNEXUS"

[UninstallDelete]
; Fichiers créés par NEXUS dans son dossier de programme (LibreHardwareMonitor compris s'il n'est plus lancé).
; Les données personnelles (%LOCALAPPDATA%\NEXUS) : voir CurUninstallStepChanged plus bas.
Type: filesandordirs; Name: "{app}\LibreHardwareMonitor"
Type: files; Name: "{app}\ancienne-version.txt"
Type: dirifempty; Name: "{app}"

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
           'NEXUS a besoin de WebView2 pour sa fenêtre native. Installe-le depuis :' + #13#10 +
           'https://developer.microsoft.com/microsoft-edge/webview2/' + #13#10#13#10 +
           'Windows 11 et la plupart des Windows 10 le possèdent déjà.',
           mbInformation, MB_OK);
  end;
end;

// Avant de copier les fichiers (et de remplacer le raccourci « NEXUS » du Bureau) : si ce raccourci mène à une
// ancienne version source de NEXUS (dossier avec nexus.pyw), son dossier est noté dans {app}\ancienne-version.txt.
// Au premier lancement, NEXUS y reprend les données (copie, l'ancien dossier n'est pas modifié : paths.py).
procedure CurStepChanged(CurStep: TSetupStep);
var
  Code: Integer;
  Script: String;
begin
  if CurStep <> ssInstall then
    exit;
  ForceDirectories(ExpandConstant('{app}'));
  Script := '$l=Join-Path ([Environment]::GetFolderPath(''Desktop'')) ''NEXUS.lnk''; ' +
            'if(Test-Path -LiteralPath $l){$w=(New-Object -ComObject WScript.Shell).CreateShortcut($l).WorkingDirectory; ' +
            'if($w -and (Test-Path -LiteralPath (Join-Path $w ''nexus.pyw''))){' +
            'Set-Content -LiteralPath ''' + ExpandConstant('{app}\ancienne-version.txt') + ''' -Value $w -Encoding UTF8}}';
  Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'), '-NoProfile -NonInteractive -Command "' + Script + '"',
       '', SW_HIDE, ewWaitUntilTerminated, Code);
end;

// Désinstallation : garder ou supprimer les données de l'utilisateur (garder par défaut).
// Mode silencieux (/SILENT, /VERYSILENT : mises à jour, scripts) : toujours gardées.
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Donnees: String;
  Code: Integer;
begin
  if CurUninstallStep <> usPostUninstall then
    exit;
  Donnees := ExpandConstant('{localappdata}\NEXUS');
  if UninstallSilent() or not DirExists(Donnees) then
    exit;
  if MsgBox('Supprimer aussi tes données NEXUS ?' + #13#10#13#10 +
            Donnees + #13#10 +
            '(configuration, statistiques, photos des souvenirs, journal, Philibert, profils ajoutés, ' +
            'sauvegardes de mise à jour)' + #13#10#13#10 +
            'Non (conseillé) : elles sont gardées et seront reprises si tu réinstalles NEXUS.' + #13#10 +
            'Oui : elles sont effacées définitivement.',
            mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
  begin
    DelTree(Donnees, True, True, True);
    // Jetons rangés dans le gestionnaire d'identifiants de Windows (bot Discord)
    Exec(ExpandConstant('{sys}\cmdkey.exe'), '/delete:jeton-bot@NEXUS-panel-discord', '', SW_HIDE, ewWaitUntilTerminated, Code);
    Exec(ExpandConstant('{sys}\cmdkey.exe'), '/delete:NEXUS-panel-discord', '', SW_HIDE, ewWaitUntilTerminated, Code);
  end;
end;
