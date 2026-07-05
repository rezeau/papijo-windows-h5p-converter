param(
    [switch] $SkipTests
)

$ErrorActionPreference = 'Stop'

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

if (-not $SkipTests) {
    python -m unittest discover -s tests
}

python -m PyInstaller `
    --onefile `
    --windowed `
    --clean `
    --name Papijo-Windows-H5p-Converter `
    .\src\papijo_converter_app.py

Write-Host ''
Write-Host 'Built executable:'
Write-Host (Join-Path $ProjectRoot 'dist\Papijo-Windows-H5p-Converter.exe')
