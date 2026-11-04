"""Safe versioned update framework primitives."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from .exceptions import ChecksumValidationError, UpdateError
from .models import UpdateApplicationEntry, UpdateManifest
from .path_utils import ensure_within_directory, read_json


def compare_semver(left: str, right: str) -> int:
    """Compare two simple semantic versions."""

    def parts(value: str) -> tuple[int, int, int]:
        core = value.split("-", 1)[0].split("+", 1)[0]
        major, minor, patch = core.split(".")
        return int(major), int(minor), int(patch)

    a = parts(left)
    b = parts(right)
    return (a > b) - (a < b)


class UpdateManager:
    """Checks, stages, verifies, and activates versioned releases."""

    def __init__(self, network_release_dir: Path | None, local_base_dir: Path, verify_sha256: bool = True) -> None:
        self.network_release_dir = network_release_dir
        self.local_base_dir = local_base_dir
        self.verify_sha256 = verify_sha256

    def network_available(self) -> bool:
        return bool(self.network_release_dir and self.network_release_dir.exists())

    def load_update_manifest(self, manifest_path: Path) -> UpdateManifest:
        data = read_json(manifest_path)
        apps = [
            UpdateApplicationEntry(
                id=str(item["id"]),
                version=str(item["version"]),
                relative_path=str(item["relative_path"]),
                sha256_manifest=str(item["sha256_manifest"]),
            )
            for item in data.get("applications", [])
        ]
        return UpdateManifest(
            schema_version=int(data["schema_version"]),
            platform_version=str(data["platform_version"]),
            published_at=str(data["published_at"]),
            applications=apps,
        )

    def sha256_file(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def validate_checksum_file(self, root: Path, checksum_file: Path) -> None:
        """Validate a GNU-style checksum file under root."""

        for raw_line in checksum_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            expected, relative = line.split(maxsplit=1)
            target = ensure_within_directory(root / relative.lstrip("* "), root)
            if not target.exists() or self.sha256_file(target) != expected:
                raise ChecksumValidationError(f"Checksum failed for {relative}")

    def stage_release(self, source: Path, version: str) -> Path:
        """Copy a release to staging, replacing incomplete prior staging."""

        if not source.exists():
            raise UpdateError(f"Release source unavailable: {source}")
        staging = self.local_base_dir / "staging" / version
        if staging.exists():
            shutil.rmtree(staging)
        shutil.copytree(source, staging)
        return staging

    def activate_staged_release(self, staging: Path, version: str) -> Path:
        """Atomically move staged files into the versioned local releases area."""

        releases = self.local_base_dir / "releases"
        releases.mkdir(parents=True, exist_ok=True)
        target = releases / version
        if target.exists():
            shutil.rmtree(target)
        staging.replace(target)
        active = self.local_base_dir / "active_version.json"
        active.write_text(json.dumps({"platform_version": version}, indent=2) + "\n", encoding="utf-8")
        return target
