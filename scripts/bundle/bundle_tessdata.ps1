#!/usr/bin/env pwsh
# scripts/bundle/bundle_tessdata.ps1
# Stages Tesseract OCR traineddata (eng.traineddata) for offline OCR execution.

$ErrorActionPreference = 'Stop'
$TargetDir = Join-Path $PSScriptRoot "../../desktop_shell/bundle/tesseract_win/tessdata"
$TessDataUrl = "https://github.com/tesseract-ocr/tessdata_fast/raw/main/eng.traineddata"
$TargetFile = Join-Path $TargetDir "eng.traineddata"

Write-Host "== Bundling Tesseract TrainedData (eng.traineddata) =="

if (-not (Test-Path $TargetDir)) {
    New-Item -ItemType Directory -Path $TargetDir -Force
}

if (-not (Test-Path $TargetFile)) {
    Write-Host "Downloading eng.traineddata from $TessDataUrl ..."
    Invoke-WebRequest -Uri $TessDataUrl -OutFile $TargetFile
    Write-Host "Downloaded eng.traineddata successfully."
} else {
    Write-Host "eng.traineddata is already present at $TargetFile."
}

Write-Host "== TrainedData bundling complete =="
