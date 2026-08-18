#!/usr/bin/env pwsh
# scripts/bundle/bundle_python_win.ps1
# Downloads and stages Windows embeddable Python with SessionGuard dependencies.

$ErrorActionPreference = 'Stop'
$PythonVer = "3.11.9"
$PythonUrl = "https://www.python.org/ftp/python/$PythonVer/python-$PythonVer-embed-amd64.zip"
$TargetDir = Join-Path $PSScriptRoot "../../desktop_shell/bundle/python_win"
$TempZip = Join-Path $env:TEMP "python-embed.zip"

Write-Host "== Bundling Python for Windows ($PythonVer) =="

if (-not (Test-Path $TargetDir)) {
    New-Item -ItemType Directory -Path $TargetDir -Force
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
pip install -r $ReqFile --target $SitePackages --no-compile --no-cache-dir

Write-Host "== Python bundling complete =="
