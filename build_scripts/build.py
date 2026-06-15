"""Build the portable Unified Streamlit Launcher release folder."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from create_pyinstaller_spec import generate_spec


class ExeBuilder:
    """Orchestrates tests, PyInstaller, asset copying, and release verification."""

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = (project_root or Path(__file__).resolve().parent.parent).resolve()
        self.build_dir = self.project_root / "build"
        self.release_dir = self.build_dir / "Unified-Streamlit-Launcher"
        self.pyinstaller_dist = self.build_dir / "pyinstaller"
        self.pyinstaller_work = self.build_dir / "pyinstaller-work"

    def run(self, command: list[str]) -> None:
        print("+", " ".join(command))
        subprocess.run(command, cwd=self.project_root, check=True)

    def clean_previous(self) -> None:
        print("Step 1: Cleaning previous build output")
        for path in (self.release_dir, self.pyinstaller_dist, self.pyinstaller_work):
            if path.exists():
                shutil.rmtree(path)

    def run_tests(self) -> None:
        print("Step 2: Running tests")
        self.run([sys.executable, "-m", "pytest"])

    def create_spec(self) -> Path:
        print("Step 3: Generating PyInstaller spec")
        spec_path = generate_spec(self.project_root)
        print(f"Spec: {spec_path}")
        return spec_path

    def run_pyinstaller(self, spec_path: Path) -> None:
        print("Step 4: Building launcher.exe")
        self.run(
            [
                sys.executable,
                "-m",
                "PyInstaller",
                "--clean",
                "--noconfirm",
                "--distpath",
                str(self.pyinstaller_dist),
                "--workpath",
                str(self.pyinstaller_work),
                str(spec_path),
            ]
        )

    def copy_release_files(self) -> None:
        print("Step 5: Copying external apps/config/runtime/docs")
        source_launcher = self.pyinstaller_dist / "launcher"
        if not source_launcher.exists():
            raise FileNotFoundError(f"PyInstaller output was not found: {source_launcher}")
        shutil.copytree(source_launcher, self.release_dir)
        for name in ("apps", "assets", "config", "docs", "runtime"):
            src = self.project_root / name
            dst = self.release_dir / name
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)

        # Simple double-click entry point for users on a network drive.
        (self.release_dir / "START_LAUNCHER.bat").write_text(
            "@echo off\n"
            ":: Double-click this file to open the Unified Streamlit Launcher.\n"
            ":: No Python install needed. Works from a network drive.\n"
            'start "" "%~dp0launcher.exe"\n',
            encoding="utf-8",
        )

        (self.release_dir / "release_info.json").write_text(
            json.dumps(
                {
                    "name": "Unified-Streamlit-Launcher",
                    "built_at": datetime.now(timezone.utc).isoformat(),
                    "apps_external_to_exe": True,
                    "app_registry": "apps/apps.json",
                    "network_drive_setup": (
                        "Set create_virtual_environments=false and "
                        "sync_to_local_cache=false in config/launcher_config.json, "
                        "then run scripts/prepare_shared_runtime.ps1 once."
                    ),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    def generate_checksums(self) -> None:
        print("Step 6: Generating checksums")
        checksum_path = self.release_dir / "checksums.sha256"
        lines: list[str] = []
        for path in sorted(self.release_dir.rglob("*")):
            if not path.is_file() or path == checksum_path:
                continue
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            relative = path.relative_to(self.release_dir).as_posix()
            lines.append(f"{digest} {relative}")
        checksum_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def verify_release(self) -> None:
        print("Step 7: Verifying release structure")
        required = [
            "launcher.exe",
            "config/launcher_config.json",
            "config/platform_manifest.json",
            "apps/apps.json",
            "apps/app_template/app.py",
            "assets",
            "runtime/README.md",
            "docs/quickstart.md",
        ]
        missing = [item for item in required if not (self.release_dir / item).exists()]
        if missing:
            raise RuntimeError(f"Release is missing required files: {missing}")

    def build(self) -> Path:
        print("=" * 72)
        print("Unified Streamlit Launcher EXE Build")
        print("=" * 72)
        self.clean_previous()
        self.run_tests()
        spec_path = self.create_spec()
        self.run_pyinstaller(spec_path)
        self.copy_release_files()
        self.generate_checksums()
        self.verify_release()
        print("=" * 72)
        print(f"Build complete: {self.release_dir}")
        print("Users can run: launcher.exe or START_LAUNCHER.bat")
        print("Network drive: run scripts/prepare_shared_runtime.ps1 once after deploy")
        print("=" * 72)
        return self.release_dir


if __name__ == "__main__":
    ExeBuilder().build()
