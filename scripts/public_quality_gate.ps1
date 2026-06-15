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
$Python = Join-Path $Root ".venv\Scripts\python.exe"
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
        & $Python -m pytest
    }
}

Invoke-GateStep "compile Python sources" {
    & $Python -m compileall -q launcher build_scripts tests
}

Invoke-GateStep "public metadata" {
    foreach ($Path in @("README.md", "LICENSE", "CONTRIBUTING.md", "SECURITY.md", "requirements-launcher.txt")) {
        if (-not (Test-Path (Join-Path $Root $Path))) {
            throw "Missing public metadata file: $Path"
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
}

if ($FullBuild) {
    Invoke-GateStep "release build" {
        & (Join-Path $PSScriptRoot "build_exe.ps1")
    }
    Invoke-GateStep "release verification" {
        & (Join-Path $PSScriptRoot "verify_release.ps1") -Path (Join-Path $Root "build\Unified-Streamlit-Launcher")
    }
}

Write-Host ""
Write-Host "Public quality gate passed."
