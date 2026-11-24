# Gera o executável do legenDay no SEU Windows (sem GitHub).
# Antes: coloque libs\libmpv-2.dll (e, opcional, libs\ffmpeg.exe) e rode no PowerShell, na raiz do projeto:
#   powershell -ExecutionPolicy Bypass -File packaging\build_windows.ps1
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

if (-not (Test-Path "libs\libmpv-2.dll")) { throw "Coloque o libmpv-2.dll na pasta libs\ antes de gerar o executavel (veja libs\README.md)." }

python -m venv .venv-build
& .\.venv-build\Scripts\python.exe -m pip install --upgrade pip
& .\.venv-build\Scripts\python.exe -m pip install . pyinstaller
& .\.venv-build\Scripts\python.exe -m PyInstaller packaging\legenday.spec --noconfirm

$p = Start-Process "dist\legenDay\legenDay.exe" -ArgumentList "--selftest" -Wait -PassThru
Get-Content "dist\legenDay\selftest.txt"
if ($p.ExitCode -ne 0) { throw "O autoteste do executavel falhou (veja acima)." }

Remove-Item "dist\legenDay\selftest.txt" -ErrorAction SilentlyContinue
Copy-Item "packaging\LEIA-ME.txt" "dist\legenDay\LEIA-ME.txt"
# o antivirus costuma segurar o .exe recem-criado por alguns segundos: tenta de novo antes de desistir
foreach ($try in 1..6) {
    try { Compress-Archive -Path "dist\legenDay" -DestinationPath "dist\legenDay-windows-x64.zip" -Force; break }
    catch { if ($try -eq 6) { throw }; Start-Sleep -Seconds 5 }
}
Write-Host "Pronto: dist\legenDay-windows-x64.zip"

# instalador (legenDay-Setup.exe), se o Inno Setup 6 estiver instalado (winget install JRSoftware.InnoSetup)
$iscc = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe", "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe") |
    Where-Object { Test-Path $_ } | Select-Object -First 1
if ($iscc) {
    $version = & .\.venv-build\Scripts\python.exe -c "import legenday; print(legenday.__version__)"
    & $iscc /Q "/DAppVersion=$version" packaging\legenday.iss
    if ($LASTEXITCODE -ne 0) { throw "O Inno Setup nao conseguiu gerar o instalador." }
    Write-Host "Pronto: dist\legenDay-Setup.exe"
} else {
    Write-Host "Inno Setup nao encontrado: instalador nao gerado (so o .zip)."
}
