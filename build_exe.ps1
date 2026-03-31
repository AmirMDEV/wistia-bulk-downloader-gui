Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Set-Location $PSScriptRoot

py -m pip install --user --upgrade pyinstaller==6.17.0
py -m PyInstaller --noconfirm --clean --onefile --noconsole --name WistiaDownloaderGUI --hidden-import wistia app.pyw
