param([string]$Config = "config\launcher_config.json")

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$PublicRoot = Split-Path -Parent $Root
$Python = Join-Path $PublicRoot ".venv\Scripts\python.exe"
if (!(Test-Path $Python)) {
  $Python = Join-Path $Root ".venv\Scripts\python.exe"
}
if (!(Test-Path $Python)) {
  $Python = (Get-Command python).Source
}
Push-Location $Root
try {
  & $Python -m launcher --development --config (Join-Path $Root $Config)
} finally {
  Pop-Location
}
