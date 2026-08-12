#!/usr/bin/env pwsh
# scripts/bundle/bundle_tesseract_win.ps1
# Stages Windows Tesseract binaries from local install.

$ErrorActionPreference = 'Stop'
$TargetDir = Join-Path $PSScriptRoot "../../desktop_shell/bundle/tesseract_win"
$LocalTess = "C:\Program Files\Tesseract-OCR"

Write-Host "== Bundling Tesseract for Windows from Local Install =="

if (-not (Test-Path $TargetDir)) {
    New-Item -ItemType Directory -Path $TargetDir -Force
}

if (Test-Path $LocalTess) {
    Write-Host "Copying Tesseract from $LocalTess ..."
    # Copy binaries and tessdata
    Copy-Item -Path "$LocalTess\*" -Destination $TargetDir -Recurse -Force
} else {
    Write-Host "Tesseract not found at $LocalTess."
    Write-Host "Please install Tesseract for Windows (UB-Mannheim) first to stage the bundle."
    exit 1
}

Write-Host "== Tesseract bundling complete =="
