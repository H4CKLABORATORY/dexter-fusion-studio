#define MyAppName "DEXTER FUSION STUDIO"
#define MyAppVersion "0.3.0"
#define MyAppExeName "DexterFusionStudio.exe"

[Setup]
AppId={{5A60FEC5-0649-4D41-AC1A-A0C0B1142E4C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=DEXTER FF
DefaultDirName={localappdata}\Programs\DexterFusionStudio
DefaultGroupName=DEXTER FUSION STUDIO
PrivilegesRequired=lowest
OutputDir=..\release
OutputBaseFilename=Dexter-Fusion-Studio-Setup-v{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
DisableProgramGroupPage=yes
ChangesAssociations=no

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; GroupDescription: "Accesos directos:"; Flags: unchecked

[Files]
Source: "..\dist\DexterFusionStudio\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\THIRD_PARTY_NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\DEXTER FUSION STUDIO"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\DEXTER FUSION STUDIO"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir DEXTER FUSION STUDIO"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Project files and personal media live outside {app} and are intentionally preserved.
