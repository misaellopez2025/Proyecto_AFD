; Instalador de Simulador AFD (Inno Setup 6).
; Se compila desde CONSTRUIR_INSTALADOR.ps1, que pasa /DDistDir con la salida de PyInstaller.

#define AppName "Simulador AFD"
#define AppVersion "1.0.0"
#define AppExe "SimuladorAFD.exe"
#ifndef DistDir
  #define DistDir "build\dist\SimuladorAFD"
#endif

[Setup]
AppId={{6E8B4C2A-3F1D-4C55-9A7E-AFD2026UMG01}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Universidad Mariano Gálvez - Autómatas y Lenguajes Formales
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
UninstallDisplayIcon={app}\{#AppExe}
SetupIconFile=docs\icono.ico
OutputDir=instalador
OutputBaseFilename=Instalador_Simulador_AFD
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "{#DistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "ejemplos\*.txt"; DestDir: "{app}\ejemplos"; Flags: ignoreversion
Source: "docs\Manual_de_usuario.pdf"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\Manual de usuario"; Filename: "{app}\Manual_de_usuario.pdf"
Name: "{group}\Archivos de ejemplo"; Filename: "{app}\ejemplos"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
