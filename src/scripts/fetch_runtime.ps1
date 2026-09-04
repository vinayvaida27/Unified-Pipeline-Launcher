<#
.SYNOPSIS
    Download an official, relocatable CPython and install it into runtime/.

.DESCRIPTION
    Fetches the official NuGet "python" package (a full, relocatable CPython
    layout that includes pip and venv -- unlike the embeddable ZIP) and copies
    its contents into the launcher's src/runtime/ folder, then validates it.

    This is the recommended way to bundle Python so end users never install it.

.EXAMPLE
    .\src\scripts\fetch_runtime.ps1
    .\src\scripts\fetch_runtime.ps1 -Version 3.12.7
#>
param(
    [string]$Version = "3.11.9"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$RuntimeDir = Join-Path $Root "runtime"
$Work = Join-Path $env:TEMP "usl-runtime-$Version"
# A .nupkg is a ZIP; Expand-Archive only accepts a .zip extension, so use .zip.
$Zip = Join-Path $env:TEMP "usl-runtime-$Version.zip"
$Url = "https://www.nuget.org/api/v2/package/python/$Version"

Write-Host "Downloading official CPython $Version from NuGet..."
Invoke-WebRequest -Uri $Url -OutFile $Zip -UseBasicParsing

if (Test-Path -LiteralPath $Work) { Remove-Item -LiteralPath $Work -Recurse -Force }
Write-Host "Extracting..."
Expand-Archive -LiteralPath $Zip -DestinationPath $Work -Force

$ToolsDir = Join-Path $Work "tools"
$SrcPython = Join-Path $ToolsDir "python.exe"
if (!(Test-Path -LiteralPath $SrcPython)) { throw "python.exe not found in package tools/ folder" }

# Clear runtime/ (keep README and .gitkeep) and copy the relocatable runtime in.
Get-ChildItem -LiteralPath $RuntimeDir -Force |
    Where-Object { $_.Name -notin @("README.md", ".gitkeep") } |
    Remove-Item -Recurse -Force
Copy-Item -Recurse -Force (Join-Path $ToolsDir "*") $RuntimeDir

$Python = Join-Path $RuntimeDir "python.exe"
if (!(Test-Path -LiteralPath $Python)) { throw "Copied runtime does not contain python.exe" }

# Ensure pip is present (NuGet layout ships ensurepip).
Write-Host "Bootstrapping pip..."
& $Python -m ensurepip --upgrade | Out-Null

# Validate: venv + pip + ssl + subprocess must all import and work.
Write-Host "Validating runtime..."
& $Python -c "import ssl, subprocess, venv, pip, sys; print('Validated', sys.version)"
$TestVenv = Join-Path $RuntimeDir "_venv_validation"
& $Python -m venv $TestVenv
Remove-Item -LiteralPath $TestVenv -Recurse -Force

# Record runtime info.
$RuntimeInfo = Join-Path $RuntimeDir "runtime_info.json"
& $Python -c "import platform, json, pathlib, datetime; pathlib.Path(r'$RuntimeInfo').write_text(json.dumps({'python_version': platform.python_version(), 'architecture': platform.architecture()[0], 'source': 'nuget:python:$Version', 'validated': True, 'validated_at': datetime.datetime.utcnow().isoformat() + 'Z'}, indent=2), encoding='utf-8')"

Remove-Item -LiteralPath $Zip -Force
Remove-Item -LiteralPath $Work -Recurse -Force
Write-Host ""
Write-Host "Done. Bundled Python $Version is installed in: $RuntimeDir"
Write-Host "Next: .\src\scripts\build_exe.ps1"
