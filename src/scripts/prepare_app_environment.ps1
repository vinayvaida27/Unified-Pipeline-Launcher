param([Parameter(Mandatory=$true)][string]$AppId)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$PublicRoot = Split-Path -Parent $Root
$Python = Join-Path $PublicRoot ".venv\Scripts\python.exe"
if (!(Test-Path $Python)) { $Python = Join-Path $Root ".venv\Scripts\python.exe" }
if (!(Test-Path $Python)) { throw "Run src/scripts/setup_dev.ps1 first." }
& $Python -c "print('Prepare individual app environments through the launcher UI, or call EnvironmentManager from a small maintenance command. Requested app: $AppId')"
