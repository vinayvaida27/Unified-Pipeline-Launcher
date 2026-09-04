<#
.SYNOPSIS
    Update the shared runtime and every recognized launcher virtual environment.

.DESCRIPTION
    Updates packages from the repository requirements files, then runs pip check
    and a Streamlit import in each environment. Unknown/orphaned environments are
    checked but are not upgraded without a requirements file.

.PARAMETER DryRun
    Discover and print the update plan without changing an environment.
#>

param(
    [string]$ReleaseDir = "",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$SourceRoot = Split-Path -Parent $PSScriptRoot
$DefaultRoot = Split-Path -Parent $SourceRoot
$ReleaseDir = $ReleaseDir.Trim().Trim([char]34)
if ($ReleaseDir -eq "") { $ReleaseDir = $DefaultRoot }
$Root = (Resolve-Path -LiteralPath $ReleaseDir -ErrorAction Stop).Path
$ReleaseSourceRoot = Join-Path $Root "src"
if (-not (Test-Path -LiteralPath $ReleaseSourceRoot)) { $ReleaseSourceRoot = $Root }

$AppsRoot = Join-Path $Root "apps"
$AppsJson = Join-Path $AppsRoot "apps.json"
$ConfigPath = Join-Path $ReleaseSourceRoot "config\launcher_config.json"
if (-not (Test-Path -LiteralPath $AppsJson)) { throw "App registry not found: $AppsJson" }
if (-not (Test-Path -LiteralPath $ConfigPath)) { throw "Launcher config not found: $ConfigPath" }

$Registry = Get-Content -LiteralPath $AppsJson -Raw | ConvertFrom-Json
$Config = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
$RequirementsByApp = @{}
foreach ($App in $Registry.applications) {
    $Requirement = Join-Path $AppsRoot "$($App.folder)\requirements.txt"
    if (Test-Path -LiteralPath $Requirement) { $RequirementsByApp[$App.id] = $Requirement }
}

$CacheRoot = [Environment]::ExpandEnvironmentVariables($Config.paths.local_cache_directory)
if (-not [IO.Path]::IsPathRooted($CacheRoot)) {
    $CacheRoot = Join-Path (Split-Path -Parent $ConfigPath) $CacheRoot
}
$EnvironmentRoot = Join-Path $CacheRoot "environments"
$Jobs = [System.Collections.Generic.List[object]]::new()
$SeenPython = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
$DiscoveryFailures = [System.Collections.Generic.List[string]]::new()

function Add-UpdateJob {
    param(
        [string]$Name,
        [string]$Python,
        [string]$Requirement = ""
    )
    if (-not (Test-Path -LiteralPath $Python)) { return }
    $ResolvedPython = (Resolve-Path -LiteralPath $Python).Path
    if (-not $SeenPython.Add($ResolvedPython)) { return }
    $Jobs.Add([pscustomobject]@{ Name = $Name; Python = $ResolvedPython; Requirement = $Requirement })
}

$DevRequirement = Join-Path $ReleaseSourceRoot "requirements-dev.txt"
Add-UpdateJob "repository development environment" (Join-Path $Root ".venv\Scripts\python.exe") $DevRequirement
Add-UpdateJob "source development environment" (Join-Path $ReleaseSourceRoot ".venv\Scripts\python.exe") $DevRequirement

if (Test-Path -LiteralPath $EnvironmentRoot) {
    foreach ($AppDirectory in Get-ChildItem -LiteralPath $EnvironmentRoot -Directory -ErrorAction SilentlyContinue) {
        foreach ($VersionDirectory in Get-ChildItem -LiteralPath $AppDirectory.FullName -Directory -ErrorAction SilentlyContinue) {
            $VenvRoot = $VersionDirectory.FullName
            if (-not (Test-Path -LiteralPath (Join-Path $VenvRoot "pyvenv.cfg"))) {
                if (Test-Path -LiteralPath (Join-Path $VenvRoot "Scripts")) {
                    $DiscoveryFailures.Add("incomplete app environment (missing pyvenv.cfg): $VenvRoot")
                }
                continue
            }
            $Python = Join-Path $VenvRoot "Scripts\python.exe"
            if (-not (Test-Path -LiteralPath $Python)) {
                $DiscoveryFailures.Add("incomplete app environment (missing python.exe): $VenvRoot")
                continue
            }
            $Relative = "$($AppDirectory.Name)\$($VersionDirectory.Name)"
            $Requirement = if ($RequirementsByApp.ContainsKey($AppDirectory.Name)) {
                $RequirementsByApp[$AppDirectory.Name]
            } else {
                ""
            }
            Add-UpdateJob "app environment $Relative" $Python $Requirement
        }
    }
}

Write-Host ""
Write-Host "============================================================"
Write-Host "  Unified Pipeline Launcher -- Package Update"
Write-Host "============================================================"
Write-Host "Repository : $Root"
Write-Host "Venvs     : $($Jobs.Count)"
Write-Host "Dry run   : $DryRun"

$Failures = [System.Collections.Generic.List[string]]::new()
foreach ($Failure in $DiscoveryFailures) { $Failures.Add($Failure) }
$SharedPython = Join-Path $ReleaseSourceRoot "runtime\python.exe"
Write-Host ""
Write-Host "[shared runtime] $SharedPython"
if (Test-Path -LiteralPath $SharedPython) {
    if ($DryRun) {
        Write-Host "  PLAN: reinstall and upgrade launcher plus all enabled app requirements"
    } else {
        try {
            & (Join-Path $PSScriptRoot "prepare_shared_runtime.ps1") -ReleaseDir $Root -Upgrade
            if ($LASTEXITCODE -ne 0) { throw "prepare_shared_runtime.ps1 exited $LASTEXITCODE" }
            & $SharedPython -m pip check
            if ($LASTEXITCODE -ne 0) { throw "pip check exited $LASTEXITCODE" }
        } catch {
            $Failures.Add("shared runtime: $($_.Exception.Message)")
        }
    }
} elseif ($DryRun) {
    Write-Host "  PLAN: runtime is missing and must be created by INSTALL.bat"
} else {
    $Failures.Add("shared runtime missing: $SharedPython")
}

foreach ($Job in $Jobs) {
    Write-Host ""
    Write-Host "[$($Job.Name)] $($Job.Python)"
    if ($Job.Requirement -eq "") {
        Write-Warning "No matching requirements file; checking this environment without upgrading it."
    } else {
        Write-Host "  Requirements: $($Job.Requirement)"
    }
    if ($DryRun) {
        Write-Host "  PLAN: pip install --upgrade, pip check, import streamlit"
        continue
    }
    try {
        & $Job.Python -m pip install --upgrade pip
        if ($LASTEXITCODE -ne 0) { throw "pip upgrade exited $LASTEXITCODE" }
        if ($Job.Requirement -ne "") {
            Push-Location -LiteralPath (Split-Path -Parent $Job.Requirement)
            try {
                & $Job.Python -m pip install --upgrade -r $Job.Requirement
                if ($LASTEXITCODE -ne 0) { throw "requirements update exited $LASTEXITCODE" }
            } finally {
                Pop-Location
            }
        }
        & $Job.Python -m pip check
        if ($LASTEXITCODE -ne 0) { throw "pip check exited $LASTEXITCODE" }
        & $Job.Python -c "import streamlit; print('  Streamlit', streamlit.__version__)"
        if ($LASTEXITCODE -ne 0) { throw "Streamlit import exited $LASTEXITCODE" }
    } catch {
        $Failures.Add("$($Job.Name): $($_.Exception.Message)")
    }
}

Write-Host ""
if ($Failures.Count -gt 0) {
    Write-Host "Package update finished with $($Failures.Count) error(s):" -ForegroundColor Red
    foreach ($Failure in $Failures) { Write-Host "  - $Failure" -ForegroundColor Red }
    exit 1
}

Write-Host "All discovered Python environments passed package update checks." -ForegroundColor Green
exit 0
