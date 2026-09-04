<#
.SYNOPSIS
    Run the fixed quality gate for public-facing changes.

.DESCRIPTION
    This is the repository's lightweight autoresearch acceptance test. Use it
    after each public-readiness or dependency change. A change is kept only
    when this gate passes.
#>

param(
    [switch]$SkipPytest,
    [switch]$FullBuild
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$PublicRoot = Split-Path -Parent $Root
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $Python = Join-Path $PublicRoot ".venv\Scripts\python.exe"
}
if (-not (Test-Path $Python)) {
    $Python = "python"
}

function Invoke-GateStep {
    param(
        [Parameter(Mandatory=$true)][string]$Name,
        [Parameter(Mandatory=$true)][scriptblock]$Body
    )

    Write-Host ""
    Write-Host "==> $Name"
    & $Body
    if ($LASTEXITCODE -ne 0) {
        throw "Quality gate failed: $Name"
    }
}

if (-not $SkipPytest) {
    Invoke-GateStep "pytest" {
        Push-Location $Root
        try {
            & $Python -m pytest
        } finally {
            Pop-Location
        }
    }
}

Invoke-GateStep "compile Python sources" {
    & $Python -m compileall -q (Join-Path $Root "launcher") (Join-Path $Root "build_scripts") (Join-Path $Root "tests")
}

Invoke-GateStep "public metadata" {
    foreach ($Path in @("pyproject.toml", "uv.lock", "requirements-launcher.txt", "scripts\ensure_uv.ps1", "scripts\create_launcher_shortcut.ps1")) {
        if (-not (Test-Path (Join-Path $Root $Path))) {
            throw "Missing public metadata file: $Path"
        }
    }
    foreach ($Path in @("README.md", "LICENSE", "INSTALL.bat", "UPDATE_PACKAGES.bat", "START_LAUNCHER.vbs", "START_LAUNCHER_DEBUG.bat", "apps\apps.json")) {
        if (-not (Test-Path (Join-Path $PublicRoot $Path))) {
            throw "Missing public root file: $Path"
        }
    }
}

Invoke-GateStep "dependency workflow" {
    $UpdateScript = Get-Content (Join-Path $Root "scripts\update_dependencies.ps1") -Raw
    $PrepareScript = Get-Content (Join-Path $Root "scripts\prepare_shared_runtime.ps1") -Raw
    if ($UpdateScript -notmatch "prepare_shared_runtime\.ps1") {
        throw "update_dependencies.ps1 must call prepare_shared_runtime.ps1"
    }
    if ($PrepareScript -notmatch "from PySide6\.QtWidgets import QApplication; import streamlit") {
        throw "prepare_shared_runtime.ps1 must validate PySide6 and streamlit"
    }
    if ($PrepareScript -notmatch "uv.*pip.*install.*--python") {
        throw "prepare_shared_runtime.ps1 must install through uv into the bundled Python"
    }
}

if ($FullBuild) {
    Invoke-GateStep "release build" {
        & (Join-Path $PSScriptRoot "build_exe.ps1")
    }
    Invoke-GateStep "release verification" {
        & (Join-Path $PSScriptRoot "verify_release.ps1") -Path (Join-Path $Root "build\Unified-Pipeline-Launcher")
    }
}

Write-Host ""
Write-Host "Public quality gate passed."
