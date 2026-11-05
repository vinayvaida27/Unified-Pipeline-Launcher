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
if (-not (Test-Path -LiteralPath $Python)) {
    throw "Locked development environment missing. Run scripts\setup_dev.ps1 first."
}

function Invoke-GateStep {
    param(
        [Parameter(Mandatory=$true)][string]$Name,
        [Parameter(Mandatory=$true)][scriptblock]$Body
    )
    Write-Host ""
    Write-Host "==> $Name"
    $global:LASTEXITCODE = 0
    & $Body
    if ($LASTEXITCODE -ne 0) { throw "Quality gate failed: $Name" }
}

if (-not $SkipPytest) {
    Invoke-GateStep "pytest" {
        Push-Location -LiteralPath $Root
        try { & $Python -m pytest } finally { Pop-Location }
    }
}

Invoke-GateStep "compile Python sources" {
    & $Python -m compileall -q (Join-Path $Root "launcher") (Join-Path $Root "build_scripts") (Join-Path $Root "tests")
}

Invoke-GateStep "public metadata" {
    foreach ($Path in @("pyproject.toml", "uv.lock", "requirements-launcher.txt", "scripts\ensure_uv.ps1", "scripts\BUILD_LAUNCHER_EXE.ps1")) {
        if (-not (Test-Path -LiteralPath (Join-Path $Root $Path))) { throw "Missing public metadata file: $Path" }
    }
    foreach ($Path in @("README.md", "src\LICENSE", "update_package.bat", "install.bat", "Unified-Pipeline-Launcher-debug.bat", "diagnose_launcher.bat", "apps\apps.json")) {
        if (-not (Test-Path -LiteralPath (Join-Path $PublicRoot $Path))) { throw "Missing public root file: $Path" }
    }
}

Invoke-GateStep "startup entrypoints" {
    $Install = Get-Content -LiteralPath (Join-Path $PublicRoot "install.bat") -Raw
    $Debug = Get-Content -LiteralPath (Join-Path $PublicRoot "Unified-Pipeline-Launcher-debug.bat") -Raw
    $Build = Get-Content -LiteralPath (Join-Path $Root "scripts\BUILD_LAUNCHER_EXE.ps1") -Raw
    if ($Install -notmatch "BUILD_LAUNCHER_EXE\.ps1") { throw "INSTALL.bat must build the branded executable." }
    if ($Install -notmatch "Unified-Pipeline-Launcher\.exe") { throw "INSTALL.bat must launch the branded executable." }
    if ($Debug -notmatch "BUILD_LAUNCHER_EXE\.ps1") { throw "Repair diagnostics must rebuild the branded executable." }
    if ($Build -notmatch "pythonw\.exe") { throw "The branded executable must use the bundled pythonw.exe." }
    if ($Build -notmatch "Unified-Pipeline-Launcher\.exe") { throw "The build script must produce the branded executable." }
}

Invoke-GateStep "application SVG icons" {
    Push-Location -LiteralPath $Root
    try {
        & $Python (Join-Path $Root "scripts\check_svg_icons.py")
    } finally {
        Pop-Location
    }
}

Invoke-GateStep "dependency workflow" {
    $UpdateScript = Get-Content -LiteralPath (Join-Path $Root "scripts\update_dependencies.ps1") -Raw
    $PrepareScript = Get-Content -LiteralPath (Join-Path $Root "scripts\prepare_shared_runtime.ps1") -Raw
    $CommonScript = Get-Content -LiteralPath (Join-Path $Root "scripts\common.ps1") -Raw
    if ($UpdateScript -notmatch "prepare_shared_runtime\.ps1") { throw "update_dependencies.ps1 must call prepare_shared_runtime.ps1" }
    if ($PrepareScript -notmatch "from PySide6\.QtWidgets import QApplication; import streamlit") { throw "prepare_shared_runtime.ps1 must validate PySide6 and streamlit" }
    if ($PrepareScript -notmatch "--link-mode=copy") { throw "prepare_shared_runtime.ps1 must use uv copy mode for cross-filesystem network installs" }
    if ($PrepareScript -notmatch "missing RECORD") { throw "prepare_shared_runtime.ps1 must detect damaged package metadata" }
    if ($CommonScript -notmatch "Get-LauncherRelativePath") { throw "common.ps1 must provide the Windows PowerShell compatible relative-path helper" }
}

Invoke-GateStep "PowerShell parser and compatibility" {
    foreach ($Script in Get-ChildItem -LiteralPath (Join-Path $Root "scripts") -Filter "*.ps1" -File) {
        $Tokens = $null
        $ParseErrors = $null
        $Ast = [System.Management.Automation.Language.Parser]::ParseFile($Script.FullName, [ref]$Tokens, [ref]$ParseErrors)
        if ($ParseErrors.Count -gt 0) { throw "Invalid PowerShell syntax in $($Script.Name): $ParseErrors" }
        $Unsupported = $Ast.FindAll({ param($Node)
            $Node -is [System.Management.Automation.Language.InvokeMemberExpressionAst] -and
            $Node.Member.Value -eq "GetRelativePath" -and $Node.Expression.Extent.Text -match '^\[(System\.)?IO\.Path\]$'
        }, $true)
        if ($Unsupported.Count -gt 0) { throw "Windows PowerShell 5.1 does not support Path.GetRelativePath: $($Script.Name)" }
    }
}

if ($FullBuild) {
    Invoke-GateStep "branded executable build" { & (Join-Path $PSScriptRoot "BUILD_LAUNCHER_EXE.ps1") }
    Invoke-GateStep "release verification" { & (Join-Path $PSScriptRoot "verify_release.ps1") -Path (Join-Path $Root "build\Unified-Pipeline-Launcher") }
}

Write-Host ""
Write-Host "Public quality gate passed."
