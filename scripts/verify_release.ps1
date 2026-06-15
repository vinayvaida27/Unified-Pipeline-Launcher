param([Parameter(Mandatory=$true)][string]$Path)

$ErrorActionPreference = "Stop"
$Required = @("launcher.exe","START_LAUNCHER.vbs","START_LAUNCHER_DEBUG.bat","requirements-launcher.txt","config\launcher_config.json","config\platform_manifest.json","apps\apps.json","assets","runtime","docs")
foreach ($item in $Required) {
  $target = Join-Path $Path $item
  if (!(Test-Path $target)) { throw "Release validation failed. Missing $item" }
}

$appsRoot = Join-Path $Path "apps"
$registryPath = Join-Path $appsRoot "apps.json"
$registry = Get-Content $registryPath -Raw | ConvertFrom-Json
if (!$registry.applications -or $registry.applications.Count -lt 1) {
  throw "Release validation failed. apps/apps.json has no registered applications."
}

$defaultEntrypoint = $registry.defaults.entrypoint
if (!$defaultEntrypoint) {
  $defaultEntrypoint = "app.py"
}

foreach ($app in $registry.applications) {
  if (!$app.folder) {
    throw "Release validation failed. Registered app is missing folder."
  }
  $appFolder = Join-Path $appsRoot $app.folder
  if (!(Test-Path $appFolder)) {
    throw "Release validation failed. Missing registered app folder: $($app.folder)"
  }
  $entrypoint = $app.entrypoint
  if (!$entrypoint) {
    $entrypoint = $defaultEntrypoint
  }
  $entrypointPath = Join-Path $appFolder $entrypoint
  if (!(Test-Path $entrypointPath)) {
    throw "Release validation failed. Missing entrypoint for $($app.folder): $entrypoint"
  }
}

Write-Host "Release structure verified. Registered apps: $($registry.applications.Count)."
