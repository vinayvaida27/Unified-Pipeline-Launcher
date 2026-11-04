# Pins the official Python runtime download in config/launcher_config.json.
# Downloads the pinned package once, computes its SHA-256, and enables the
# launcher's runtime-download fallback.
#
# Usage (from the repo root):
#   .\src\scripts\pin_runtime_download.ps1
#   .\src\scripts\pin_runtime_download.ps1 -Version 3.12.7

param(
    [string]$Version = "3.11.9",
    [string]$ConfigPath = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
if ($ConfigPath -eq "") {
    $ConfigPath = Join-Path $Root "config\launcher_config.json"
}

$url = "https://globalcdn.nuget.org/packages/python.$Version.nupkg"
$temp = Join-Path $env:TEMP "python-runtime-$Version.nupkg"

Write-Host "Downloading $url"
Invoke-WebRequest -Uri $url -OutFile $temp -UseBasicParsing

$hash = (Get-FileHash -Path $temp -Algorithm SHA256).Hash.ToLower()
Write-Host "SHA-256: $hash"

$config = Get-Content $ConfigPath -Raw | ConvertFrom-Json
$config.runtime.download.enabled = $true
$config.runtime.download.version = $Version
$config.runtime.download.url = $url
$config.runtime.download.sha256 = $hash
$config | ConvertTo-Json -Depth 10 | Set-Content $ConfigPath -Encoding UTF8

Remove-Item $temp
Write-Host "Pinned Python $Version in $ConfigPath (download fallback enabled)."
