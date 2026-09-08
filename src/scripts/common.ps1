function Normalize-LauncherPathInput {
    param([Parameter(Mandatory=$true)][string]$Path)

    $Clean = $Path.Trim().Trim([char]34).Trim()
    if ($Clean -eq "" -or $Clean.IndexOf([char]34) -ge 0) {
        throw "Invalid path: $Path"
    }
    return $Clean
}

function Resolve-LauncherPath {
    param([Parameter(Mandatory=$true)][string]$Path)

    return (Resolve-Path -LiteralPath (Normalize-LauncherPathInput $Path) -ErrorAction Stop).Path
}

function Get-LauncherRelativePath {
    param(
        [Parameter(Mandatory=$true)][string]$BasePath,
        [Parameter(Mandatory=$true)][string]$Path
    )

    # Windows PowerShell 5.1 runs on .NET Framework, where
    # [IO.Path]::GetRelativePath() does not exist.  Keep this helper compatible
    # with both Windows PowerShell and PowerShell 7.
    $Base = [IO.Path]::GetFullPath((Normalize-LauncherPathInput $BasePath))
    $Target = [IO.Path]::GetFullPath((Normalize-LauncherPathInput $Path))
    $Separators = [char[]]@([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar)
    $Base = $Base.TrimEnd($Separators)

    if ($Target.Equals($Base, [StringComparison]::OrdinalIgnoreCase)) {
        return "."
    }

    $Prefix = $Base + [IO.Path]::DirectorySeparatorChar
    if (-not $Target.StartsWith($Prefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Path is outside base directory. Base: $Base ; Path: $Target"
    }

    return $Target.Substring($Prefix.Length)
}

function Clear-LauncherPythonEnvironment {
    foreach ($Name in @("PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP", "PYTHONUSERBASE")) {
        Remove-Item -LiteralPath "Env:$Name" -ErrorAction SilentlyContinue
    }
    $env:PYTHONNOUSERSITE = "1"
}

function Test-LauncherPythonRuntime {
    param([Parameter(Mandatory=$true)][string]$Python)

    $Probe = "import encodings, os, sys; root=os.path.normcase(os.path.realpath(os.path.dirname(sys.executable))); paths=(sys.prefix, sys.base_prefix, encodings.__file__); raise SystemExit(0 if all(os.path.commonpath((root, os.path.normcase(os.path.realpath(path)))) == root for path in paths) else 86)"
    & $Python -I -c $Probe
    return $LASTEXITCODE -eq 0
}

function Assert-LauncherPythonRuntime {
    param([Parameter(Mandatory=$true)][string]$Python)

    if (-not (Test-LauncherPythonRuntime $Python)) {
        throw "Python runtime is incomplete or resolves libraries outside its own directory: $Python"
    }
}

function Invoke-LauncherRuntimeUpdate {
    param(
        [Parameter(Mandatory=$true)][string]$RuntimeDir,
        [Parameter(Mandatory=$true)][scriptblock]$Build,
        [Parameter(Mandatory=$true)][scriptblock]$Validate
    )

    $Target = [IO.Path]::GetFullPath((Normalize-LauncherPathInput $RuntimeDir)).TrimEnd('\')
    $Parent = Split-Path -Parent $Target
    if (-not $Parent -or -not (Test-Path -LiteralPath $Parent -PathType Container)) {
        throw "Runtime parent folder must already exist: $Parent"
    }
    if ((Test-Path -LiteralPath $Target) -and
        ((Get-Item -LiteralPath $Target -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw "Runtime updates cannot replace a junction or symbolic link: $Target"
    }
    # Keep all generated paths beside the actual target, including on SMB. The
    # open handle serializes cooperating updaters and is released on process exit.
    $LockPath = "$Target.update.lock"
    try {
        $UpdateLock = [IO.File]::Open($LockPath, 'OpenOrCreate', 'ReadWrite', 'None')
    } catch {
        throw "Runtime update is already running or the folder is not writable: $Target. $($_.Exception.Message)"
    }
    $Suffix = [guid]::NewGuid().ToString('N')
    $Stage = "$Target.staging-$Suffix"
    $Backup = "$Target.previous-$Suffix"
    foreach ($GeneratedPath in @($Stage, $Backup)) {
        if ((Split-Path -Parent ([IO.Path]::GetFullPath($GeneratedPath))) -ne $Parent) {
            $UpdateLock.Dispose()
            throw "Unsafe runtime update path: $GeneratedPath"
        }
    }
    try {
        [IO.Directory]::CreateDirectory($Stage) | Out-Null
        & $Build $Stage
        & $Validate $Stage
        # These are two directory moves, not an atomic transaction. Preserve the
        # backup on success and restore it if activation fails (e.g. file locks).
        if (Test-Path -LiteralPath $Target) {
            [IO.Directory]::Move($Target, $Backup)
        }
        try {
            [IO.Directory]::Move($Stage, $Target)
            & $Validate $Target
        } catch {
            try {
                if ((Test-Path -LiteralPath $Target) -and -not (Test-Path -LiteralPath $Stage)) {
                    [IO.Directory]::Move($Target, $Stage)
                }
                if ((Test-Path -LiteralPath $Backup) -and -not (Test-Path -LiteralPath $Target)) {
                    [IO.Directory]::Move($Backup, $Target)
                }
            } catch {
                throw "Runtime activation and rollback failed. Restore '$Backup' to '$Target'. $($_.Exception.Message)"
            }
            throw
        }
        if (Test-Path -LiteralPath $Backup) {
            Write-Host "Previous runtime retained for rollback: $Backup"
        }
    } finally {
        # Only the generated, confined staging path is disposable. Never delete
        # the target or backup when installation, validation, or promotion fails.
        if (Test-Path -LiteralPath $Stage) {
            Remove-Item -LiteralPath $Stage -Recurse -Force -ErrorAction SilentlyContinue
        }
        $UpdateLock.Dispose()
        # Leave the empty lock file in place: deleting it races another opener.
    }
}
