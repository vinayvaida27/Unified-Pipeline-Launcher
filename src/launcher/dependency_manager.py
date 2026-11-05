"""Scan app imports and update only missing bundled-runtime packages."""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from .app_discovery import discover_apps
from .path_utils import atomic_write_json

PACKAGE_ALIASES = {"PIL": "Pillow", "cv2": "opencv-python", "sklearn": "scikit-learn", "yaml": "PyYAML"}
PACKAGE_IMPORTS = {value: key for key, value in PACKAGE_ALIASES.items()}


def scan_python_dependencies(apps_directory: Path) -> list[str]:
    """Return unique third-party package names imported by registered apps."""

    modules: set[str] = set()
    local_modules: set[str] = set()
    stdlib = getattr(sys, "stdlib_module_names", set())
    for app in discover_apps(apps_directory, include_disabled=True):
        # A direct file on a drive root must not turn a whole network/local
        # drive into the scan scope; project folders still scan recursively.
        candidates = [app.entrypoint] if app.app_dir == Path(app.app_dir.anchor or app.app_dir) else app.app_dir.rglob("*.py")
        python_files = [
            path for path in candidates
            if not any(part in {".venv", "venv", "__pycache__", ".pytest_cache"} for part in path.parts)
        ]
        local_modules.update(path.stem for path in python_files)
        local_modules.update(path.parent.name for path in python_files if path.name == "__init__.py")
        if len(python_files) == 1 and python_files[0] == app.entrypoint:
            try:
                local_modules.update(path.stem for path in app.entrypoint.parent.glob("*.py"))
                local_modules.update(
                    path.name for path in app.entrypoint.parent.iterdir()
                    if path.is_dir() and (path / "__init__.py").is_file()
                )
            except OSError:
                pass
        for path in python_files:
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except (OSError, UnicodeError, SyntaxError):
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    modules.update(alias.name.split(".", 1)[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    modules.add(node.module.split(".", 1)[0])
    packages = {
        PACKAGE_ALIASES.get(module, module)
        for module in modules
        if module not in stdlib and module not in {"streamlit"} and module not in local_modules
    }
    return sorted(packages, key=str.casefold)


def _missing_packages(runtime_python: Path, packages: list[str]) -> list[str]:
    if not packages:
        return []
    modules = [PACKAGE_IMPORTS.get(package, package) for package in packages]
    script = (
        "import importlib.util, sys; "
        "print('\\n'.join(module for module in sys.argv[1:] "
        "if importlib.util.find_spec(module) is None))"
    )
    result = subprocess.run(
        [str(runtime_python), "-I", "-c", script, *modules],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    missing_modules = set(result.stdout.splitlines())
    return [package for package, module in zip(packages, modules) if module in missing_modules]


def update_runtime_dependencies(
    apps_directory: Path,
    runtime_python: Path,
    state_directory: Path,
    progress=None,
) -> dict[str, list[str]]:
    """Scan, persist, and install only packages missing from the bundled runtime."""

    packages = scan_python_dependencies(apps_directory)
    state_directory.mkdir(parents=True, exist_ok=True)
    requirements_path = state_directory / "discovered-requirements.txt"
    requirements_path.write_text("\n".join(packages) + ("\n" if packages else ""), encoding="utf-8")
    missing = _missing_packages(runtime_python, packages)
    if progress:
        progress(f"Found {len(packages)} packages; {len(missing)} need installation")
    installed: list[str] = []
    failed: list[str] = []
    failures: list[str] = []
    for package in missing:
        result = subprocess.run(
            [str(runtime_python), "-I", "-m", "pip", "install", "--disable-pip-version-check", package],
            capture_output=True,
            text=True,
            check=False,
            timeout=1800,
        )
        if result is None or result.returncode == 0:
            installed.append(package)
        else:
            failed.append(package)
            detail = (result.stderr or result.stdout or "pip returned a failure").strip().splitlines()[-1]
            failures.append(f"{package}: {detail}")
        if progress:
            progress(f"Packages: {len(installed)} installed, {len(failed)} failed")
    (state_directory / "package-update-errors.log").write_text("\n".join(failures) + ("\n" if failures else ""), encoding="utf-8")
    skipped = [package for package in packages if package not in missing]
    atomic_write_json(
        state_directory / "installed-packages.json",
        {"updated_at": datetime.now(timezone.utc).isoformat(), "packages": packages, "installed": skipped + installed, "failed": failed},
    )
    return {"packages": packages, "missing": missing, "installed": installed, "skipped": skipped, "failed": failed, "errors": failures}
