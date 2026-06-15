<#
.SYNOPSIS
    Build the one-click Setup.exe installer for the Unified Streamlit Launcher.

.DESCRIPTION
    1. Builds the portable release folder (launcher.exe + runtime + apps...).
    2. Verifies a bundled Python runtime is present (unless you rely on the
       auto-download fallback).
    3. Compiles build_scripts\installer.nsis with NSIS into a single Setup.exe.

    Requires NSIS (makensis). Install once with:  winget install NSIS.NSIS

.EXAMPLE
    .\src\scripts\build_installer.ps1
    .\src\scripts\build_installer.ps1 -SkipBuild   # reuse an existing release folder
#>
param(
    [switch]$SkipBuild,
    [switch]$AllowMissingRuntime
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$ReleaseDir = Join-Path $Root "build\Unified-Streamlit-Launcher"
$Nsi = Join-Path $Root "build_scripts\installer.nsis"
$Setup = Join-Path $Root "build\UnifiedStreamlitLauncherSetup.exe"

# 1. Build the release folder unless reusing one.
if (-not $SkipBuild) {
    Write-Host "Building release folder..."
    & (Join-Path $Root "scripts\build_exe.ps1")
}
if (-not (Test-Path (Join-Path $ReleaseDir "launcher.exe"))) {
    throw "Release not found. Run .\src\scripts\build_exe.ps1 first (or omit -SkipBuild)."
}

# 2. Guard: a release without a bundled runtime only works if auto-download is on.
$BundledPython = Join-Path $ReleaseDir "runtime\python.exe"
if (-not (Test-Path $BundledPython) -and -not $AllowMissingRuntime) {
    Write-Warning "No bundled runtime at runtime\python.exe."
    Write-Warning "Run .\src\scripts\fetch_runtime.ps1 (recommended) or .\src\scripts\pin_runtime_download.ps1"
    Write-Warning "to enable the auto-download fallback, then rebuild. Use -AllowMissingRuntime to override."
    throw "Aborting: installer would ship without a Python runtime."
}

# 3. Locate makensis.
$MakeNsis = (Get-Command makensis.exe -ErrorAction SilentlyContinue).Source
if (-not $MakeNsis) {
    foreach ($candidate in @(
        "$env:ProgramFiles\NSIS\makensis.exe",
        "${env:ProgramFiles(x86)}\NSIS\makensis.exe"
    )) {
        if (Test-Path $candidate) { $MakeNsis = $candidate; break }
    }
}
if (-not $MakeNsis) {
    throw "NSIS (makensis.exe) not found. Install it with:  winget install NSIS.NSIS"
}

# 4. Compile.
Write-Host "Compiling installer with $MakeNsis ..."
& $MakeNsis "/DSOURCE_DIR=$ReleaseDir" "/DOUT_FILE=$Setup" $Nsi
if ($LASTEXITCODE -ne 0) { throw "makensis failed with exit code $LASTEXITCODE" }

Write-Host ""
Write-Host "Done. One-click installer created:"
Write-Host "  $Setup"
Write-Host "Hand this single file to users -- they double-click it to install."
