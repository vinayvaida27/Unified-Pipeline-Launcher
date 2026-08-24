<#
.SYNOPSIS
    Create the user-facing no-console START_LAUNCHER.lnk shortcut.

.DESCRIPTION
    The shortcut is generated on the target machine because .lnk files contain
    absolute paths. It works from paths with spaces, mapped drives, and UNC
    shares. If launcher.exe exists at the public root, the shortcut targets it.
    Otherwise it targets START_LAUNCHER.vbs, which selects a current local
    runtime cache when one is available.

.EXAMPLE
    .\src\scripts\create_launcher_shortcut.ps1

.EXAMPLE
    .\src\scripts\create_launcher_shortcut.ps1 -ReleaseDir "Z:\Unified-Pipeline-Launcher" -Launch
#>

param(
    [string]$ReleaseDir = "",
    [switch]$Launch
)

$ErrorActionPreference = "Stop"

if ($ReleaseDir -eq "") {
    $ReleaseDir = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
}
$Root = (Resolve-Path $ReleaseDir).Path
$SourceRoot = Join-Path $Root "src"
if (-not (Test-Path $SourceRoot)) {
    $SourceRoot = $Root
}
$LauncherExe = Join-Path $Root "launcher.exe"
$LauncherScript = Join-Path $Root "START_LAUNCHER.vbs"
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
    $WorkingDirectory = $Root
} else {
    if (-not (Test-Path $LauncherScript)) {
        throw "Launcher bootstrap not found: $LauncherScript"
    }
    $TargetPath = Join-Path $env:SystemRoot "System32\wscript.exe"
    $Arguments = "`"$LauncherScript`""
    $WorkingDirectory = $Root
}

$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $TargetPath
$Shortcut.Arguments = $Arguments
$Shortcut.WorkingDirectory = $WorkingDirectory
$Shortcut.WindowStyle = 7
$Shortcut.Description = "Unified Pipeline Launcher"
$Shortcut.Save()

Write-Host "Created: $ShortcutPath"

if ($Launch) {
    Start-Process $ShortcutPath
}
