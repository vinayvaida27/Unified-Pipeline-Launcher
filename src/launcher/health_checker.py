"""Streamlit health polling."""

from __future__ import annotations

import re
import time
from pathlib import Path
from subprocess import Popen
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import urlopen

from .constants import HEALTH_PATH
from .exceptions import ApplicationHealthCheckError
from .path_utils import read_text_tail


class HealthChecker:
    """Polls a Streamlit server until it is healthy.

    The returned URL is *always* constructed from the ``port`` argument that was
    allocated for this specific launch.  Log parsing is used only as a fast-path
    signal that the server is up, and only accepted when the port found in the
    log exactly matches the expected ``port``.  A URL from a previous launch
    (different port) is silently ignored.
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

            # A successful response on a recently released port may belong to
            # another process. When launch logs are available, require both the
            # expected-port readiness marker and Streamlit's health endpoint.
            if log_path:
                log_url = self.streamlit_ready_url_from_log(log_path, expected_port=port)
                if log_url and self._url_ok(health_url):
                    return root_url
            elif self._url_ok(health_url):
                return root_url

            time.sleep(0.1)

        raise ApplicationHealthCheckError(
            f"Application did not become healthy within {timeout_seconds} seconds"
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

    @staticmethod
    def streamlit_ready_url_from_log(log_path: Path, expected_port: int | None = None) -> str | None:
        """Return the latest ready localhost URL for the expected port, or None."""
        try:
            text = read_text_tail(log_path, 8000)
        except OSError:
            return None
        if "You can now view your Streamlit app in your browser." not in text:
            return None
        ready_urls = re.findall(r"https?://127\.0\.0\.1:\d+", text)
        if expected_port is not None:
            ready_urls = [url for url in ready_urls if HealthChecker._port_from_url(url) == expected_port]
        return ready_urls[-1] if ready_urls else None
