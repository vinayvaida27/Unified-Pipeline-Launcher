<#
.SYNOPSIS
    Full one-command deploy for Z:\Vinay Vaida\Unified-Streamlit-Launcher.

.DESCRIPTION
    Run this once after git clone, and again after every git pull.

    What it does:
      1. Downloads a portable Python runtime into runtime\  (first time only)
      2. Installs launcher and app packages into that runtime (every pull)
      3. Prints where users should look

    No EXE build needed. No Python install for users. Everything runs from
    the network drive using the bundled runtime.

.EXAMPLE
    cd "Z:\Vinay Vaida\Unified-Streamlit-Launcher"
    .\scripts\deploy_network.ps1
#>

param()
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

Write-Host ""
Write-Host "============================================================"
Write-Host "  Unified Streamlit Launcher -- Network Drive Deploy"
Write-Host "  $Root"
Write-Host "============================================================"

# ── Step 1: Download Python runtime (skip if already present) ───────────────
$Python = Join-Path $Root "runtime\python.exe"
if (Test-Path $Python) {
    $Ver = & $Python --version 2>&1
    Write-Host ""
    Write-Host "[1/2] Runtime already present: $Ver  (skipping download)"
} else {
    Write-Host ""
    Write-Host "[1/2] Downloading portable Python runtime..."
    & (Join-Path $PSScriptRoot "fetch_runtime.ps1")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

# ── Step 2: Install all app packages into the shared runtime ─────────────────
Write-Host ""
Write-Host "[2/2] Installing launcher and app packages into shared runtime..."
& (Join-Path $PSScriptRoot "prepare_shared_runtime.ps1") -ReleaseDir $Root
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# ── Done ─────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "============================================================"
Write-Host "  DEPLOY COMPLETE"
Write-Host "============================================================"
Write-Host ""
Write-Host "Users open the launcher by double-clicking:"
Write-Host "  $Root\START_LAUNCHER.vbs"
Write-Host ""
Write-Host "For debugging with a visible console, run:"
Write-Host "  $Root\START_LAUNCHER.bat"
Write-Host ""
Write-Host "To update after git pull, run this script again."
Write-Host ""
