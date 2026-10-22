# Instala solo en esta carpeta. No modifica el PATH ni requiere administrador.
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear el entorno virtual. Se necesita Python 3.10 o posterior.' }
}
& '.\.venv\Scripts\python.exe' -B -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron instalar las dependencias de Python.' }

$localDot = Join-Path $PSScriptRoot 'tools/graphviz/Grafis/bin/dot.exe'
$systemDot = Get-Command dot -ErrorAction SilentlyContinue
if (-not (Test-Path -LiteralPath $localDot) -and -not $systemDot -and -not $env:AFD_DOT) {
    $releaseUrl = 'https://gitlab.com/api/v4/projects/4207231/packages/generic/graphviz-releases/16.1.0/windows_10_cmake_Release_Graphviz-16.1.0-win64.zip'
    $expectedHash = '733E49626C492242EB8DCA30EA627B6EAD20710E207998C7933B4909D92D6ABC'
    New-Item -ItemType Directory -Force -Path 'tools/downloads' | Out-Null
    $archivePath = Join-Path $PSScriptRoot 'tools/downloads/graphviz.zip'
    Invoke-WebRequest -Uri $releaseUrl -OutFile $archivePath
    $actualHash = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash
    if ($actualHash -ne $expectedHash) { throw 'El SHA256 de Graphviz no coincide con el archivo oficial. No se instalará.' }
    Expand-Archive -LiteralPath $archivePath -DestinationPath (Join-Path $PSScriptRoot 'tools/graphviz') -Force
    $extractedRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot 'tools/graphviz/Graphviz-16.1.0-win64')).Path
    $destinationRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot 'tools/graphviz/Grafis'))
    $projectRoot = (Resolve-Path -LiteralPath $PSScriptRoot).Path
    foreach ($targetPath in @($extractedRoot,$destinationRoot)) {
        if (-not $targetPath.StartsWith($projectRoot + [IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) {
            throw 'La ruta de Graphviz está fuera del proyecto.'
        }
    }
    Move-Item -LiteralPath $extractedRoot -Destination $destinationRoot
    Remove-Item -LiteralPath $archivePath -Force
}

# Graphviz 16.1.0: dot, salida JSON y tipografía Pango, con sus dependencias.
$portableRoot = Join-Path $PSScriptRoot 'tools/graphviz/Grafis'
if (Test-Path -LiteralPath $portableRoot) {
    $resolvedPortableRoot = (Resolve-Path -LiteralPath $portableRoot).Path
    $graphvizRuntime = @(
        'brotlicommon.dll','brotlidec.dll','bz2.dll','cairo-2.dll','cdt.dll',
        'cgraph.dll','dot.exe','ffi-8.dll','fontconfig-1.dll','freetype.dll',
        'fribidi-0.dll','gio-2.0-0.dll','glib-2.0-0.dll','gmodule-2.0-0.dll',
        'gobject-2.0-0.dll','gvc.dll','gvplugin_core.dll','gvplugin_dot_layout.dll',
        'gvplugin_pango.dll','harfbuzz.dll','iconv-2.dll','intl-8.dll','libexpat.dll',
        'libpng16.dll','pango-1.0-0.dll','pangocairo-1.0-0.dll','pangoft2-1.0-0.dll',
        'pangowin32-1.0-0.dll','pathplan.dll','pcre2-8.dll','pixman-1-0.dll',
        'vcruntime140.dll','vcruntime140_1.dll','xdot.dll','zlib1.dll'
    )
    $extras = @('include','lib','share') | ForEach-Object { Join-Path $resolvedPortableRoot $_ }
    $extras += @(Get-ChildItem -LiteralPath (Join-Path $resolvedPortableRoot 'bin') -File | Where-Object { $_.Extension -in @('.exe','.dll') -and $_.Name -notin $graphvizRuntime } | ForEach-Object { $_.FullName })
    $extras += @('bin/dot_sandbox','bin/gvmap.sh','bin/config8') | ForEach-Object { Join-Path $resolvedPortableRoot $_ }
    foreach ($extra in $extras) {
        if (-not (Test-Path -LiteralPath $extra)) { continue }
        $resolvedExtra = (Resolve-Path -LiteralPath $extra).Path
        if (-not $resolvedExtra.StartsWith($resolvedPortableRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
            throw 'La ruta de limpieza está fuera de la instalación portátil de Graphviz.'
        }
        Remove-Item -LiteralPath $resolvedExtra -Recurse -Force
    }
    # Actualiza el registro para no intentar cargar plugins que se eliminaron.
    & $localDot -c
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo configurar el registro de plugins de Graphviz.' }
}

# La interfaz usa QtCore, QtGui y QtWidgets, sin QML ni herramientas de diseño.
$resolvedProjectRoot = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$qtRoot = Join-Path $resolvedProjectRoot '.venv/Lib/site-packages/PySide6'
$bindingRoot = Join-Path $resolvedProjectRoot '.venv/Lib/site-packages/shiboken6'
$qtExtras = @('doc','glue','include','lib','metatypes','qml','scripts','typesystems') | ForEach-Object { Join-Path $qtRoot $_ }
$qtExtras += @('include','lib') | ForEach-Object { Join-Path $bindingRoot $_ }
$qtExtras += @(Get-ChildItem -LiteralPath $qtRoot -File | Where-Object { $_.Extension -in @('.exe','.lib','.pyi') } | ForEach-Object { $_.FullName })
$qtExtras += @(Get-ChildItem -LiteralPath $bindingRoot -File | Where-Object { $_.Extension -in @('.lib','.pyi') } | ForEach-Object { $_.FullName })
$qtExtras += @(Get-ChildItem -LiteralPath $qtRoot -File -Filter 'Qt*.pyd' | Where-Object { $_.Name -notin @('QtCore.pyd','QtGui.pyd','QtWidgets.pyd') } | ForEach-Object { $_.FullName })
$qtExtras += @(Get-ChildItem -LiteralPath (Join-Path $resolvedProjectRoot '.venv/Scripts') -File -Filter 'pyside6-*.exe' | ForEach-Object { $_.FullName })
# Las DLL de Network y Svg también sostienen plugins de la interfaz de Windows.
$qtRuntime = @('Qt6Core.dll','Qt6Gui.dll','Qt6Widgets.dll','Qt6Network.dll','Qt6Svg.dll')
$qtExtras += @(Get-ChildItem -LiteralPath $qtRoot -File -Filter 'Qt6*.dll' | Where-Object { $_.Name -notin $qtRuntime } | ForEach-Object { $_.FullName })
$qtExtras += @(Join-Path $qtRoot 'pyside6qml.abi3.dll')
$qtExtras += @('designer','qmltooling','sqldrivers','vectorimageformats') | ForEach-Object { Join-Path $qtRoot ('plugins/' + $_) }
foreach ($extra in $qtExtras) {
    if (-not (Test-Path -LiteralPath $extra)) { continue }
    $resolvedExtra = (Resolve-Path -LiteralPath $extra).Path
    if (-not $resolvedExtra.StartsWith($resolvedProjectRoot + [IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) {
        throw 'La ruta de limpieza está fuera del proyecto.'
    }
    Remove-Item -LiteralPath $resolvedExtra -Recurse -Force
}

& '.\.venv\Scripts\python.exe' -B -c "from diagram import find_dot, calculate_layout; from afd_core import EXAMPLES; print('Graphviz:', find_dot()); print('Estados de prueba:', len(calculate_layout(EXAMPLES[0])['objects']) - 1)"
if ($LASTEXITCODE -ne 0) { throw 'La verificación de Graphviz falló. Revisá AFD_DOT y la instalación.' }
Write-Output 'Configuración completa. Abrí INICIAR.bat para iniciar AFD.'
