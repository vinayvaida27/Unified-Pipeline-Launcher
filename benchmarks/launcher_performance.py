"""Small repeatable launcher startup benchmark using only the standard library."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
RUNTIME = SRC / "runtime" / "python.exe"


def _run(script: str, repeats: int) -> list[float]:
    values = []
    for _ in range(repeats):
        started = time.perf_counter()
        subprocess.run([str(RUNTIME), "-c", script], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
        values.append((time.perf_counter() - started) * 1000)
    return values


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=5)
    args = parser.parse_args()
    import_script = "import sys; sys.path.insert(0, r'%s'); import launcher.main" % SRC
    discovery_script = (
        "import sys; from pathlib import Path; sys.path.insert(0, r'%s'); "
        "from launcher.config_loader import load_platform_config; "
        "from launcher.app_discovery import discover_apps; "
        "c=load_platform_config(Path(r'%s')); discover_apps(c.paths.apps_directory)"
        % (SRC, SRC / "config" / "launcher_config.json")
    )
    result = {
        "python": str(RUNTIME),
        "repeats": args.repeats,
        "launcher_import_ms": _run(import_script, args.repeats),
        "config_and_discovery_ms": _run(discovery_script, args.repeats),
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
