# Run this from: D:\pythonProject\HRI\Streamlit_Launcher
# Right-click > Run with PowerShell

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# Remove stale lock if present
$LockFile = ".git\index.lock"
if (Test-Path $LockFile) {
    Remove-Item $LockFile -Force
    Write-Host "Removed stale git lock."
}

# Create or switch to branch 'hri'
$CurrentBranch = git rev-parse --abbrev-ref HEAD 2>$null
if ($CurrentBranch -ne "hri") {
    $Exists = git branch --list hri
    if ($Exists) {
        git checkout hri
    } else {
        git checkout -b hri
    }
}

# Stage all changes
git add -A

# Commit
git commit -m "feat: network drive deployment -- shared runtime, instant launch

- create_virtual_environments=false: skip per-user venv creation entirely
- sync_to_local_cache=false: run apps/runtime directly from network drive
- environment_manager: shared_runtime_state() fast path (no pip install)
- main.py: honour sync_to_local_cache flag
- models/config_loader: add sync_to_local_cache field
- scripts/deploy_network.ps1: one-command full deploy
- scripts/prepare_shared_runtime.ps1: install all packages into shared runtime
- START_LAUNCHER.lnk / START_LAUNCHER.vbs: no-console entry points for users
- START_LAUNCHER_DEBUG.bat: visible-console troubleshooting entry point
- tests: add shared-runtime fast-path test, fix full-flow test for venv mode"

# Push
git push origin hri --set-upstream

Write-Host ""
Write-Host "Done! Branch 'hri' pushed to GitHub."
Write-Host "Tomorrow: git pull origin hri, then .\scripts\deploy_network.ps1"
