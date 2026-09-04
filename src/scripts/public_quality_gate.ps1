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
if (-not (Test-Path $Python)) { $Python = Join-Path $PublicRoot ".venv\Scripts\python.exe" }
if (-not (Test-Path $Python)) { $Python = "python" }

function Invoke-GateStep {
    param(
        [Parameter(Mandatory=$true)][string]$Name,
        [Parameter(Mandatory=$true)][scriptblock]$Body
    )
    Write-Host ""
    Write-Host "==> $Name"
    & $Body
    if ($LASTEXITCODE -ne 0) { throw "Quality gate failed: $Name" }
}

if (-not $SkipPytest) {
    Invoke-GateStep "pytest" {
        Push-Location $Root
        try { & $Python -m pytest } finally { Pop-Location }
    }
}

Invoke-GateStep "compile Python sources" {
    & $Python -m compileall -q (Join-Path $Root "launcher") (Join-Path $Root "build_scripts") (Join-Path $Root "tests")
}

Invoke-GateStep "public metadata" {
    foreach ($Path in @("pyproject.toml", "uv.lock", "requirements-launcher.txt", "scripts\ensure_uv.ps1", "scripts\create_launcher_shortcut.ps1")) {
        if (-not (Test-Path (Join-Path $Root $Path))) { throw "Missing public metadata file: $Path" }
    }
    foreach ($Path in @("README.md", "LICENSE", "INSTALL.bat", "UPDATE_PACKAGES.bat", "START_LAUNCHER.bat", "START_LAUNCHER.vbs", "START_LAUNCHER_DEBUG.bat", "apps\apps.json")) {
        if (-not (Test-Path (Join-Path $PublicRoot $Path))) { throw "Missing public root file: $Path" }
    }
}

Invoke-GateStep "startup entrypoints" {
    $NormalBat = Get-Content (Join-Path $PublicRoot "START_LAUNCHER.bat") -Raw
    $DebugBat = Get-Content (Join-Path $PublicRoot "START_LAUNCHER_DEBUG.bat") -Raw
    $Vbs = Get-Content (Join-Path $PublicRoot "START_LAUNCHER.vbs") -Raw
    foreach ($Text in @($NormalBat, $DebugBat, $Vbs)) {
        if ($Text -notmatch "-I\s+-m\s+launcher") { throw "Launcher entrypoints must use isolated module startup (-I -m launcher)." }
        if ($Text -notmatch "--no-local-cache") { throw "Launcher entrypoints must explicitly bypass expensive startup caching." }
    }
    if ($DebugBat -notmatch "import encodings") { throw "Debug startup must validate the bundled runtime." }
}

Invoke-GateStep "application SVG icons" {
    Push-Location $Root
    try {
        & $Python -c "from pathlib import Path; from PySide6.QtCore import QByteArray; from PySide6.QtSvg import QSvgRenderer; import sys; root=Path(sys.argv[1]); bad=[]; [bad.append(str(p)) for p in root.rglob('*.svg') if not QSvgRenderer(QByteArray(p.read_bytes())).isValid()]; print('SVG icons checked:', len(list(root.rglob('*.svg')))); print(*bad, sep='\n'); raise SystemExit(1 if bad else 0)" (Join-Path $PublicRoot "apps")
    } finally {
        Pop-Location
    }
}

Invoke-GateStep "dependency workflow" {
    $UpdateScript = Get-Content (Join-Path $Root "scripts\update_dependencies.ps1") -Raw
    $PrepareScript = Get-Content (Join-Path $Root "scripts\prepare_shared_runtime.ps1") -Raw
    if ($UpdateScript -notmatch "prepare_shared_runtime\.ps1") { throw "update_dependencies.ps1 must call prepare_shared_runtime.ps1" }
    if ($PrepareScript -notmatch "from PySide6\.QtWidgets import QApplication; import streamlit") { throw "prepare_shared_runtime.ps1 must validate PySide6 and streamlit" }
    if ($PrepareScript -notmatch "--link-mode=copy") { throw "prepare_shared_runtime.ps1 must use uv copy mode for cross-filesystem network installs" }
    if ($PrepareScript -notmatch "missing RECORD") { throw "prepare_shared_runtime.ps1 must detect damaged package metadata" }
}

if ($FullBuild) {
    Invoke-GateStep "release build" { & (Join-Path $PSScriptRoot "build_exe.ps1") }
    Invoke-GateStep "release verification" { & (Join-Path $PSScriptRoot "verify_release.ps1") -Path (Join-Path $Root "build\Unified-Pipeline-Launcher") }
}

Write-Host ""
Write-Host "Public quality gate passed."
