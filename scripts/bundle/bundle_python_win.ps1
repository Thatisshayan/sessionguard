#!/usr/bin/env pwsh
# scripts/bundle/bundle_python_win.ps1
# Downloads and stages Windows embeddable Python with SessionGuard dependencies.

$ErrorActionPreference = 'Stop'
$PythonVer = "3.11.9"
$PythonUrl = "https://www.python.org/ftp/python/$PythonVer/python-$PythonVer-embed-amd64.zip"
$TargetDir = Join-Path $PSScriptRoot "../../desktop_shell/bundle/python_win"
$TempZip = Join-Path $env:TEMP "python-embed.zip"
$BundleMajorMinor = (($PythonVer -split '\.')[0..1] -join '.')

Write-Host "== Bundling Python for Windows ($PythonVer) =="

$HostPyVersion = (& python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')").Trim()
if ($LASTEXITCODE -ne 0) {
    throw "Failed to run host python for bundling."
}
if ($HostPyVersion -ne $BundleMajorMinor) {
    throw "Host python $HostPyVersion does not match bundled runtime $BundleMajorMinor. Run this script with Python $BundleMajorMinor on PATH."
}

if (-not (Test-Path $TargetDir)) {
    New-Item -ItemType Directory -Path $TargetDir -Force
}
else {
    Get-ChildItem -Path $TargetDir -Force | Remove-Item -Recurse -Force
}

# 1. Download
Write-Host "Downloading $PythonUrl ..."
Invoke-WebRequest -Uri $PythonUrl -OutFile $TempZip

# 2. Extract
Write-Host "Extracting to $TargetDir ..."
Expand-Archive -Path $TempZip -DestinationPath $TargetDir -Force
Remove-Item $TempZip

# 3. Enable site-packages
# Embeddable python ignores site-packages by default. We must uncomment it in ._pth
$pthFile = Get-ChildItem -Path $TargetDir -Filter "*._pth" | Select-Object -First 1
if ($pthFile) {
    Write-Host "Configuring $($pthFile.Name) for site-packages..."
    $content = Get-Content $pthFile.FullName
    $content = $content -replace '#import site', 'import site'
    # Point the embeddable runtime at a clean bundled dependency tree
    $content += ".."
    $content += "Lib/sg_site_packages"
    $content | Set-Content $pthFile.FullName
}

# 4. Install dependencies
Write-Host "Installing requirements from backend/requirements.txt ..."
$ReqFile = Resolve-Path (Join-Path $PSScriptRoot "../../requirements.txt")
$SitePackages = Join-Path $TargetDir "Lib/sg_site_packages"

if (-not (Test-Path $SitePackages)) {
    New-Item -ItemType Directory -Path $SitePackages -Force
}

# Use local python to install into the bundle
# Note: Embeddable python doesn't have pip, we use system pip with --target
python -m pip install -r $ReqFile --target $SitePackages --no-compile --no-cache-dir

# 5. Smoke-test critical imports so compiled wheels fail here instead of in the installer
$EmbeddedPython = Join-Path $TargetDir "python.exe"
& $EmbeddedPython -c "import importlib; mods=['uvicorn','fastapi','multipart','jwt','structlog','dotenv','cv2','numpy','pandas','openpyxl','reportlab','pytesseract','aiosqlite','httpx','pydantic_core._pydantic_core']; [importlib.import_module(m) for m in mods]; print('BUNDLED_PYTHON_OK')"

Write-Host "== Python bundling complete =="
