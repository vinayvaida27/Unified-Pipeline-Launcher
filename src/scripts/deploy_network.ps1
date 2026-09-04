<#
.SYNOPSIS
    Install or repair Unified Pipeline Launcher after cloning or updating.

.DESCRIPTION
    Run this once after git clone, again after every git pull, or whenever the
    bundled runtime becomes incomplete/corrupt.

    What it does:
      1. Validates the portable Python runtime and rebuilds it when missing or invalid
      2. Installs launcher and registered app packages into that runtime
      3. Creates START_LAUNCHER.lnk for no-console user launches

    No system Python installation is required. Everything runs from the bundled
    runtime in the repository/release folder.

.EXAMPLE
    cd "Z:\Unified-Pipeline-Launcher"
    .\src\scripts\deploy_network.ps1
#>

param()
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "common.ps1")
Clear-LauncherPythonEnvironment

$SourceRoot = Split-Path -Parent $PSScriptRoot
$Root = Split-Path -Parent $SourceRoot
$Python = Join-Path $SourceRoot "runtime\python.exe"

Write-Host ""
Write-Host "============================================================"
Write-Host "  Unified Pipeline Launcher -- Install / Repair"
Write-Host "  $Root"
Write-Host "============================================================"

# Step 1: Validate the bundled runtime. Existence of python.exe alone is not
# sufficient: a partially deleted runtime can still contain python.exe while
# failing before startup because Lib\encodings or other stdlib files are gone.
$RuntimeValid = $false
if (Test-Path -LiteralPath $Python) {
    Write-Host ""
    Write-Host "[1/3] Validating bundled Python runtime..."
    try {
        $RuntimeValid = Test-LauncherPythonRuntime $Python
    } catch {
        $RuntimeValid = $false
    }
}

if ($RuntimeValid) {
    $Ver = & $Python -I --version 2>&1
    Write-Host "      Runtime OK: $Ver"
} else {
    if (Test-Path -LiteralPath $Python) {
        Write-Warning "Bundled runtime is incomplete or corrupt. Rebuilding Python 3.11.9..."
    } else {
        Write-Host ""
        Write-Host "[1/3] Bundled runtime missing. Downloading Python 3.11.9..."
    }

    & (Join-Path $PSScriptRoot "fetch_runtime.ps1") -Version "3.11.9"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    if (-not (Test-LauncherPythonRuntime $Python)) {
        throw "Runtime repair completed but validation still failed: $Python"
    }
    $Ver = & $Python -I --version 2>&1
    Write-Host "      Repaired runtime: $Ver"
}

# Step 2: Install launcher and app packages.
Write-Host ""
Write-Host "[2/3] Installing launcher and app packages into shared runtime..."
& (Join-Path $PSScriptRoot "prepare_shared_runtime.ps1") -ReleaseDir $Root
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# Final runtime/package validation. Keep the runtime probe isolated, but import
# the launcher source from SourceRoot without -I because isolated mode removes
# the working/source directory from sys.path.
Write-Host ""
Write-Host "      Validating runtime and launcher imports..."
& $Python -I -c "import encodings; from PySide6.QtWidgets import QApplication; import streamlit; print('      Runtime validation: OK')"
if ($LASTEXITCODE -ne 0) {
    throw "Runtime/package validation failed after deployment."
}

Push-Location $SourceRoot
try {
    & $Python -c "import launcher; print('      Launcher module validation: OK')"
    if ($LASTEXITCODE -ne 0) {
        throw "Launcher source package could not be imported from: $SourceRoot"
    }
} finally {
    Pop-Location
}

# Step 3: Create the no-console shortcut.
Write-Host ""
Write-Host "[3/3] Creating no-console launcher shortcut..."
& (Join-Path $PSScriptRoot "create_launcher_shortcut.ps1") -ReleaseDir $Root
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "============================================================"
Write-Host "  DEPLOY / REPAIR COMPLETE"
Write-Host "============================================================"
Write-Host ""
Write-Host "Normal launch:"
Write-Host "  $Root\START_LAUNCHER.lnk"
Write-Host ""
Write-Host "Fallback no-console launch:"
Write-Host "  $Root\START_LAUNCHER.vbs"
Write-Host ""
Write-Host "Debug launch:"
Write-Host "  $Root\START_LAUNCHER_DEBUG.bat"
Write-Host ""
