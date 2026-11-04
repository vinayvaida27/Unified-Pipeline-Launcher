param()

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot "common.ps1")
Clear-LauncherPythonEnvironment
$Uv = & (Join-Path $PSScriptRoot "ensure_uv.ps1")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Building Unified Pipeline Launcher EXE release..."
& $Uv run --project $Root --locked python (Join-Path $Root "build_scripts\build.py")
if ($LASTEXITCODE -ne 0) {
  exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Done. Release folder:"
Write-Host (Join-Path $Root "build\Unified-Pipeline-Launcher")
