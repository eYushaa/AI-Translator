# AITranslator - Windows derleme betiği (PowerShell)
# Kullanım:  .\packaging\build.ps1
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
python -m venv .venv
.\.venv\Scripts\python -m pip install -U pip
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
.\.venv\Scripts\python -m pip install -e .
.\.venv\Scripts\python -m pytest -q
# İkon yoksa oluştur
if (-not (Test-Path "app.ico")) {
    .\.venv\Scripts\python -c "from PySide6.QtWidgets import QApplication; import sys; app = QApplication(sys.argv); from aitranslator.ui.theme import make_app_icon; make_app_icon(256).pixmap(256, 256).save('app.ico')"
}
.\.venv\Scripts\python -m PyInstaller --noconfirm --clean --onefile --windowed --name AITranslator `
  --icon app.ico --paths src --collect-all aitranslator --collect-all winrt --hidden-import winocr --collect-submodules keyring.backends `
  launcher.py
Write-Host "`nHazır (Tek .exe): dist\AITranslator.exe"
$iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
if (Test-Path $iscc) { & $iscc packaging\installer.iss; Write-Host "Kurulum sihirbazı: dist\AITranslator-Setup.exe" }
else { Write-Host "Kurulum sihirbazı için Inno Setup 6 kurup betiği tekrar çalıştırın (https://jrsoftware.org/isinfo.php)." }
