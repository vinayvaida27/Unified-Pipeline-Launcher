"""Optional helper for pre-warming app environments before distribution.

The default product creates app environments on first launch in the user's
local cache. This script is intentionally conservative and documents the hook
point for teams that later choose to pre-build wheelhouses or environments.
"""

from __future__ import annotations


def main() -> int:
    print("Pre-bundled app venvs are not enabled by default.")
    print("Recommended production path: ship app wheelhouses, then let launcher create per-user venvs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
