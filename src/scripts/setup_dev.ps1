param()

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot "common.ps1")
Clear-LauncherPythonEnvironment
$Uv = & (Join-Path $PSScriptRoot "ensure_uv.ps1")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $Uv sync --project $Root --locked
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $Uv run --project $Root --locked python -I -c "import PySide6, streamlit; print('PySide6 and Streamlit validated')"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Development environment ready."
Write-Host "Test:  & `"$Uv`" run --project src --locked pytest src\tests"
Write-Host "Run: powershell -ExecutionPolicy Bypass -File .\src\scripts\run_launcher_dev.ps1"
