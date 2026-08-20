#define MyAppName "QuiltForge"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "ITSZ Studios"
#define MyAppURL "https://its-ze.github.io/quiltforge/"
#define MyAppExeName "QuiltForge.exe"

[Setup]
AppId={{A1909C59-3319-44D7-9DDA-9E87E4A60302}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE.txt
OutputDir=..\dist
OutputBaseFilename=QuiltForge-Setup-{#MyAppVersion}
SetupIconFile=..\src\quiltforge\resources\quiltforge.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no
VersionInfoVersion={#MyAppVersion}.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=QuiltForge Windows Installer
VersionInfoCopyright=Copyright (c) 2026 Zach Skeens

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\QuiltForge\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\QuiltForge"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\QuiltForge"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Classes\.qforge"; ValueType: string; ValueName: ""; ValueData: "QuiltForge.Project"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\QuiltForge.Project"; ValueType: string; ValueName: ""; ValueData: "QuiltForge Project"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\QuiltForge.Project\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"
Root: HKCU; Subkey: "Software\Classes\QuiltForge.Project\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch QuiltForge"; Flags: nowait postinstall skipifsilent
