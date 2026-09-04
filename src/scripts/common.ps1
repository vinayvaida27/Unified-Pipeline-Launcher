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
