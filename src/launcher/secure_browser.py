"""Open local apps in an extension-free browser session."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from urllib.parse import urlparse


def _find_edge() -> Path | None:
    roots = (
        os.environ.get("PROGRAMFILES(X86)"),
        os.environ.get("PROGRAMFILES"),
        os.environ.get("LOCALAPPDATA"),
    )
    candidates = tuple(Path(root) / "Microsoft/Edge/Application/msedge.exe" for root in roots if root)
    return next((path for path in candidates if path.is_file()), None)


def open_isolated_browser(url: str) -> bool:
    """Open a loopback URL in an ephemeral Edge Guest window without extensions."""

    try:
        parsed = urlparse(url)
        if (
            parsed.scheme != "http"
            or parsed.hostname != "127.0.0.1"
            or parsed.port is None
            or parsed.username is not None
            or parsed.password is not None
        ):
            return False
    except ValueError:
        return False
    edge = _find_edge()
    if edge is None:
        return False
    command = [
        str(edge),
        "--guest",
        "--inprivate",
        "--disable-extensions",
        "--no-first-run",
        "--no-default-browser-check",
        f"--app={url}",
    ]
    try:
        subprocess.Popen(
            command,
            shell=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
    except OSError:
        return False
    return True
