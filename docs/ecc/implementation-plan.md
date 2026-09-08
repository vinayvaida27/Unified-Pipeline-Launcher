# ECC reliability work

Base: `09652ff1a1426200e67c9e521c75bc24e2877455` (`origin/clean_ui`).
Implementation branch: `ECC`, in a separate worktree. The earlier local VBS
experiment and customized applications remain in the original checkout.

The user authorized implementation of the supplied six-phase ECC plan and later
explicitly authorized committing and pushing the reviewed code to `ECC`. This
remains a separate review branch, not a production-readiness declaration. The installed ECC 2.2.1 planner,
architect, TDD, Python review, security, and verification resources guide the
work; they do not become launcher dependencies. Generic rules are adapted to
Python/Windows; project requirements remain in `AGENTS.md`.

## Prioritized changes

| Priority | Confirmed issue and impact | Smallest fix / regression | Rollback |
|---|---|---|---|
| P1 | BAT/VBS can report success when Python exits with an error; parenthesized paths break parsing | One canonical BAT; quoted path reporting; wait for process exit; native wrapper tests | Restore entrypoint files together |
| P1 | Runtime/cache replacement can delete the usable copy before validation | Stage, validate, lock, retain backup, recover failed promotion; injected failures | Restore retained prior directory with launcher closed |
| P1 | Update/download versions and cached paths can escape approved directories | Component/path validation, private staging, marker verification; traversal/junction tests | Revert affected modules, disable optional updates |
| P1 | A late start failure can stop a replacement process; untrusted ownership markers can authorize cleanup | Match exact state and process identity; race and ownership tests | Revert process manager with all test apps stopped |
| P2 | Qt partially accepts malformed SVGs and emits repeated warnings | Shared warning-aware renderer, fallback, bounded logging; actual Qt fixture | Revert renderer/card together |
| P2 | Explicit cache/download operations block the UI; runtime cache+download can hit an assertion | Existing Qt worker with queued progress; GUI timer responsiveness test | Revert startup helper and use explicit cache opt-out |
| P2 | Portable release omits the canonical BAT and support scripts | Copy/verify required release files; synthetic packaging test | Restore build scripts |
| P2 | CI/tests still expect the older VBS startup and implicit caching; gate scans comments | Replace obsolete expectations with equivalent current behavior tests and AST checks | Restore tests/gate only with matching architecture |

Optional runtime relocation/versioned-archive redesign, scientific package
upgrades, analytical changes, and cosmetic redesign are outside this change.
Network-hosted source deployment and local installed runtime are distinct modes;
the local runtime must never resolve its prefix/stdlib through the network source.

## Verification

Record RED/GREEN for each changed behavior. Run controlled uv/Python tests,
actual Windows PowerShell 5.1, synthetic native entrypoints, Qt, Streamlit/browser
lifecycle, dependency/source scans, and an independent diff review. The corporate
mapped/UNC source and the intended local installed runtime are absent on this
machine; report those acceptance cases as NOT RUN, not as synthetic-test passes.
See `release-report.md` for commands, results, measurements, and manual acceptance.
