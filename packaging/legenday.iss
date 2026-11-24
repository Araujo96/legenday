; Instalador do legenDay (Inno Setup 6): gera dist\legenDay-Setup.exe a partir da pasta dist\legenDay.
;   iscc /DAppVersion=0.6.1 packaging\legenday.iss
; Instala só para o usuário (sem pedir administrador), cria os atalhos e abre o app no fim.
; Rodar uma versão nova por cima atualiza; as palavras salvas (~\.legenday) nunca são apagadas.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
; o AppId identifica o programa no Windows: nunca mude, senão a atualização vira uma segunda instalação
AppId={{8C1E3B6A-4F2D-4E7B-9A51-6D0C2B7F3E11}
AppName=legenDay
AppVersion={#AppVersion}
AppVerName=legenDay {#AppVersion}
AppPublisher=Lucas Araujo
AppPublisherURL=https://github.com/Araujo96/legenday
AppSupportURL=https://github.com/Araujo96/legenday/issues
AppUpdatesURL=https://github.com/Araujo96/legenday/releases/latest
VersionInfoVersion={#AppVersion}
DefaultDirName={autopf}\legenDay
DisableProgramGroupPage=yes
DisableDirPage=yes
DisableReadyPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist
OutputBaseFilename=legenDay-Setup
SetupIconFile=..\src\legenday\assets\icon.ico
UninstallDisplayIcon={app}\legenDay.exe
UninstallDisplayName=legenDay
WizardStyle=modern
Compression=lzma2/ultra64
SolidCompression=yes
; fecha o legenDay aberto antes de atualizar os arquivos
CloseApplications=force

[Languages]
Name: "ptbr"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[InstallDelete]
; ao atualizar, tira os arquivos internos da versão anterior (evita sobrar biblioteca velha misturada)
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "..\dist\legenDay\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\legenDay"; Filename: "{app}\legenDay.exe"
Name: "{autodesktop}\legenDay"; Filename: "{app}\legenDay.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\legenDay.exe"; Description: "{cm:LaunchProgram,legenDay}"; Flags: nowait postinstall skipifsilent
