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
    foreach ($Path in @("pyproject.toml", "uv.lock", "requirements-launcher.txt", "scripts\ensure_uv.ps1", "scripts\create_launcher_shortcut.ps1")) {
        if (-not (Test-Path -LiteralPath (Join-Path $Root $Path))) { throw "Missing public metadata file: $Path" }
    }
    foreach ($Path in @("README.md", "LICENSE", "UPDATE_PACKAGES.bat", "START_LAUNCHER.bat", "START_LAUNCHER.vbs", "START_LAUNCHER_DEBUG.bat", "apps\apps.json")) {
        if (-not (Test-Path -LiteralPath (Join-Path $PublicRoot $Path))) { throw "Missing public root file: $Path" }
    }
}

Invoke-GateStep "startup entrypoints" {
    $NormalBat = Get-Content -LiteralPath (Join-Path $PublicRoot "START_LAUNCHER.bat") -Raw
    $DebugBat = Get-Content -LiteralPath (Join-Path $PublicRoot "START_LAUNCHER_DEBUG.bat") -Raw
    $Vbs = Get-Content -LiteralPath (Join-Path $PublicRoot "START_LAUNCHER.vbs") -Raw
    $ShortcutScript = Get-Content -LiteralPath (Join-Path $Root "scripts\create_launcher_shortcut.ps1") -Raw

    foreach ($Text in @($NormalBat)) {
        if ($Text -notmatch "-m\s+launcher") { throw "Batch launcher entrypoints must start the launcher package with -m launcher." }
        if ($Text -match "-I\s+-m\s+launcher") { throw "Launcher module startup must not use -I because launcher lives in the source directory." }
        if ($Text -notmatch "--no-local-cache") { throw "Batch launcher entrypoints must explicitly bypass expensive startup caching." }
        if ($Text -notmatch "import launcher") { throw "Batch launcher entrypoints must validate that the source package is importable." }
    }

    if ($NormalBat -notmatch "--silent") { throw "START_LAUNCHER.bat must support silent wrapper execution." }
    if ($NormalBat -notmatch '/wait') { throw "Canonical startup must propagate the launcher process exit status." }
    if ($DebugBat -notmatch 'START_LAUNCHER\.bat.*--debug') { throw "Debug startup must delegate to the canonical batch." }
    if ($Vbs -notmatch "START_LAUNCHER\.bat") { throw "START_LAUNCHER.vbs must delegate to START_LAUNCHER.bat so startup logic has one source of truth." }
    if ($Vbs -notmatch "--silent") { throw "START_LAUNCHER.vbs must invoke the batch launcher in silent mode." }
    if ($ShortcutScript -notmatch "START_LAUNCHER\.vbs") { throw "The generated shortcut must target START_LAUNCHER.vbs." }
    if ($NormalBat -notmatch "import encodings") { throw "Canonical startup must validate the bundled runtime." }
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
    Invoke-GateStep "release build" { & (Join-Path $PSScriptRoot "build_exe.ps1") }
    Invoke-GateStep "release verification" { & (Join-Path $PSScriptRoot "verify_release.ps1") -Path (Join-Path $Root "build\Unified-Pipeline-Launcher") }
}

Write-Host ""
Write-Host "Public quality gate passed."
