[Setup]
AppName=AITranslator
AppVersion=1.0.0
DefaultDirName={autopf}\AITranslator
DefaultGroupName=AITranslator
OutputDir=..\dist
OutputBaseFilename=AITranslator-Setup
PrivilegesRequired=lowest
Compression=lzma2
SolidCompression=yes
UninstallDisplayName=AITranslator

[Files]
Source: "..\dist\AITranslator\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\AITranslator"; Filename: "{app}\AITranslator.exe"
Name: "{autodesktop}\AITranslator"; Filename: "{app}\AITranslator.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Masaüstü kısayolu"; Flags: unchecked
Name: "autostart"; Description: "Windows ile birlikte başlat"

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "AITranslator"; ValueData: """{app}\AITranslator.exe"" --background"; Tasks: autostart; Flags: uninsdeletevalue

[Run]
Filename: "{app}\AITranslator.exe"; Description: "AITranslator'ı başlat"; Flags: nowait postinstall skipifsilent
