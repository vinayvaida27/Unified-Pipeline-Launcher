"""Streamlit health polling."""

from __future__ import annotations

import time
from pathlib import Path
from subprocess import Popen
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import urlopen

from .constants import HEALTH_PATH
from .exceptions import ApplicationHealthCheckError


class HealthChecker:
    """Polls a Streamlit server until it is healthy.

    The returned URL is always constructed from the port allocated for this
    launch. Streamlit's loopback health endpoint is the readiness signal; the
    optional log path is included only in timeout errors for diagnostics.
    """

    def wait_until_healthy(
        self,
        process: Popen,
        port: int,
        timeout_seconds: int,
        log_path: Path | None = None,
    ) -> str:
        """Wait for the health endpoint on ``port`` and return the root URL.

        Never returns a URL whose port differs from ``port``.
        """
        root_url = f"http://127.0.0.1:{port}"
        health_url = f"{root_url}{HEALTH_PATH}"
        deadline = time.time() + timeout_seconds

        while time.time() < deadline:
            exit_code = process.poll()
            if exit_code is not None:
                raise ApplicationHealthCheckError(
                    f"Streamlit exited before becoming healthy with code {exit_code}"
                )

            if self._url_ok(health_url):
                return root_url

            time.sleep(0.1)

        log_hint = f"; see {log_path}" if log_path else ""
        raise ApplicationHealthCheckError(
            f"Application did not become healthy within {timeout_seconds} seconds{log_hint}"
        )

    @staticmethod
    def _port_from_url(url: str) -> int | None:
        """Extract the integer port from a URL, or None on parse failure."""
        try:
            return urlparse(url).port
        except ValueError:
            return None

    @staticmethod
    def _url_ok(url: str) -> bool:
        try:
            with urlopen(url, timeout=0.2) as response:
                return 200 <= int(response.status) < 300 and response.read(16).strip().lower() == b"ok"
        except (OSError, URLError):
            return False
