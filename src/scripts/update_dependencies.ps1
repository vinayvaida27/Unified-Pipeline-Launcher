<#
.SYNOPSIS
    Add or update Python dependencies, then refresh the bundled runtime.

.DESCRIPTION
    This is the public maintainer path for dependency changes. Requirements
    files are the source of truth; this script updates them when requested,
    installs launcher plus app dependencies into runtime\, and validates the
    imports needed to start the desktop launcher and Streamlit apps.

.EXAMPLE
    .\src\scripts\update_dependencies.ps1

.EXAMPLE
    .\src\scripts\update_dependencies.ps1 -Target launcher -Package "requests>=2.32,<3"

.EXAMPLE
    .\src\scripts\update_dependencies.ps1 -Target app -AppId 01_hello_pipeline -Package "plotly>=5,<6"
#>

param(
    [ValidateSet("launcher", "app")]
    [string]$Target = "launcher",

    [string]$AppId = "",

    [string]$Package = "",

    [string]$ReleaseDir = "",

    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$SourceRoot = Split-Path -Parent $PSScriptRoot
$PublicRoot = Split-Path -Parent $SourceRoot
if ($ReleaseDir -eq "") {
    $ReleaseDir = $PublicRoot
}
$ReleaseDir = (Resolve-Path $ReleaseDir).Path
$ReleaseSourceRoot = Join-Path $ReleaseDir "src"
if (-not (Test-Path $ReleaseSourceRoot)) {
    $ReleaseSourceRoot = $ReleaseDir
}

function Normalize-RequirementName {
    param([Parameter(Mandatory=$true)][string]$Spec)

    $Trimmed = $Spec.Trim()
    if ($Trimmed -eq "" -or $Trimmed.StartsWith("#") -or $Trimmed.StartsWith("-")) {
        return ""
    }

    $Match = [regex]::Match($Trimmed, "^[A-Za-z0-9_.-]+")
    if (-not $Match.Success) {
        return ""
    }
    return $Match.Value.ToLowerInvariant().Replace("_", "-")
}

function Update-RequirementFile {
    param(
        [Parameter(Mandatory=$true)][string]$Path,
        [Parameter(Mandatory=$true)][string]$Spec
    )

    $PackageName = Normalize-RequirementName $Spec
    if ($PackageName -eq "") {
        throw "Package must start with a package name, for example: streamlit>=1.40,<2"
    }

    $Parent = Split-Path -Parent $Path
    if (-not (Test-Path $Parent)) {
        New-Item -ItemType Directory -Path $Parent | Out-Null
    }
    if (-not (Test-Path $Path)) {
        New-Item -ItemType File -Path $Path | Out-Null
    }

    $Lines = @(Get-Content -Path $Path -ErrorAction SilentlyContinue)
    $Updated = $false
    for ($Index = 0; $Index -lt $Lines.Count; $Index++) {
        if ((Normalize-RequirementName $Lines[$Index]) -eq $PackageName) {
            $Lines[$Index] = $Spec
            $Updated = $true
            break
        }
    }

    if (-not $Updated) {
        $Lines += $Spec
    }

    $Lines | Set-Content -Path $Path -Encoding UTF8
    Write-Host "Updated requirement: $Path"
}

function Get-AppRequirementFile {
    param([Parameter(Mandatory=$true)][string]$RequestedAppId)

    if ($RequestedAppId -eq "") {
        throw "Use -AppId when -Target app is selected."
    }

    $AppsRoot = Join-Path $ReleaseDir "apps"
    $AppsJson = Join-Path $AppsRoot "apps.json"
    if (-not (Test-Path $AppsJson)) {
        throw "App registry not found: $AppsJson"
    }

    $Registry = Get-Content $AppsJson -Raw | ConvertFrom-Json
    $App = $Registry.applications | Where-Object {
        $_.id -eq $RequestedAppId -or $_.folder -eq $RequestedAppId
    } | Select-Object -First 1

    if (-not $App) {
        throw "App was not found in the app registry: $RequestedAppId"
    }

    return Join-Path $AppsRoot "$($App.folder)\requirements.txt"
}

    if ($Package -ne "") {
    if ($Target -eq "launcher") {
        $RequirementFile = Join-Path $ReleaseSourceRoot "requirements-launcher.txt"
    } else {
        $RequirementFile = Get-AppRequirementFile $AppId
    }
    Update-RequirementFile -Path $RequirementFile -Spec $Package
} else {
    Write-Host "No package supplied. Reinstalling and validating existing requirements."
}

$Python = Join-Path $ReleaseSourceRoot "runtime\python.exe"
if (-not (Test-Path $Python)) {
    if ($ReleaseDir -ne $PublicRoot) {
        throw "Runtime not found at $Python. Prepare the runtime in the release folder first."
    }

    Write-Host "Runtime not found. Fetching pinned portable Python runtime..."
    & (Join-Path $PSScriptRoot "fetch_runtime.ps1")
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if ($SkipInstall) {
    Write-Host "Skipped runtime install. Requirements files were updated only."
    exit 0
}

& (Join-Path $PSScriptRoot "prepare_shared_runtime.ps1") -ReleaseDir $ReleaseDir
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Dependency update complete."
