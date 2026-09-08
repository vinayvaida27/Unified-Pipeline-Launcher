---
paths:
  - "**/*.py"
  - "**/*.ps1"
  - "**/*.bat"
  - "**/*.vbs"
---
# Python and Windows verification

Adapted from ECC 2.2.1 `python/testing.md` and `tdd-workflow`.
Follow [AGENTS.md](../../../AGENTS.md) for authoritative runtime/path constraints.

Use pytest through the controlled uv environment. The optional `verification`
dependency group contains pinned test/scanner tools; these are not production
dependencies. Assert behavior, including failures, rather than only source text.

Keep unit, Qt, Windows process/PowerShell, browser, and actual SMB tests distinct.
Qt offscreen tests do not prove a Windows shortcut showed a native window.
Use coverage to find untested critical paths, not as a substitute for assertions.
Document any missed ECC coverage target and the corresponding risk.
