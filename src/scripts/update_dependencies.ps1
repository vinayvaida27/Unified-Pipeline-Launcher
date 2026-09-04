<#
.SYNOPSIS
    Add or update Python dependencies, then refresh the bundled runtime.

.DESCRIPTION
    Launcher dependencies are updated in pyproject.toml and uv.lock. App
    dependencies remain in each app's requirements.txt. The shared runtime is
    then resolved, installed, and validated with uv.

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
. (Join-Path $PSScriptRoot "common.ps1")
Clear-LauncherPythonEnvironment
$SourceRoot = Split-Path -Parent $PSScriptRoot
$PublicRoot = Split-Path -Parent $SourceRoot
if ($ReleaseDir -eq "") {
    $ReleaseDir = $PublicRoot
}
$ReleaseDir = Resolve-LauncherPath $ReleaseDir
$ReleaseSourceRoot = Join-Path $ReleaseDir "src"
if (-not (Test-Path -LiteralPath $ReleaseSourceRoot)) {
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
    if (-not (Test-Path -LiteralPath $Parent)) {
        New-Item -ItemType Directory -Path $Parent | Out-Null
    }
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType File -Path $Path | Out-Null
    }

    $Lines = @(Get-Content -LiteralPath $Path -ErrorAction SilentlyContinue)
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

    $Lines | Set-Content -LiteralPath $Path -Encoding UTF8
    Write-Host "Updated requirement: $Path"
}

function Get-AppRequirementFile {
    param([Parameter(Mandatory=$true)][string]$RequestedAppId)

    if ($RequestedAppId -eq "") {
        throw "Use -AppId when -Target app is selected."
    }

    $AppsRoot = Join-Path $ReleaseDir "apps"
    $AppsJson = Join-Path $AppsRoot "apps.json"
    if (-not (Test-Path -LiteralPath $AppsJson)) {
        throw "App registry not found: $AppsJson"
    }

    $Registry = Get-Content -LiteralPath $AppsJson -Raw | ConvertFrom-Json
    $App = $Registry.applications | Where-Object {
        $_.id -eq $RequestedAppId -or $_.folder -eq $RequestedAppId
    } | Select-Object -First 1

    if (-not $App) {
        throw "App was not found in the app registry: $RequestedAppId"
    }

    return Join-Path $AppsRoot "$($App.folder)\requirements.txt"
}

if ($Target -eq "launcher") {
    $ProjectFile = Join-Path $ReleaseSourceRoot "pyproject.toml"
    if (-not (Test-Path -LiteralPath $ProjectFile)) {
        throw "Launcher project metadata not found: $ProjectFile"
    }
    $Uv = & (Join-Path $PSScriptRoot "ensure_uv.ps1")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $ProjectArgument = if ($ReleaseSourceRoot -eq $ReleaseDir) { "." } else { "src" }
    $RequirementArgument = Join-Path $ProjectArgument "requirements-launcher.txt"
    Push-Location -LiteralPath $ReleaseDir
    try {
        if ($Package -ne "") {
            & $Uv add --project $ProjectArgument --no-sync $Package
        } else {
            Write-Host "No package supplied. Refreshing the launcher lock and compatibility requirements."
            & $Uv lock --project $ProjectArgument
        }
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        & $Uv export --project $ProjectArgument --locked --no-dev --no-emit-project --no-hashes --output-file $RequirementArgument
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    } finally {
        Pop-Location
    }
    Write-Host "Updated launcher dependencies: $ProjectFile"
} elseif ($Package -ne "") {
    $RequirementFile = Get-AppRequirementFile $AppId
    Update-RequirementFile -Path $RequirementFile -Spec $Package
} else {
    Write-Host "No package supplied. Reinstalling and validating existing app requirements."
}

$Python = Join-Path $ReleaseSourceRoot "runtime\python.exe"
if (-not (Test-Path -LiteralPath $Python)) {
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
