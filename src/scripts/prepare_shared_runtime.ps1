<#
.SYNOPSIS
    ONE-TIME admin setup for network drive deployments.

.DESCRIPTION
    Reads every app from the app registry, collects all requirements.txt files,
    and installs every package directly into the bundled runtime's site-packages.
    After this runs once, ALL users get instant app launches -- no venv creation,
    no pip install, no waiting.

    Run this:
      - Once after placing the release folder on the network drive.
      - Again whenever you add a new app or bump a package version.

    Requires write access to the bundled runtime folder.

.PARAMETER ReleaseDir
    Path to the repository or portable release folder.
    Auto-detected: checks build\Unified-Pipeline-Launcher\ first, then the
    repo root itself (so you can run this directly from a repo on a network drive).

.EXAMPLE
    .\src\scripts\prepare_shared_runtime.ps1
    .\src\scripts\prepare_shared_runtime.ps1 -ReleaseDir "Z:\Unified-Pipeline-Launcher"
#>

param(
    [string]$ReleaseDir = "",
    [switch]$Upgrade
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "common.ps1")
if ($ReleaseDir -ne "") { $ReleaseDir = Normalize-LauncherPathInput $ReleaseDir }
Clear-LauncherPythonEnvironment

if ($ReleaseDir -eq "") {
    $SourceRoot = Split-Path -Parent $PSScriptRoot
    $ScriptParent = Split-Path -Parent $SourceRoot
    $BuildRelease = Join-Path $SourceRoot "build\Unified-Pipeline-Launcher"
    if (Test-Path -LiteralPath (Join-Path $BuildRelease "runtime\python.exe")) {
        $ReleaseDir = $BuildRelease
    }
    elseif (Test-Path -LiteralPath (Join-Path $ScriptParent "src\runtime\python.exe")) {
        $ReleaseDir = $ScriptParent
    }
    else {
        $ReleaseDir = $ScriptParent
    }
}

$ReleaseDir = Resolve-LauncherPath $ReleaseDir
$SourceRoot = Join-Path $ReleaseDir "src"
if (-not (Test-Path -LiteralPath $SourceRoot)) { $SourceRoot = $ReleaseDir }

Write-Host ""
Write-Host "============================================================"
Write-Host "  Unified Pipeline Launcher -- Shared Runtime Setup"
Write-Host "============================================================"
Write-Host "Release folder : $ReleaseDir"

$Python = Join-Path $SourceRoot "runtime\python.exe"
if (-not (Test-Path -LiteralPath $Python)) {
    Write-Error @"
Bundled runtime not found at: $Python

Run src\scripts\fetch_runtime.ps1 first to download a portable Python runtime,
then re-run this script.
"@
    exit 1
}

# Detect damaged distributions before uv attempts an in-place update. A missing
# RECORD means the environment cannot be safely uninstalled/upgraded. Rebuild
# the portable runtime instead of leaving a partially repaired installation.
$SitePackages = Join-Path $SourceRoot "runtime\Lib\site-packages"
if (Test-Path -LiteralPath $SitePackages) {
    $BrokenDistInfo = @(
        Get-ChildItem -LiteralPath $SitePackages -Directory -Filter "*.dist-info" -ErrorAction SilentlyContinue |
            Where-Object { -not (Test-Path -LiteralPath (Join-Path $_.FullName "RECORD")) }
    )
    if ($BrokenDistInfo.Count -gt 0) {
        Write-Warning "Damaged Python package metadata was detected:"
        $BrokenDistInfo | ForEach-Object { Write-Warning "  $($_.Name) (missing RECORD)" }
        Write-Host "Rebuilding the portable runtime before installing packages..."
        & (Join-Path $PSScriptRoot "fetch_runtime.ps1")
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        $Python = Join-Path $SourceRoot "runtime\python.exe"
    }
}

Write-Host "Runtime python : $Python"
Assert-LauncherPythonRuntime $Python
$PythonVersion = & $Python --version 2>&1
Write-Host "Python version : $PythonVersion"
$Uv = & (Join-Path $PSScriptRoot "ensure_uv.ps1")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "Dependency tool: $(& $Uv --version)"

$AppsRoot = Join-Path $ReleaseDir "apps"
$AppsJson = Join-Path $AppsRoot "apps.json"
if (-not (Test-Path -LiteralPath $AppsJson)) {
    Write-Error "App registry not found: $AppsJson"
    exit 1
}
$Registry = Get-Content -LiteralPath $AppsJson -Raw | ConvertFrom-Json

$AllRequirements = @()
$AllWheelhouses  = @()

$LauncherRequirements = Join-Path $SourceRoot "requirements-launcher.txt"
if (Test-Path -LiteralPath $LauncherRequirements) {
    $AllRequirements += $LauncherRequirements
    Write-Host "  Found launcher requirements: requirements-launcher.txt"
} else {
    Write-Error "Launcher requirements not found: $LauncherRequirements"
    exit 1
}

foreach ($App in $Registry.applications) {
    if ($App.enabled -eq $false) { continue }
    $AppFolder = Join-Path $AppsRoot $App.folder
    $ReqFile = Join-Path $AppFolder "requirements.txt"
    if (Test-Path -LiteralPath $ReqFile) {
        $AllRequirements += $ReqFile
        Write-Host "  Found requirements: apps\$($App.folder)\requirements.txt"
    } else {
        Write-Host "  (no requirements.txt for $($App.name))"
    }
    $WheelDir = Join-Path $AppFolder "wheelhouse"
    if ((Test-Path -LiteralPath $WheelDir) -and @(Get-ChildItem -LiteralPath $WheelDir -File -ErrorAction SilentlyContinue).Count -gt 0) {
        $AllWheelhouses += $WheelDir
    }
}

$TempReq = [System.IO.Path]::GetTempFileName() + ".txt"
$Lines = @("# Auto-generated by prepare_shared_runtime.ps1")
foreach ($ReqFile in $AllRequirements) {
    $Lines += "# --- $ReqFile ---"
    $Lines += Get-Content -LiteralPath $ReqFile
}
$Lines | Set-Content -LiteralPath $TempReq -Encoding UTF8
Write-Host ""
Write-Host "Merged $($AllRequirements.Count) requirements file(s)."

Write-Host ""
Write-Host "Installing all packages into shared runtime..."
Write-Host "(This may take a few minutes on first run.)"
Write-Host ""

# The uv cache is normally local while this runtime may be on a mapped/UNC
# filesystem. Windows hardlinks cannot cross filesystems, so request copy mode
# directly instead of failing a hardlink attempt and then falling back.
$UvArgs = @("pip", "install", "--python", $Python, "--no-config", "--link-mode=copy")
if ($Upgrade) { $UvArgs += "--upgrade" }

if ($AllWheelhouses.Count -gt 0) {
    Write-Host "Trying local wheelhouse(s) without network access."
    foreach ($WheelDir in $AllWheelhouses) {
        $UvArgs += "--find-links"
        $UvArgs += $WheelDir
    }
}

$UvArgs += "-r"
$UvArgs += $TempReq

if ($AllWheelhouses.Count -gt 0) {
    & $Uv @UvArgs --offline
    $ExitCode = $LASTEXITCODE
    if ($ExitCode -ne 0) {
        Write-Host "Local wheelhouses were incomplete; retrying with the package index."
        & $Uv @UvArgs
        $ExitCode = $LASTEXITCODE
    }
} else {
    & $Uv @UvArgs
    $ExitCode = $LASTEXITCODE
}

Remove-Item -LiteralPath $TempReq -Force -ErrorAction SilentlyContinue
if ($ExitCode -ne 0) {
    Write-Error "Package installation failed (exit code $ExitCode)."
    exit $ExitCode
}

Write-Host ""
Write-Host "Verifying launcher and Streamlit imports..."
& $Uv pip check --python $Python --no-config
if ($LASTEXITCODE -ne 0) {
    Write-Error "Shared runtime dependency check failed."
    exit 1
}
Assert-LauncherPythonRuntime $Python
& $Python -I -c "import encodings, pandas; from PySide6.QtWidgets import QApplication; import streamlit; print('  encodings, pandas, PySide6 and streamlit OK')"
if ($LASTEXITCODE -ne 0) {
    Write-Error "Runtime import validation failed after installation."
    exit 1
}

# Store a relocatable marker: no absolute release path or requirement paths.
# Get-LauncherRelativePath is compatible with Windows PowerShell 5.1, unlike
# [IO.Path]::GetRelativePath(), which exists only on newer .NET runtimes.
$RequirementSummary = @()
foreach ($ReqFile in $AllRequirements) {
    $Relative = Get-LauncherRelativePath -BasePath $ReleaseDir -Path $ReqFile
    $Hash = (Get-FileHash -LiteralPath $ReqFile -Algorithm SHA256).Hash.ToLowerInvariant()
    $RequirementSummary += [pscustomobject]@{ path = $Relative; sha256 = $Hash }
}
$Marker = @{
    prepared_at  = (Get-Date -Format "o")
    python       = $PythonVersion.ToString()
    installer    = "uv"
    uv_version   = (& $Uv --version).ToString()
    requirements = $RequirementSummary
} | ConvertTo-Json -Depth 4

$MarkerPath = Join-Path $SourceRoot "runtime\.shared_runtime_ready.json"
$Marker | Set-Content -LiteralPath $MarkerPath -Encoding UTF8

Write-Host ""
Write-Host "============================================================"
Write-Host "  Setup complete!"
Write-Host "============================================================"
Write-Host ""
Write-Host "All packages are installed. Users can now launch instantly."
Write-Host "Release folder: $ReleaseDir"
Write-Host ""
