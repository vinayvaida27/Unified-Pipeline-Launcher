param()

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$PublicRoot = Split-Path -Parent $Root
$Python = Join-Path $PublicRoot ".venv\Scripts\python.exe"
if (!(Test-Path $Python)) { $Python = Join-Path $Root ".venv\Scripts\python.exe" }
if (!(Test-Path $Python)) { throw "Run src/scripts/setup_dev.ps1 first." }

Write-Host "Building Unified Pipeline Launcher EXE release..."
& $Python (Join-Path $Root "build_scripts\build.py")
if ($LASTEXITCODE -ne 0) {
  exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Done. Release folder:"
Write-Host (Join-Path $Root "build\Unified-Pipeline-Launcher")
