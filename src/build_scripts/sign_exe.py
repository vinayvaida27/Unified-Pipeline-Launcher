"""Optional code-signing hook for launcher.exe."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--signtool", required=True, help="Path to signtool.exe")
    parser.add_argument("--cert-subject", required=True, help="Certificate subject name")
    parser.add_argument("--exe", default="build/Unified-Streamlit-Launcher/launcher.exe")
    args = parser.parse_args()

    exe_path = Path(args.exe)
    if not exe_path.exists():
        raise FileNotFoundError(exe_path)

    subprocess.run(
        [
            args.signtool,
            "sign",
            "/n",
            args.cert_subject,
            "/tr",
            "http://timestamp.digicert.com",
            "/td",
            "sha256",
            "/fd",
            "sha256",
            str(exe_path),
        ],
        check=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
