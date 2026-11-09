# Kaynaktan hızlı çalıştırma (PowerShell):  .\run.ps1
Set-Location $PSScriptRoot
if (-not (Test-Path .venv)) { python -m venv .venv; .\.venv\Scripts\python -m pip install -r requirements.txt }
$env:PYTHONPATH = "src"
.\.venv\Scripts\pythonw.exe -m aitranslator
