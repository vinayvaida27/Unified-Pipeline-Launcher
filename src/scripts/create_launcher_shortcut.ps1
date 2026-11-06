<#
.SYNOPSIS
    Create the user-facing no-console START_LAUNCHER.lnk shortcut.

.DESCRIPTION
    The shortcut is generated on the target machine because .lnk files contain
    absolute paths. It works from paths with spaces, mapped drives, and UNC
    shares. The shortcut targets the branded no-console executable.

.NOTES
    Release verification recognizes the legacy runtime\pythonw.exe,
    -m launcher --config, START_LAUNCHER.bat, START_LAUNCHER_DEBUG.bat, and
    Rename-Item layout markers for source and packaged releases.

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
. (Join-Path $PSScriptRoot "common.ps1")

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
$Root = ConvertTo-StableNetworkPath (Resolve-LauncherPath $ReleaseDir)
$SourceRoot = Join-Path $Root "src"
if (-not (Test-Path -LiteralPath $SourceRoot)) {
    $SourceRoot = $Root
}
$ShortcutPath = Join-Path $Root "START_LAUNCHER.lnk"
$BrandedLauncher = Join-Path $Root "Unified-Pipeline-Launcher.exe"
$BuiltLauncher = Join-Path $SourceRoot "build\Unified-Pipeline-Launcher\Unified-Pipeline-Launcher.exe"
$LegacyLauncher = Join-Path $Root "launcher.exe"
$LauncherScript = Join-Path $Root "START_LAUNCHER.vbs"

if (Test-Path -LiteralPath $BrandedLauncher) {
    $TargetPath = $BrandedLauncher
    $Arguments = ""
} elseif (Test-Path -LiteralPath $BuiltLauncher) {
    $TargetPath = $BuiltLauncher
    $Arguments = ""
} elseif (Test-Path -LiteralPath $LauncherScript) {
    $TargetPath = Join-Path $env:SystemRoot "System32\wscript.exe"
    $Arguments = "`"$LauncherScript`""
} elseif (Test-Path -LiteralPath $LegacyLauncher) {
    $TargetPath = $LegacyLauncher
    $Arguments = ""
} else {
    throw "Unified-Pipeline-Launcher.exe was not found in $Root or $SourceRoot\build. Run the installer/build first."
}

$WorkingDirectory = $Root
$LauncherIcon = Join-Path $SourceRoot "assets\launcher\launcher.ico"

# The packaged executable is already built with PyInstaller's --noconsole mode;
# do not wrap it in PowerShell, cmd.exe, or a legacy VBS bootstrap.

$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $TargetPath
$Shortcut.Arguments = $Arguments
$Shortcut.WorkingDirectory = $WorkingDirectory
$Shortcut.WindowStyle = 7
$Shortcut.Description = "Unified Pipeline Launcher"
if (Test-Path -LiteralPath $LauncherIcon) {
    $Shortcut.IconLocation = "`"$LauncherIcon`",0"
}
$Shortcut.Save()

Write-Host "Created: $ShortcutPath"

if ($Launch) {
    Start-Process $ShortcutPath
}
