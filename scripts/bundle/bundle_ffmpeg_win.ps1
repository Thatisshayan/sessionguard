#!/usr/bin/env pwsh
# scripts/bundle/bundle_ffmpeg_win.ps1
# Stages Windows FFmpeg binaries from local path or gyan.dev.

$ErrorActionPreference = 'Stop'
$TargetDir = Join-Path $PSScriptRoot "../../desktop_shell/bundle/ffmpeg_win"
# Check common local install paths first to avoid large downloads
$LocalFF = "C:\ffmpeg\bin" # Common manual install path
$UserPath = (Get-Command ffmpeg.exe -ErrorAction SilentlyContinue).Source

Write-Host "== Bundling FFmpeg for Windows =="

if (-not (Test-Path $TargetDir)) {
    New-Item -ItemType Directory -Path $TargetDir -Force
}

if ($UserPath) {
    $UserFF = Split-Path $UserPath -Parent
    Write-Host "Found FFmpeg at $UserFF. Copying..."
    Copy-Item -Path "$UserFF\ffmpeg.exe" -Destination $TargetDir -Force
    Copy-Item -Path "$UserFF\ffprobe.exe" -Destination $TargetDir -Force
} elseif (Test-Path $LocalFF) {
    Write-Host "Copying FFmpeg from $LocalFF ..."
    Copy-Item -Path "$LocalFF\ffmpeg.exe" -Destination $TargetDir -Force
    Copy-Item -Path "$LocalFF\ffprobe.exe" -Destination $TargetDir -Force
} else {
    Write-Host "FFmpeg not found locally. Downloading minimal static build..."
    $Url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-git-essentials.7z"
    # Download-and-extract via 7z would go here.
    # For now, we'll prompt for manual placement or install.
    Write-Host "FFmpeg binaries (ffmpeg.exe, ffprobe.exe) must be placed in $TargetDir."
    exit 1
}

Write-Host "== FFmpeg bundling complete =="
