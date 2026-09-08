"""Windows PowerShell 5.1 integration with synthetic runtimes; no SMB or downloads."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.skipif(
    os.name != "nt", reason="Requires Windows PowerShell 5.1"
)]
SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
POWERSHELL = "powershell.exe"


def _quote(path: Path) -> str:
    return "'" + str(path).replace("'", "''") + "'"


def _run(script: str, folder: Path) -> subprocess.CompletedProcess[str]:
    probe = folder / "probe.ps1"
    probe.write_text("$ErrorActionPreference = 'Stop'\n" + script, encoding="utf-8-sig")
    # The agent host uses PowerShell 7; let Windows PowerShell construct its own
    # module paths instead of attempting to import the host's incompatible DLLs.
    environment = {
        key: value for key, value in os.environ.items() if key.lower() != "psmodulepath"
    }
    return subprocess.run(
        [
            POWERSHELL,
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(probe),
        ],
        cwd=folder,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


@pytest.fixture(scope="module")
def fake_python(tmp_path_factory) -> Path:
    folder = tmp_path_factory.mktemp("synthetic-runtime-program")
    executable = folder / "python.exe"
    source = r"""
using System;
using System.IO;
using System.Reflection;
public class RuntimeProbe {
    public static int Main(string[] args) {
        string exe = Assembly.GetExecutingAssembly().Location;
        string root = Path.GetDirectoryName(exe);
        string command = String.Join(" ", args);
        if (Path.GetFileName(exe) == "synthetic-console.exe") {
            return File.Exists(File.ReadAllText(Path.Combine(root, "console-interpreter"))) ? 0 : 52;
        }
        if (command.Contains("--version")) { Console.WriteLine("Python 3.11.9"); return 0; }
        if (command.Contains("ensurepip") && File.Exists(Path.Combine(root, "fail-ensurepip"))) return 17;
        if (args.Length > 1 && args[0] == "-m" && args[1] == "venv") {
            string scripts = Path.Combine(args[2], "Scripts");
            Directory.CreateDirectory(scripts);
            File.Copy(exe, Path.Combine(scripts, "python.exe"));
        }
        if (args.Length > 1 && args[0] == "pip" && args[1] == "install") {
            int index = Array.IndexOf(args, "--python");
            string interpreter = args[index + 1];
            int prefix = Array.IndexOf(args, "--prefix");
            string runtime = prefix < 0 ? Path.GetDirectoryName(interpreter) : args[prefix + 1];
            File.WriteAllText(Path.Combine(runtime, "installation-started"), "changed");
            string scripts = Path.Combine(runtime, "Scripts");
            Directory.CreateDirectory(scripts);
            File.Copy(exe, Path.Combine(scripts, "synthetic-console.exe"), true);
            File.WriteAllText(Path.Combine(scripts, "console-interpreter"), interpreter);
            if (File.Exists(Path.Combine(root, "fail-install"))) return 19;
        }
        if (args.Length > 0 && args[0] == "sync" && File.Exists(Path.Combine(root, "fail-sync"))) return 23;
        if (args.Length > 0 && args[0] == "venv") {
            File.WriteAllText(Path.Combine(root, "destructive-rebuild-attempt"), command);
            return 20;
        }
        if (command.Contains("import encodings") && File.Exists(Path.Combine(root, "fail-validation"))) return 86;
        return 0;
    }
}
"""
    result = _run(
        "$source = @'\n" + source + "\n'@\n"
        f"Add-Type -TypeDefinition $source -OutputAssembly {_quote(executable)} -OutputType ConsoleApplication\n",
        folder,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return executable


def _release(folder: Path, fake_python: Path) -> Path:
    source = folder / "src"
    scripts = source / "scripts"
    scripts.mkdir(parents=True)
    for name in ("common.ps1", "fetch_runtime.ps1", "prepare_shared_runtime.ps1"):
        shutil.copy2(SCRIPTS / name, scripts / name)
    runtime = source / "runtime"
    runtime.mkdir()
    shutil.copy2(fake_python, runtime / "python.exe")
    (runtime / "previous-usable-runtime").write_text("preserve", encoding="utf-8")
    (source / "requirements-launcher.txt").write_text(
        "synthetic==1\n", encoding="utf-8"
    )
    apps = folder / "apps"
    apps.mkdir()
    (apps / "apps.json").write_text(json.dumps({"applications": []}), encoding="utf-8")
    return runtime


@pytest.mark.parametrize("failure", ["fail-ensurepip", "fail-validation"])
def test_fetch_failure_preserves_previous_runtime(tmp_path, fake_python, failure):
    runtime = _release(tmp_path / "release [test]", fake_python)
    package = tmp_path / "package"
    tools = package / "tools"
    tools.mkdir(parents=True)
    shutil.copy2(fake_python, tools / "python.exe")
    (tools / failure).touch()
    result = _run(
        "function Invoke-WebRequest { param($Uri, $OutFile, [switch]$UseBasicParsing) Set-Content -LiteralPath $OutFile 'archive' }\n"
        "function Expand-Archive { param($LiteralPath, $DestinationPath, [switch]$Force) "
        f"Copy-Item -LiteralPath {_quote(package)} -Destination $DestinationPath -Recurse }}\n"
        f"& {_quote(runtime.parent / 'scripts' / 'fetch_runtime.ps1')} -Version '3.11.9'\n",
        tmp_path,
    )
    assert (runtime / "previous-usable-runtime").read_text(
        encoding="utf-8"
    ) == "preserve", result.stdout + result.stderr
    assert result.returncode != 0, result.stdout + result.stderr


def test_failed_package_install_preserves_runtime(tmp_path, fake_python):
    runtime = _release(tmp_path / "release [test]", fake_python)
    uv = tmp_path / "uv.exe"
    shutil.copy2(fake_python, uv)
    (tmp_path / "fail-install").touch()
    (runtime.parent / "scripts" / "ensure_uv.ps1").write_text(
        f"Write-Output {_quote(uv)}\nexit 0\n", encoding="utf-8-sig"
    )
    result = _run(
        f"& {_quote(runtime.parent / 'scripts' / 'prepare_shared_runtime.ps1')} -ReleaseDir {_quote(runtime.parent.parent)}\n",
        tmp_path,
    )
    assert result.returncode != 0, result.stdout + result.stderr
    assert not (runtime / "installation-started").exists(), (
        result.stdout + result.stderr
    )
    assert (runtime / "previous-usable-runtime").is_file()


def test_prepared_console_script_uses_final_interpreter(tmp_path, fake_python):
    runtime = _release(tmp_path / "release [test]", fake_python)
    uv = tmp_path / "uv.exe"
    shutil.copy2(fake_python, uv)
    (runtime.parent / "scripts" / "ensure_uv.ps1").write_text(
        f"Write-Output {_quote(uv)}\nexit 0\n", encoding="utf-8-sig"
    )
    result = _run(
        f"& {_quote(runtime.parent / 'scripts' / 'prepare_shared_runtime.ps1')} -ReleaseDir {_quote(runtime.parent.parent)}\n",
        tmp_path,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    console = subprocess.run(
        [str(runtime / "Scripts" / "synthetic-console.exe")], check=False, timeout=10
    )
    assert console.returncode == 0, (
        "Generated console script refers to a staging interpreter that no longer exists"
    )


@pytest.mark.parametrize(
    "scenario",
    [
        "success",
        "build-failure",
        "validation-failure",
        "activation-validation-failure",
        "concurrent",
        "locked-file",
    ],
)
def test_runtime_replacement_is_recoverable(tmp_path, scenario):
    runtime = tmp_path / "local installed [runtime] (test)"
    runtime.mkdir()
    (runtime / "previous").write_text("usable", encoding="utf-8")
    build = "param($Stage) Set-Content -LiteralPath (Join-Path $Stage 'replacement') 'ready'"
    validation = "param($Stage) if (-not (Test-Path -LiteralPath (Join-Path $Stage 'replacement'))) { throw 'missing replacement' }"
    before, after = "", ""
    if scenario == "build-failure":
        build += "; throw 'interrupted copy'"
    elif scenario == "validation-failure":
        validation += "; throw 'invalid runtime'"
    elif scenario == "activation-validation-failure":
        validation += "; if ($Stage -notlike '*.staging-*') { throw 'final path validation failed' }"
    elif scenario == "concurrent":
        before = f"$Lock = [IO.File]::Open({_quote(Path(str(runtime) + '.update.lock'))}, 'OpenOrCreate', 'ReadWrite', 'None')\n"
        after = "$Lock.Dispose()\n"
    elif scenario == "locked-file":
        before = f"$Lock = [IO.File]::Open({_quote(runtime / 'previous')}, 'Open', 'ReadWrite', 'None')\n"
        after = "$Lock.Dispose()\n"
    result = _run(
        f". {_quote(SCRIPTS / 'common.ps1')}\n{before}"
        "try {\n"
        f"Invoke-LauncherRuntimeUpdate -RuntimeDir {_quote(runtime)} -Build {{ {build} }} -Validate {{ {validation} }}\n"
        f"}} finally {{ {after} }}\n",
        tmp_path,
    )
    if scenario == "success":
        assert result.returncode == 0, result.stdout + result.stderr
        assert (runtime / "replacement").is_file()
        backups = [
            path
            for path in tmp_path.iterdir()
            if path.name.startswith(runtime.name + ".previous-")
        ]
        assert len(backups) == 1
        assert (backups[0] / "previous").read_text(encoding="utf-8") == "usable"
    else:
        assert result.returncode != 0, result.stdout + result.stderr
        assert (runtime / "previous").read_text(encoding="utf-8") == "usable"
        assert not (runtime / "replacement").exists()
        if scenario == "concurrent":
            assert "already" in result.stderr.lower(), result.stderr
        elif scenario == "build-failure":
            assert "interrupted copy" in result.stderr, result.stderr
        elif scenario == "validation-failure":
            assert "invalid runtime" in result.stderr, result.stderr
        elif scenario == "activation-validation-failure":
            assert "final path validation failed" in result.stderr, result.stderr
        elif scenario == "locked-file":
            assert 'Exception calling "Move"' in result.stderr, result.stderr


@pytest.mark.parametrize("download_fails", [False, True])
def test_missing_record_repairs_selected_runtime_in_staging(
    tmp_path, fake_python, download_fails
):
    script_runtime = _release(tmp_path / "script release", fake_python)
    selected_runtime = _release(tmp_path / "selected release [test]", fake_python)
    broken = selected_runtime / "Lib" / "site-packages" / "synthetic-1.dist-info"
    broken.mkdir(parents=True)
    package = tmp_path / "package"
    package_tools = package / "tools"
    package_tools.mkdir(parents=True)
    shutil.copy2(fake_python, package_tools / "python.exe")
    if download_fails:
        (package_tools / "fail-ensurepip").touch()
    uv = tmp_path / "uv.exe"
    shutil.copy2(fake_python, uv)
    (script_runtime.parent / "scripts" / "ensure_uv.ps1").write_text(
        f"Write-Output {_quote(uv)}\nexit 0\n", encoding="utf-8-sig"
    )
    result = _run(
        "function Invoke-WebRequest { param($Uri, $OutFile, [switch]$UseBasicParsing) Set-Content -LiteralPath $OutFile 'archive' }\n"
        "function Expand-Archive { param($LiteralPath, $DestinationPath, [switch]$Force) "
        f"Copy-Item -LiteralPath {_quote(package)} -Destination $DestinationPath -Recurse }}\n"
        f"& {_quote(script_runtime.parent / 'scripts' / 'prepare_shared_runtime.ps1')} -ReleaseDir {_quote(selected_runtime.parent.parent)}\n",
        tmp_path,
    )
    assert (script_runtime / "previous-usable-runtime").is_file()
    assert not (script_runtime / "installation-started").exists()
    if download_fails:
        assert result.returncode != 0
        assert "pip bootstrap failed" in result.stderr, result.stdout + result.stderr
        assert (selected_runtime / "previous-usable-runtime").is_file()
    else:
        assert result.returncode == 0, result.stdout + result.stderr
        assert (selected_runtime / "installation-started").is_file()
        assert (selected_runtime / ".shared_runtime_ready.json").is_file()
        assert not broken.exists()
        assert not (selected_runtime / "previous-usable-runtime").exists()
        backups = [
            path
            for path in selected_runtime.parent.iterdir()
            if path.name.startswith("runtime.previous-")
        ]
        assert len(backups) == 1
        assert (backups[0] / "previous-usable-runtime").is_file()


def test_failed_dev_sync_does_not_clear_existing_environment(tmp_path, fake_python):
    runtime = _release(tmp_path / "release [test]", fake_python)
    source = runtime.parent
    scripts = source / "scripts"
    shutil.copy2(
        SCRIPTS / "update_all_environments.ps1", scripts / "update_all_environments.ps1"
    )
    config = source / "config"
    config.mkdir()
    (config / "launcher_config.json").write_text(
        json.dumps({"paths": {"local_cache_directory": str(tmp_path / "cache")}}),
        encoding="utf-8",
    )
    development = source / ".venv" / "Scripts"
    development.mkdir(parents=True)
    shutil.copy2(fake_python, development / "python.exe")
    uv = tmp_path / "uv.exe"
    shutil.copy2(fake_python, uv)
    (tmp_path / "fail-sync").touch()
    (scripts / "ensure_uv.ps1").write_text(
        f"Write-Output {_quote(uv)}\nexit 0\n", encoding="utf-8-sig"
    )
    (scripts / "prepare_shared_runtime.ps1").write_text(
        "exit 0\n", encoding="utf-8-sig"
    )
    result = _run(
        f"& {_quote(scripts / 'update_all_environments.ps1')} -ReleaseDir {_quote(source.parent)}\nexit $LASTEXITCODE\n",
        tmp_path,
    )
    assert result.returncode != 0, result.stdout + result.stderr
    assert not (tmp_path / "destructive-rebuild-attempt").exists(), (
        result.stdout + result.stderr
    )
    assert "sync exited 23" in result.stdout, result.stdout + result.stderr


def test_deploy_validates_launcher_from_literal_source_directory(tmp_path, fake_python):
    runtime = _release(tmp_path / "release [test] (synthetic)", fake_python)
    scripts = runtime.parent / "scripts"
    shutil.copy2(SCRIPTS / "deploy_network.ps1", scripts / "deploy_network.ps1")
    (scripts / "prepare_shared_runtime.ps1").write_text(
        "exit 0\n", encoding="utf-8-sig"
    )
    (scripts / "create_launcher_shortcut.ps1").write_text(
        "exit 0\n", encoding="utf-8-sig"
    )
    result = _run(f"& {_quote(scripts / 'deploy_network.ps1')}\n", tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "DEPLOY / REPAIR COMPLETE" in result.stdout
