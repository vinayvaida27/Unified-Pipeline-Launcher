# Performance optimization report

## Scope

This report covers the `optimization/astra-performance` branch based on
`development/codex-launcher-v2`. The branch preserves the working tree's
uncommitted registry entry and does not push or merge changes.

## Execution path

`Unified-Pipeline-Launcher.exe` starts the bundled Python runtime, loads the
platform configuration and app registry, creates the PySide6 window, and keeps
Streamlit launches in worker threads. Each app receives a dynamic port and is
verified on `127.0.0.1` before an isolated browser session opens.

## Measured baseline and current measurements

The repeatable command is:

```powershell
python .\benchmarks\launcher_performance.py --repeats 5
```

Measured on the local repository with the bundled runtime before this branch's
documentation-only additions:

- Warm `launcher.main` import: approximately 183–190 ms per process.
- Configuration plus discovery of 10 apps: approximately 12–15 ms.
- Offscreen `MainWindow` construction: approximately 39 ms.
- Focused non-Qt tests: 67 passed before the Add Application feature; the
  feature's registry/discovery tests pass separately.

The current working tree also contains an intentionally preserved, uncommitted
`outside-app` registry entry. Count-based discovery tests therefore see 11
apps in this checkout; that user change was not altered to make the fixture
pass.

These are local measurements, not network-drive or packaged-EXE results.

## Optimizations retained

- Health-check `urllib`/SSL imports are deferred until an app actually starts,
  reducing work before the first usable UI.
- Readiness logs are parsed only when file size or modification time changes,
  avoiding repeated file reads during polling.
- Existing app discovery uses sets for duplicate IDs and sorted one-pass output.
- Existing UI startup and app launches remain bounded by the configured worker
  limit and startup timeout.
- Icon decoding is cached by path, size, and modification time, so repeated
  fallback or shared icons do not perform repeated disk decode work.
- Filter relayouts now short-circuit when the visible application ID/order set
  is unchanged.

The regression gate is:

```powershell
& .\src\runtime\python.exe .\benchmarks\performance_gate.py
```

It uses median repeated process measurements and fails above 1000 ms for
launcher import or 500 ms for configuration plus discovery.

## Validation

Run focused checks with:

```powershell
$env:PYTHONPATH = "src"
python -m pytest src/tests/test_app_discovery.py src/tests/test_health_checker.py src/tests/test_process_manager.py -q
```

The bundled runtime can smoke-test the Qt window with `QT_QPA_PLATFORM=offscreen`.
System Python on the development machine does not include PySide6, so the full
Qt test suite and a packaged Windows EXE launch were not completed here.

## Remaining limits

Mapped-drive and UNC latency, antivirus impact, SmartScreen behavior, and
domain runtime repair require validation on the target Windows environment.
No new telemetry, automatic package upgrades, or unbounded concurrency were
introduced.

Event-driven SMB notifications, persistent metadata caching, and progressive
first-window rendering were not added: the repository has no repeatable SMB
fixture here, and making those changes would risk showing stale registry data
before the existing validation path completes. They remain candidates for a
target-machine experiment with measured network latency.
