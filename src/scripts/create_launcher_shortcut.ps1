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
$ReleaseDir = $ReleaseDir.Trim().Trim([char]34)

function ConvertTo-StableNetworkPath {
    param([Parameter(Mandatory=$true)][string]$Path)

    $FullPath = [IO.Path]::GetFullPath($Path)
    $DriveRoot = [IO.Path]::GetPathRoot($FullPath)
    if ($FullPath.StartsWith("\\") -or $DriveRoot -notmatch "^[A-Za-z]:\\$") {
        return $FullPath
    }

    $Drive = Get-PSDrive -Name $DriveRoot.Substring(0, 1) -ErrorAction SilentlyContinue
    if (-not $Drive -or -not $Drive.DisplayRoot -or -not $Drive.DisplayRoot.StartsWith("\\")) {
        return $FullPath
    }

    $RelativePath = $FullPath.Substring($DriveRoot.Length).TrimStart("\")
    if ($RelativePath -eq "") { return $Drive.DisplayRoot.TrimEnd("\") }
    return Join-Path $Drive.DisplayRoot $RelativePath
}

if ($ReleaseDir -eq "") {
    $ReleaseDir = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
}
$Root = ConvertTo-StableNetworkPath (Resolve-Path -LiteralPath $ReleaseDir -ErrorAction Stop).Path
$SourceRoot = Join-Path $Root "src"
if (-not (Test-Path -LiteralPath $SourceRoot)) {
    $SourceRoot = $Root
}
$LauncherExe = Join-Path $Root "launcher.exe"
$LauncherScript = Join-Path $Root "START_LAUNCHER.vbs"
$ShortcutPath = Join-Path $Root "START_LAUNCHER.lnk"
$LegacyBat = Join-Path $Root "START_LAUNCHER.bat"
$DebugBat = Join-Path $Root "START_LAUNCHER_DEBUG.bat"

if (Test-Path -LiteralPath $LegacyBat) {
    if (Test-Path -LiteralPath $DebugBat) {
        Remove-Item -LiteralPath $LegacyBat -Force
        Write-Host "Removed legacy user-facing batch file: $LegacyBat"
    } else {
        Rename-Item -LiteralPath $LegacyBat -NewName "START_LAUNCHER_DEBUG.bat"
        Write-Host "Renamed legacy batch file to: $DebugBat"
    }
}

if (Test-Path -LiteralPath $LauncherExe) {
    $TargetPath = $LauncherExe
    $Arguments = ""
    $WorkingDirectory = $Root
} else {
    if (-not (Test-Path -LiteralPath $LauncherScript)) {
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
$LauncherIcon = Join-Path $SourceRoot "assets\launcher\launcher.ico"
if (Test-Path -LiteralPath $LauncherIcon) {
    $Shortcut.IconLocation = "`"$LauncherIcon`",0"
}
$Shortcut.Save()

Write-Host "Created: $ShortcutPath"

if ($Launch) {
    Start-Process $ShortcutPath
}
