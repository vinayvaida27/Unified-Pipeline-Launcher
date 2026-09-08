"""Download a pinned official CPython runtime when no bundled runtime exists.

The launcher never uses a Python already installed on the user's machine.
If the release folder does not contain ``runtime/python.exe``, this module
downloads the exact CPython version pinned in ``launcher_config.json``
(URL + SHA-256), verifies it, and extracts it into the per-user cache.
"""

from __future__ import annotations

import hashlib
import re
import stat
import tempfile
import zipfile
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import urlopen

from .exceptions import RuntimeDownloadError, SecurityValidationError
from .models import PlatformConfig
from .path_utils import atomic_write_json, ensure_within_directory, read_json

CHUNK_SIZE = 1024 * 256


class RuntimeDownloader:
    """Fetches, verifies, and extracts a pinned official CPython build."""

    def __init__(self, config: PlatformConfig) -> None:
        self.config = config
        self.download = config.runtime.download
        self.downloads_dir = config.paths.local_cache_directory / "runtime" / "downloads"

    @property
    def runtime_dir(self) -> Path:
        if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", self.download.version):
            raise RuntimeDownloadError("Runtime download version must have the form major.minor.patch")
        try:
            expected = self.config.paths.local_cache_directory.resolve() / "runtime" / "downloads" / self.download.version
            resolved = ensure_within_directory(expected, self.config.paths.local_cache_directory)
            if resolved != expected:
                raise SecurityValidationError("Downloaded runtime directories cannot be links or junction aliases")
            return resolved
        except SecurityValidationError as exc:
            raise RuntimeDownloadError("Runtime download directory escapes its designated cache location") from exc

    @property
    def marker_path(self) -> Path:
        return self.runtime_dir / ".runtime_download_ready.json"

    def cached_python(self) -> Path | None:
        """Return the previously downloaded runtime when still valid."""

        if not self.marker_path.exists():
            return None
        try:
            marker = read_json(self.marker_path)
        except (OSError, ValueError):
            return None
        if (
            marker.get("sha256") != self.download.sha256
            or marker.get("version") != self.download.version
            or marker.get("url") != self.download.url
        ):
            return None
        try:
            python_path = ensure_within_directory(Path(str(marker.get("python_path", ""))), self.runtime_dir)
        except (OSError, ValueError, SecurityValidationError):
            return None
        return python_path if python_path.name.lower() == "python.exe" and python_path.is_file() else None

    def ensure_runtime(self, progress: Callable[[str], None] | None = None) -> Path:
        """Return a private runtime, downloading it when necessary."""

        if not self.download.enabled:
            raise RuntimeDownloadError("Runtime download is disabled in the launcher configuration")
        if not self.download.url or not self.download.sha256 or not self.download.version:
            raise RuntimeDownloadError("Runtime download configuration is incomplete (url, sha256, and version are required)")
        cached = self.cached_python()
        if cached:
            return cached
        if progress:
            progress(f"Downloading Python {self.download.version}")
        archive_path = self._download_archive(progress)
        try:
            if progress:
                progress("Verifying download")
            self._verify_sha256(archive_path)
            if progress:
                progress("Extracting Python runtime")
            python_path = self._extract(archive_path)
        finally:
            archive_path.unlink(missing_ok=True)
        atomic_write_json(
            self.marker_path,
            {
                "version": self.download.version,
                "url": self.download.url,
                "sha256": self.download.sha256,
                "python_path": str(python_path),
                "downloaded_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        return python_path

    def _download_archive(self, progress: Callable[[str], None] | None) -> Path:
        url = urlsplit(self.download.url)
        if url.scheme != "https" or not url.hostname:
            raise RuntimeDownloadError("Runtime downloads require an HTTPS URL")
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
        archive_path = None
        try:
            with tempfile.NamedTemporaryFile(dir=self.downloads_dir, suffix=".download", delete=False) as handle:
                archive_path = Path(handle.name)
                with urlopen(self.download.url, timeout=60) as response:
                    total = int(response.headers.get("Content-Length") or 0)
                    received = 0
                    while True:
                        chunk = response.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        handle.write(chunk)
                        received += len(chunk)
                        if progress and total:
                            percent = int(received * 100 / total)
                            progress(f"Downloading Python {self.download.version} ({percent}%)")
        except (OSError, URLError) as exc:
            if archive_path is not None:
                archive_path.unlink(missing_ok=True)
            raise RuntimeDownloadError(
                "Could not download the Python runtime. Check the network connection and try again."
            ) from exc
        return archive_path

    def _verify_sha256(self, archive_path: Path) -> None:
        digest = hashlib.sha256()
        with archive_path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
                digest.update(chunk)
        if digest.hexdigest().lower() != self.download.sha256.lower():
            raise RuntimeDownloadError("Downloaded Python runtime failed SHA-256 verification")

    def _extract(self, archive_path: Path) -> Path:
        runtime_dir = self.runtime_dir
        if runtime_dir.exists():
            raise RuntimeDownloadError("Existing downloaded runtime was preserved; use explicit runtime repair")
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=f".{self.download.version}.", dir=self.downloads_dir) as temporary:
            staging_dir = Path(temporary)
            try:
                with zipfile.ZipFile(archive_path) as archive:
                    for member in archive.infolist():
                        path = PureWindowsPath(member.filename)
                        if path.drive or path.root or ".." in path.parts or stat.S_ISLNK(member.external_attr >> 16):
                            raise RuntimeDownloadError("Runtime archive contains unsafe paths")
                        ensure_within_directory(staging_dir / member.filename, staging_dir)
                    archive.extractall(staging_dir)
            except zipfile.BadZipFile as exc:
                raise RuntimeDownloadError("Downloaded Python runtime archive is corrupt") from exc
            except SecurityValidationError as exc:
                raise RuntimeDownloadError("Runtime archive contains unsafe paths") from exc
            python_path = self._find_python(staging_dir)
            if python_path is None:
                raise RuntimeDownloadError("python.exe was not found inside the downloaded runtime archive")
            relative = python_path.relative_to(staging_dir)
            # Renaming into a new version never removes an existing runtime.
            staging_dir.rename(runtime_dir)
        return (runtime_dir / relative).resolve()

    @staticmethod
    def _find_python(extracted_dir: Path) -> Path | None:
        # The official NuGet "python" package ships python.exe under tools/.
        candidates = [extracted_dir / "python.exe", extracted_dir / "tools" / "python.exe"]
        for candidate in candidates:
            if candidate.is_file():
                return candidate
        matches = sorted(extracted_dir.rglob("python.exe"))
        return matches[0] if matches else None
