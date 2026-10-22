# Genera instalador\Instalador_Simulador_AFD.exe
# Requisitos: Python 3.10+ e Inno Setup 6 (winget install JRSoftware.InnoSetup).
# Uso: powershell -ExecutionPolicy Bypass -File CONSTRUIR_INSTALADOR.ps1
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

# El entorno y los archivos intermedios van fuera de OneDrive para no sincronizarlos.
$buildRoot = Join-Path $env:LOCALAPPDATA 'AFD-build'
$venv = Join-Path $buildRoot 'venv'
$python = Join-Path $venv 'Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    python -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear el entorno virtual de compilación.' }
}
& $python -m pip install -q -r requirements.txt pyinstaller==6.22.3
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron instalar las dependencias.' }

Write-Output '1/3 Generando manual de usuario (PDF)...'
& $python -B generar_manual.py
if ($LASTEXITCODE -ne 0) { throw 'No se pudo generar el manual.' }

Write-Output '2/3 Empaquetando la aplicación con PyInstaller...'
$here = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$dist = Join-Path $buildRoot 'dist'
& $python -m PyInstaller --noconfirm --clean --windowed --name SimuladorAFD `
    --icon (Join-Path $here 'docs\icono.ico') `
    --add-data ((Join-Path $here 'tools\graphviz') + ';tools\graphviz') `
    --add-data ((Join-Path $here 'docs\Manual_de_usuario.pdf') + ';docs') `
    --exclude-module tkinter `
    --distpath $dist --workpath (Join-Path $buildRoot 'work') --specpath $buildRoot `
    (Join-Path $here 'main.py')
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller falló.' }

Write-Output '3/3 Compilando el instalador con Inno Setup...'
$iscc = @("${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
          "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $iscc) { throw 'No se encontró Inno Setup 6. Instálelo con: winget install JRSoftware.InnoSetup' }
& $iscc /Q ("/DDistDir=" + (Join-Path $dist 'SimuladorAFD')) instalador.iss
if ($LASTEXITCODE -ne 0) { throw 'Inno Setup falló.' }

Write-Output ('Listo: ' + (Join-Path $here 'instalador\Instalador_Simulador_AFD.exe'))
