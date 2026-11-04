param([string]$Config = "config\launcher_config.json")

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root "runtime\python.exe"
if (!(Test-Path $Python)) {
  throw "Production runtime is missing: $Python"
}
Push-Location $Root
try {
  & $Python -m launcher --config (Join-Path $Root $Config)
} finally {
  Pop-Location
}
