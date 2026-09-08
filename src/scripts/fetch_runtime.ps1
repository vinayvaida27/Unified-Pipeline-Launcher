<#
.SYNOPSIS
    Download and validate official relocatable CPython before replacing runtime/.
.DESCRIPTION
    Uses the NuGet python package, preserves the previous runtime for rollback,
    and stops on every failed native validation or bootstrap command.
#>
param(
    [string]$Version = "3.11.9",
    [string]$RuntimeDir = ""
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "common.ps1")
Clear-LauncherPythonEnvironment
if ($Version -notmatch '^\d+\.\d+\.\d+$') { throw "Invalid Python version: $Version" }
if ($RuntimeDir -eq "") { $RuntimeDir = Join-Path (Split-Path -Parent $PSScriptRoot) "runtime" }

Invoke-LauncherRuntimeUpdate -RuntimeDir $RuntimeDir -Build {
    param($Stage)
    $Work = Join-Path $env:TEMP ("usl-runtime-{0}" -f [guid]::NewGuid().ToString('N'))
    $Zip = "$Work.zip"
    try {
        Write-Host "Downloading official CPython $Version from NuGet..."
        [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri "https://www.nuget.org/api/v2/package/python/$Version" -OutFile $Zip -UseBasicParsing
        Expand-Archive -LiteralPath $Zip -DestinationPath $Work -Force
        $ToolsDir = Join-Path $Work "tools"
        if (-not (Test-Path -LiteralPath (Join-Path $ToolsDir "python.exe"))) {
            throw "python.exe not found in package tools/ folder"
        }
        Get-ChildItem -LiteralPath $ToolsDir -Force | ForEach-Object {
            Copy-Item -LiteralPath $_.FullName -Destination $Stage -Recurse -Force
        }
        foreach ($Name in @('README.md', '.gitkeep')) {
            $Preserved = Join-Path $RuntimeDir $Name
            if (Test-Path -LiteralPath $Preserved) { Copy-Item -LiteralPath $Preserved -Destination $Stage -Force }
        }
        $Python = Join-Path $Stage "python.exe"
        Write-Host "Bootstrapping pip in staged runtime..."
        & $Python -I -m ensurepip --upgrade | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "pip bootstrap failed (exit code $LASTEXITCODE)." }
    } finally {
        Remove-Item -LiteralPath $Zip -Force -ErrorAction SilentlyContinue
        if ((Split-Path -Parent ([IO.Path]::GetFullPath($Work))) -eq [IO.Path]::GetFullPath($env:TEMP).TrimEnd('\')) {
            Remove-Item -LiteralPath $Work -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
} -Validate {
    param($Stage)
    $Python = Join-Path $Stage "python.exe"
    Write-Host "Validating staged runtime..."
    Assert-LauncherPythonRuntime $Python
    & $Python -I -c "import ssl, subprocess, venv, pip, sys; print('Validated', sys.version)"
    if ($LASTEXITCODE -ne 0) { throw "Runtime import validation failed (exit code $LASTEXITCODE)." }
    # Disposable venv lives on local TEMP even for mapped/UNC source deployments.
    $TestVenv = Join-Path $env:TEMP ("usl-venv-validation-{0}" -f [guid]::NewGuid().ToString('N'))
    try {
        & $Python -m venv $TestVenv
        if ($LASTEXITCODE -ne 0) { throw "Temporary venv validation failed (exit code $LASTEXITCODE)." }
        $TestVenvPython = Join-Path $TestVenv "Scripts\python.exe"
        if (-not (Test-Path -LiteralPath $TestVenvPython)) { throw "Temporary validation venv does not contain python.exe." }
        & $TestVenvPython -I -c "import encodings, ssl, subprocess, venv, sys; print('Venv validated', sys.version)"
        if ($LASTEXITCODE -ne 0) { throw "Temporary venv import validation failed (exit code $LASTEXITCODE)." }
    } finally {
        if ((Split-Path -Parent ([IO.Path]::GetFullPath($TestVenv))) -eq [IO.Path]::GetFullPath($env:TEMP).TrimEnd('\')) {
            Remove-Item -LiteralPath $TestVenv -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
    $RuntimeInfo = Join-Path $Stage "runtime_info.json"
    & $Python -I -c "import platform, json, pathlib, datetime, sys; pathlib.Path(sys.argv[1]).write_text(json.dumps({'python_version': platform.python_version(), 'architecture': platform.architecture()[0], 'source': 'nuget:python:$Version', 'validated': True, 'validated_at': datetime.datetime.utcnow().isoformat() + 'Z'}, indent=2), encoding='utf-8')" $RuntimeInfo
    if ($LASTEXITCODE -ne 0) { throw "Runtime metadata write failed (exit code $LASTEXITCODE)." }
}
Write-Host "Done. Bundled Python $Version is installed in: $RuntimeDir"
