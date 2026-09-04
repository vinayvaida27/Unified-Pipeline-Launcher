<#
.SYNOPSIS
    Update the shared runtime and every recognized launcher virtual environment.

.DESCRIPTION
    Synchronizes the development environment from uv.lock, updates packages in
    the bundled runtime and app environments with uv, then validates each one.

.PARAMETER DryRun
    Discover and print the update plan without changing an environment.
#>

param(
    [string]$ReleaseDir = "",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "common.ps1")
Clear-LauncherPythonEnvironment
$SourceRoot = Split-Path -Parent $PSScriptRoot
$DefaultRoot = Split-Path -Parent $SourceRoot
if ($ReleaseDir -eq "") { $ReleaseDir = $DefaultRoot }
$Root = Resolve-LauncherPath $ReleaseDir
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

Add-UpdateJob "repository development environment" (Join-Path $Root ".venv\Scripts\python.exe") "project:dev"
Add-UpdateJob "source development environment" (Join-Path $ReleaseSourceRoot ".venv\Scripts\python.exe") "project:dev"

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
$Uv = ""
if (-not $DryRun) {
    $Uv = & (Join-Path $PSScriptRoot "ensure_uv.ps1")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
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
            & $Uv pip check --python $SharedPython --no-config
            if ($LASTEXITCODE -ne 0) { throw "uv dependency check exited $LASTEXITCODE" }
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
    } elseif ($Job.Requirement -eq "project:dev") {
        Write-Host "  Source: pyproject.toml + uv.lock"
    } else {
        Write-Host "  Requirements: $($Job.Requirement)"
    }
    if ($DryRun) {
        Write-Host "  PLAN: uv sync/install, uv pip check, import streamlit"
        continue
    }
    try {
        if ($Job.Requirement -eq "project:dev") {
            $EnvironmentPath = Split-Path -Parent (Split-Path -Parent $Job.Python)
            $PythonVersion = & $Job.Python -I -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
            $PreviousProjectEnvironment = $env:UV_PROJECT_ENVIRONMENT
            try {
                $env:UV_PROJECT_ENVIRONMENT = $EnvironmentPath
                & $Uv sync --project $ReleaseSourceRoot --locked --python $Job.Python
                $NeedsRebuild = $LASTEXITCODE -ne 0
                if (-not $NeedsRebuild) {
                    & $Uv pip check --python $Job.Python --no-config
                    $NeedsRebuild = $LASTEXITCODE -ne 0
                }
                if ($NeedsRebuild) {
                    Write-Warning "The development environment is incomplete; rebuilding it from uv.lock."
                    & $Uv venv --clear --python $PythonVersion $EnvironmentPath
                    if ($LASTEXITCODE -ne 0) { throw "development environment rebuild exited $LASTEXITCODE" }
                    & $Uv sync --project $ReleaseSourceRoot --locked --python $PythonVersion
                    if ($LASTEXITCODE -ne 0) { throw "development environment sync exited $LASTEXITCODE" }
                }
            } finally {
                if ($null -eq $PreviousProjectEnvironment) {
                    Remove-Item -LiteralPath "Env:UV_PROJECT_ENVIRONMENT" -ErrorAction SilentlyContinue
                } else {
                    $env:UV_PROJECT_ENVIRONMENT = $PreviousProjectEnvironment
                }
            }
        } elseif ($Job.Requirement -ne "") {
            $InstallArgs = @("pip", "install", "--python", $Job.Python, "--no-config", "--upgrade")
            $Wheelhouse = Join-Path (Split-Path -Parent $Job.Requirement) "wheelhouse"
            if (Test-Path -LiteralPath $Wheelhouse) {
                $Wheels = @(Get-ChildItem -LiteralPath $Wheelhouse -File -ErrorAction SilentlyContinue)
                if ($Wheels.Count -gt 0) { $InstallArgs += @("--no-index", "--find-links", $Wheelhouse) }
            }
            $InstallArgs += @("-r", $Job.Requirement)
            Push-Location -LiteralPath (Split-Path -Parent $Job.Requirement)
            try {
                & $Uv @InstallArgs
                if ($LASTEXITCODE -ne 0) { throw "requirements update exited $LASTEXITCODE" }
            } finally {
                Pop-Location
            }
        }
        & $Uv pip check --python $Job.Python --no-config
        if ($LASTEXITCODE -ne 0) { throw "uv dependency check exited $LASTEXITCODE" }
        & $Job.Python -I -c "import streamlit; print('  Streamlit', streamlit.__version__)"
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
