"""Fail-fast regression gate for the lightweight launcher benchmarks."""

from __future__ import annotations

import json
import statistics
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "benchmarks" / "launcher_performance.py"


def main() -> int:
    result = subprocess.run(
        [sys.executable, str(BENCHMARK), "--repeats", "3"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    import_ms = statistics.median(data["launcher_import_ms"])
    discovery_ms = statistics.median(data["config_and_discovery_ms"])
    if import_ms > 1000 or discovery_ms > 500:
        print(f"Performance gate failed: import={import_ms:.1f}ms discovery={discovery_ms:.1f}ms")
        return 1
    print(f"Performance gate passed: import={import_ms:.1f}ms discovery={discovery_ms:.1f}ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
