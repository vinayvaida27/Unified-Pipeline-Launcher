<#
.SYNOPSIS
    Create the user-facing no-console START_LAUNCHER.lnk shortcut.

.DESCRIPTION
    The shortcut is generated on the target machine because .lnk files contain
    absolute paths. It works from paths with spaces, mapped drives, and UNC
    shares. If launcher.exe exists, the shortcut targets it. Otherwise it
    targets runtime\pythonw.exe -m launcher with the local config file.

.EXAMPLE
    .\scripts\create_launcher_shortcut.ps1

.EXAMPLE
    .\scripts\create_launcher_shortcut.ps1 -ReleaseDir "Z:\Vinay Vaida\Unified-Streamlit-Launcher" -Launch
#>

param(
    [string]$ReleaseDir = "",
    [switch]$Launch
)

$ErrorActionPreference = "Stop"

if ($ReleaseDir -eq "") {
    $ReleaseDir = Split-Path -Parent $PSScriptRoot
}
$Root = (Resolve-Path $ReleaseDir).Path
$LauncherExe = Join-Path $Root "launcher.exe"
$PythonW = Join-Path $Root "runtime\pythonw.exe"
$Config = Join-Path $Root "config\launcher_config.json"
$ShortcutPath = Join-Path $Root "START_LAUNCHER.lnk"
$LegacyBat = Join-Path $Root "START_LAUNCHER.bat"
$DebugBat = Join-Path $Root "START_LAUNCHER_DEBUG.bat"

if (Test-Path $LegacyBat) {
    if (Test-Path $DebugBat) {
        Remove-Item -LiteralPath $LegacyBat -Force
        Write-Host "Removed legacy user-facing batch file: $LegacyBat"
    } else {
        Rename-Item -LiteralPath $LegacyBat -NewName "START_LAUNCHER_DEBUG.bat"
        Write-Host "Renamed legacy batch file to: $DebugBat"
    }
}

if (Test-Path $LauncherExe) {
    $TargetPath = $LauncherExe
    $Arguments = ""
} else {
    if (-not (Test-Path $PythonW)) {
        throw "pythonw.exe not found: $PythonW"
    }
    if (-not (Test-Path $Config)) {
        throw "Launcher config not found: $Config"
    }
    $TargetPath = $PythonW
    $Arguments = "-m launcher --config `"$Config`""
}

$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $TargetPath
$Shortcut.Arguments = $Arguments
$Shortcut.WorkingDirectory = $Root
$Shortcut.WindowStyle = 7
$Shortcut.Description = "Unified Streamlit Launcher"
$Shortcut.Save()

Write-Host "Created: $ShortcutPath"

if ($Launch) {
    Start-Process $ShortcutPath
}
