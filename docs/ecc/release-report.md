# ECC reliability release report

Status: integration draft for the separate `ECC` review branch. Local evidence
does not establish production readiness. Actual corporate SMB and the intended
local installed-runtime acceptance remain **NOT RUN**.

## Source and authorization

- Starting commit: `09652ff1a1426200e67c9e521c75bc24e2877455`, from `origin/clean_ui`.
- Implementation branch: `ECC`, in the separate `Streamlit_Launcher_ECC` worktree.
- The original checkout, local VBS experiment, and customized/untracked apps were
  preserved. No laboratory or patient inputs were used in verification.
- The user authorized the supplied ECC plan and subsequently authorized pushing
  the reviewed code to GitHub on `ECC`. This is not approval to update a live
  deployment or to merge into `clean_ui`.
- The exact source/documentation publication list and per-file reasons are in
  [changed-files.md](changed-files.md). Generated evidence and runtime binaries
  are ignored. The published Git commit identifies the reviewed final diff;
  compare it with the starting commit above, rather than the original dirty checkout.

Project requirements remain in [AGENTS.md](../../AGENTS.md). The initial audit and
priorities are in [implementation-plan.md](implementation-plan.md). The separate
[security review](security-review.md) records scanner commands, applicability,
coding-agent configuration review, and remediation proposals.

## Implemented runtime and update changes

| Files | Behavior and reason |
|---|---|
| `src/scripts/common.ps1` | An exclusive lock protects the actual runtime target. A confined sibling candidate is built and validated, the original is retained, and final-path validation runs after activation. Failed activation attempts restore the original directory. |
| `src/scripts/fetch_runtime.ps1` | Downloads into unique temporary paths, checks native bootstrap/validation exit codes, supports an explicit destination, and validates before replacing a runtime. |
| `src/scripts/prepare_shared_runtime.ps1` | Installs into staging. Missing `RECORD` rebuilds the selected release's Python base at the existing Python version, then installs its full enabled requirements. uv uses the final interpreter with a candidate prefix so generated Windows console scripts survive activation. |
| `src/scripts/update_all_environments.ps1` | Failed development sync no longer clears the existing environment. Shared, app, and development maintenance installation requests copy mode. |
| `src/scripts/deploy_network.ps1` | Uses a literal source directory for launcher-import validation, including names containing brackets. |
| `src/tests/test_powershell_runtime_updates.py` | Exercises failed download/bootstrap/install, native exit status, missing metadata, concurrent writers, locked files, failed final validation, retained backups, selected-release isolation, console entrypoints, and literal paths under Windows PowerShell. |

The complete [reviewed manifest](changed-files.md) also covers these fixes:

- BAT owns source and frozen startup; VBS/debug/shortcut delegate to it. Paths
  are derived from the entrypoint, inherited Python options are ignored, and
  wrapper failures preserve exit status and actionable error messages.
- Runtime executable, prefix, base prefix and `encodings` are checked using
  canonical paths. Downloads and cache candidates receive validation too.
- Explicit startup copy/download/validation uses the existing Qt worker pool
  with queued progress, preserving GUI-thread widget access and error types.
- Cache/download/release staging rejects traversal and junction aliases,
  preserves previous versions, and handles failed promotion and concurrent writers.
- Process lifecycle updates match the exact process state, protecting replacement
  processes and rejecting cleanup without a valid ownership identity.
- Registry discovery keeps apps with missing icon files visible. Missing, invalid
  XML and partly accepted malformed SVGs reach a letter fallback with bounded logs.
  Missing metadata and escaped paths are still rejected; release asset validation
  still reports missing/bad registered SVG files.
- Portable packaging includes the canonical BAT and support scripts. Checksum
  generation and quality gates use PowerShell 5.1-compatible literal paths.
- Optional verification dependencies and project-local ECC common/Python guidance
  stay outside the production runtime. CI separates local tests and browser
  checks and makes no claim to corporate SMB or visible desktop acceptance.

uv's documented `--prefix` behavior generates scripts referencing the selected
installing interpreter. Selecting the final runtime while writing into the
candidate was verified with a disposable offline wheel and a real Streamlit
installation. [uv prefix documentation](https://docs.astral.sh/uv/reference/settings/#prefix).

## Executed runtime verification

Platform: Windows 11; actual Windows PowerShell **5.1.26100.9278**; controlled
development Python **3.11.15**; pinned uv **0.11.14**. The standalone runtime
downloaded for acceptance was official NuGet CPython **3.11.9**.

From the ECC repository root, these focused commands were executed:

```powershell
& .\src\.venv\Scripts\python.exe -m pytest src/tests/test_powershell_runtime_updates.py -q
& .\src\.venv\Scripts\python.exe -m ruff check src/tests/test_powershell_runtime_updates.py
& .\src\.venv\Scripts\python.exe -m ruff format --check src/tests/test_powershell_runtime_updates.py
powershell.exe -NoProfile -NonInteractive -Command '$PSVersionTable.PSVersion.ToString()'
```

| Check | Observed result |
|---|---|
| Initial runtime regression run | Exit 1: **5 failed, 3 passed**. It reproduced deletion of the previous runtime and partial package installation left in the original runtime. |
| Failed development sync reproducer | Exit 1: **1 failed, 9 deselected**; the synthetic updater recorded an attempted destructive `uv venv --clear`. |
| Literal deployment-path reproducer | Exit 1: **1 failed, 12 deselected**; `Push-Location` treated `[test]` as a wildcard. |
| Final-path validation reproducer | Exit 1: **1 failed, 11 deselected**; the initial implementation did not rerun validation at the activated path. |
| Generated console-script reproducer | Exit 1: **1 failed, 13 deselected**; the synthetic native console returned 52 because its staging interpreter no longer existed. |
| Final focused regression run | Exit 0: **14 passed in 24.96 seconds**. |
| Ruff and format check | Exit 0; no findings; file formatted. |
| Independent runtime review | Initial reviewer independently ran **13 tests in 20.67 seconds**, all passing. Follow-up review of the final prefix/version-preservation change found no actionable issue. |

The test executables are synthetic fixtures compiled locally. They run through
real Windows PowerShell 5.1, with downloads/package behavior controlled by test
fixtures. They are not real SMB or scientific-package integration results.
PowerShell line coverage was not measured; the tests assert filesystem and
native-process behavior. Changed Python-module coverage belongs in the final
integration results.

## Real isolated installation and repair

The disposable acceptance deployment was:

```text
D:\pythonProject\HRI\Streamlit_Launcher_ECC\audit_artifacts\acceptance [ECC] (test)
```

It contained copied launcher support files and one synthetic Streamlit app.
Its cache was redirected inside the disposable directory and development
interpreter fallback was disabled. The live runtime and original applications
were not repaired, copied, or replaced.

The following PowerShell processes were executed against that directory:

```powershell
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "D:\pythonProject\HRI\Streamlit_Launcher_ECC\audit_artifacts\acceptance [ECC] (test)\install-acceptance.ps1"
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "D:\pythonProject\HRI\Streamlit_Launcher_ECC\audit_artifacts\acceptance [ECC] (test)\repair-acceptance.ps1"
```

The first driver called `fetch_runtime.ps1 -RuntimeDir <acceptance>\src\runtime`
and then `prepare_shared_runtime.ps1 -ReleaseDir <acceptance>`. The second saved
and removed only the synthetic deployment's Streamlit `RECORD`, reran shared
preparation, and executed the final `Scripts\streamlit.exe --version`. The
execution-policy option applied only to those test processes; no persistent
execution-policy setting was changed.

| Operation | Result and observed duration |
|---|---|
| Official CPython download, ensurepip, isolated imports, temporary venv, final-path validation | PASS, exit 0; **74.6551364 seconds** |
| Initial shared-runtime package preparation | PASS, exit 0; **35.4120336 seconds**; 41 packages installed |
| Candidate and activated runtime dependency checks | PASS; **43 packages** compatible at both paths |
| Required imports | PASS: `encodings`, `pandas`, `PySide6`, and `streamlit` |
| Missing-RECORD repair with a fresh staged base | PASS, exit 0; **84.4750898 seconds**; full enabled requirements installed before activation |
| Final prefix/standard-library probe after repair | PASS, exit 0; **0.0468909 seconds**; `sys.prefix`, `sys.base_prefix`, and `encodings` all point inside the activated runtime |
| Native `Scripts\streamlit.exe --version` after repair | PASS, exit 0; Streamlit **1.63.0**, **0.6021119 seconds** |

An intermediate real console-script test failed with exit 1 and
`uv trampoline failed to canonicalize script path`. The final `--prefix` change
fixed that reproduced regression. Module-based Streamlit and pip invocation
worked before and after the fix.

Local evidence is retained in `audit_artifacts/acceptance [ECC] (test)/install.log`,
`repair.log`, `runtime-probes.json` (before the console fix), and
`runtime-probes-after.json`. The separate offline prefix experiment is in
`audit_artifacts/prefix-probe/evidence.json`. Runtime binaries, generated logs,
and these scratch directories are excluded from Git.

These are individual observations on a local disk with an existing uv cache,
not clean-machine or SMB benchmarks. No percentage speedup is claimed.

## Additional performance evidence

With `RUN_PERFORMANCE_AUDIT=1`, the following command was executed:

```powershell
& .\src\.venv\Scripts\python.exe -m pytest src/tests/test_performance_audit.py -q -s --basetemp=audit_artifacts/pytest-performance
```

Exit 0: **2 passed in 28.77 seconds**, using controlled Python 3.11.15.

| Measurement | Observed result |
|---|---|
| Offscreen window construction | 0.087 seconds; this is not first-visible-HWND timing |
| One synthetic app | 1.317 seconds; 67.56 MiB |
| Two concurrent synthetic apps | 1.339 seconds; 134.07 MiB |
| Five concurrent synthetic apps | 1.075 seconds; 335.09 MiB |
| Stop and port release | 0.837 seconds |
| Twenty lifecycle cycles | 22.504 seconds total; 1.125 seconds mean |
| Owned child processes before/after cycles | 0 / 0 |
| Parent RSS before/after cycles | 73.64 / 73.99 MiB |

A separate local single-app cache probe measured discovery at **0.00224 seconds**,
first explicit app copy at **0.01160 seconds**, and a repeat fingerprint/cache
check at **0.01146 seconds**. It asserted that the copied synthetic entrypoint
matched its source. These are tiny synthetic-app measurements, not a benchmark
of private applications or a full runtime copy. A representative native launch
logged runtime validation work at **0.390 seconds**, first-window show at
**0.962 seconds** after entering Python `main`, and its first event-loop turn
at **0.963 seconds**. External wrapper-to-window measurements include earlier
runtime/import/bootstrap work and are reported separately below.

There is no comparable pre-change performance baseline. These observations do
not establish improvement, scientific throughput, or corporate-network timing.

## Acceptance matrix and remaining gates

| Scenario | Status | Evidence or remaining work |
|---|---|---|
| Runtime update from an unrelated working directory; spaces, brackets, parentheses | PASS | Synthetic PowerShell cases plus the real isolated installation path |
| Interrupted copy/install; validation failure; locked file; competing updater | PASS | Controlled Windows failure injection; old target remains recoverable |
| Missing RECORD repairs only the selected release | PASS | Two separate synthetic release roots and real isolated fresh-base repair |
| Generated console script survives candidate activation | PASS | Native synthetic regression, offline uv wheel probe, and real Streamlit console |
| Local temporary standalone runtime prefix and imports | PASS | Real before/after activation probes |
| Native source BAT/VBS/debug/shortcut windows and moved deployment | PASS | Six cases with a discoverable synthetic app; real visible HWND, responsiveness, expected executable and clean exit checked sequentially |
| Complete unit/Qt/browser suite, build, lint, scanners, and changed-module coverage | Integration owner to finalize | Append exact final commands, exit codes, counts, and artifact evidence below |
| Actual mapped drive `Z:` and equivalent corporate UNC deployment | NOT RUN | No corporate share acceptance was performed; synthetic path tests are separate |
| Intended `%LOCALAPPDATA%\OrganizationName\UnifiedPipelineLauncher` installed-runtime mode | NOT RUN | A local disposable runtime is not evidence for the live installed layout |
| Corporate share access denied/unavailable, read-only user, active multi-user update | NOT RUN | Requires an approved isolated deployment and representative accounts on the actual share |
| Physical interruption/power loss between activation moves | NOT RUN | Controlled errors/locks are covered; prior runtime is retained for manual recovery |
| Real scientific app/model output equivalence | NOT RUN | No laboratory apps, model weights, analytical rules, or data were changed or tested |
| Code signing and a full installer release | NOT RUN | Local portable build verification does not sign an executable or publish an installer |
| Complete runtime-cache copying/rollback performance on SMB | NOT RUN | Tiny synthetic app-copy timing and controlled rollback correctness do not measure this deployment workload |

Before deploying, run the native entrypoints one at a time and verify an actual
visible, responsive launcher, then exercise start/view/stop/restart/close with
synthetic applications. Repeat on approved mapped, equivalent UNC, and local
installed-runtime fixtures. Check an unrelated working directory, relocation,
Unicode paths, inherited Python configuration, and read-only access. Exercise
missing/unreadable `encodings`, actionable failure reporting, and malformed SVG
warnings. The release must not substitute wrapper exit status, offscreen Qt, or
mocked network paths for these acceptance checks.

## Security and operational residuals

The independent security report records the following executed outcomes:

| Check | Result |
|---|---|
| Final development/build/verification lock audit | pip-audit exit 0: 82 applicable packages, zero known vulnerabilities |
| Original checkout runtime metadata audit | pip-audit exit 1: 45 distributions; setuptools 65.5.0 produced seven entries covering four unique advisory families |
| Launcher/build source scan | Bandit exit 1: zero HIGH, two MEDIUM URL-scheme warnings, 18 LOW findings; findings reviewed without suppressions |
| Focused update/download security regressions | 33 passed, including real Windows junction cases |
| Focused security-module coverage | Downloader 87%, updater 89%, combined 88%; not whole-application coverage |
| AgentShield 1.4.0 six-file active-configuration snapshot | Exit 0: zero CRITICAL/HIGH, four MEDIUM, one LOW, one INFO; narrow static snapshot only |
| Intended installed runtime and full Git-history/entropy audit | NOT RUN |

The original runtime's four advisory families are CVE-2022-40897,
CVE-2024-6345, CVE-2025-47273, and CVE-2026-59890. The last is filesystem-dependent,
notably on macOS, and was not demonstrated as a Windows launcher exploit.
Presence of affected metadata is confirmed; exploitation was not attempted.
The proposed setuptools upgrade remains a separate compatibility task; no live
runtime upgrade was performed. The development lock retained every existing
package version set: 54 existing names plus 30 verification-related additions.
See the security report for advisory links, exact commands, and review limits.

- Runtime NuGet downloads use the official HTTPS endpoint and structural/import
  validation but do not verify a trusted pinned archive checksum. This remains
  an administrative-script download-integrity gap; no exploit was demonstrated
  by these tests. The separate Python `RuntimeDownloader` SHA-256 checks do not
  cover `fetch_runtime.ps1`.
- `uv pip check` establishes installed dependency consistency, not absence of
  known vulnerabilities. Development-lock and deployed-distribution audit
  results must be reported separately. The synthetic deployed set is not every
  local application's merged scientific dependency set.
- The exclusive file handle coordinates cooperating updaters. It does not prove
  every active user's processes permit safe replacement. Close affected apps
  and reserve a maintenance window, especially for SMB deployment.
- Activation uses separate directory moves. The previous runtime is retained,
  but process termination/power loss in the gap may require manual recovery.
- Development/app virtual environments still receive in-place updates. Removing
  automatic destructive rebuilding does not make those updates transactional.
- Coding-agent configuration is a separate review surface. The project-local
  override disables ECC's unneeded `chrome-devtools` MCP server; ECC common and
  Python rules reference `AGENTS.md`. The snapshot identified the bundled
  `npx -y chrome-devtools-mcp@latest` surface as an unnecessary unpinned execution
  path. A trusted-project reload/new task must verify effective server
  disablement; an existing session was not proven retroactively reconfigured.

No scientific package upgrades are proposed on the basis of these synthetic
runtime tests. Security-driven upgrades need their own compatibility evidence.

## Rollback

1. Close the launcher and all affected applications. Inspect whether `runtime`
   is already usable; a caught failure may have restored it automatically.
2. Identify the exact `runtime.previous-<id>` directory printed by the update.
   Preserve all copies and the recorded source commit. Do not select or remove
   directories using a wildcard.
3. If manual runtime restoration is necessary, move the failed runtime to a
   distinct sibling recovery directory, then move the selected previous runtime
   back to the exact original `runtime` path. Resolve both absolute paths and
   verify they are inside the intended deployment before any recursive move.
   These moves also require free handles and are not atomic as a pair.
4. Validate prefix/standard-library confinement and required imports with that
   runtime, then use the canonical debug entrypoint and verify the native UI.
5. If source rollback is needed, review the recorded prior commit in a separate
   recovery checkout. Do not reset the deployment or overwrite customized app
   files. Keep backups until source/runtime compatibility and application
   acceptance have been checked.

## Guarded manual source update to ECC

This procedure was **not executed against a live deployment**. Complete the
remaining acceptance gates first and close every affected user's apps. Run it
in Windows PowerShell 5.1 after entering the actual deployment directory. It
stops for local/untracked files; preserve and reconcile customized applications
in a separate checkout rather than removing them to bypass that guard.

```powershell
$ErrorActionPreference = 'Stop'
$Deployment = (Resolve-Path -LiteralPath (Get-Location).Path).Path
$LocalChanges = @(git -C $Deployment status --porcelain --untracked-files=normal)
if ($LASTEXITCODE -ne 0) { throw 'This is not an accessible Git deployment.' }
if ($LocalChanges.Count -gt 0) { throw 'Local/untracked files must be preserved and reviewed in a separate checkout.' }
$Before = git -C $Deployment rev-parse HEAD
if ($LASTEXITCODE -ne 0) { throw 'Cannot record the current source revision.' }
Write-Host "Source revision before update: $Before"

git -C $Deployment fetch origin ECC
if ($LASTEXITCODE -ne 0) { throw 'Fetching ECC failed; deployment was not updated.' }
git -C $Deployment show-ref --verify --quiet refs/heads/ECC
if ($LASTEXITCODE -eq 0) {
    git -C $Deployment switch ECC
} elseif ($LASTEXITCODE -eq 1) {
    git -C $Deployment switch --create ECC --track origin/ECC
} else {
    throw 'Cannot determine whether the ECC branch exists.'
}
if ($LASTEXITCODE -ne 0) { throw 'Cannot switch this clean deployment to ECC.' }
git -C $Deployment merge --ff-only origin/ECC
if ($LASTEXITCODE -ne 0) { throw 'ECC cannot be updated by fast-forward; stop and review the divergence.' }

$Prepare = Join-Path $Deployment 'src\scripts\prepare_shared_runtime.ps1'
powershell.exe -NoProfile -NonInteractive -File $Prepare -ReleaseDir $Deployment
if ($LASTEXITCODE -ne 0) { throw 'Runtime preparation failed. Keep the previous runtime and inspect the reported recovery paths.' }
$Shortcut = Join-Path $Deployment 'src\scripts\create_launcher_shortcut.ps1'
powershell.exe -NoProfile -NonInteractive -File $Shortcut -ReleaseDir $Deployment
if ($LASTEXITCODE -ne 0) { throw 'Shortcut generation failed; do not declare the update complete.' }
Write-Host 'Preparation finished. Verify START_LAUNCHER_DEBUG.bat and the regenerated shortcut before reopening the deployment.'
```

The snippet performs no blanket restore, clean, force-push, or application-file
copy. It uses ordinary shared-runtime preparation without requesting unrelated
package upgrades. A dirty customized deployment needs a reviewed merge/release
procedure instead of an automatic branch switch.

## Final integration record

The initial complete-suite baseline was **7 failed, 118 passed, 13 skipped,
2 xfailed** (32.83 seconds, exit 1). Several assertions described the superseded
VBS/cache architecture. Their replacements assert current behavior and are
supplemented by actual Windows process, PowerShell and native-window regressions.

Additional recorded RED/GREEN evidence includes:

| Regression | RED | GREEN |
|---|---|---|
| Entry points, quoting and real exit codes | 5 failed, 2 passed | 7 passed after canonical-wrapper fixes |
| Startup progress and portable packaging | 3 failed | 3 passed |
| RuntimeNotFoundError survives worker propagation | 1 failed, 2 passed | Included in final startup suite |
| Download fallback validation and bracket-path quality gate | 4 failed | 4 passed; relevant existing suites 19 passed |
| Missing icon from real registry reaches actual AppCard fallback | 2 failed, 17 passed | 19 passed, including preserved path/schema checks |
| PowerShell checksum API | Actual 5.1 MethodNotFound error | Real checksum and quality-gate regression passed |
| Python startup environment contamination | Native launch could not import launcher | `-E -s` source startup and inherited-option regressions passed |

The native acceptance fixture was strengthened to require discovery of its
synthetic app. This caught incomplete fixture metadata; the scratch fixture was
corrected before final native acceptance. Earlier window-only success does not
establish that an app was discovered. No real application registry was edited.

The first PyInstaller build passed structure verification but its real window
test failed: unrelated Poppler ICU DLLs inherited through the build PATH broke
Qt imports. Packaging success alone was therefore not accepted as a release pass.
The final build and native evidence below cover the corrected build environment.

Verification uses the pinned development interpreter. Commands below run from
the worktree root except the explicitly noted build command. The two acceptance
variables identify prepared synthetic directories inside `audit_artifacts`;
they must never identify the live runtime or private applications.

```powershell
$Python = Join-Path (Get-Location) 'src\.venv\Scripts\python.exe'
$Uv = & .\src\scripts\ensure_uv.ps1
& $Uv lock --project src --check
& $Uv pip check --python $Python
& $Python -m compileall -q src/launcher src/build_scripts src/scripts src/tests
& $Python -m ruff check --isolated --select E9,F63,F7,F82 src/launcher src/build_scripts src/scripts src/tests
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\src\scripts\public_quality_gate.ps1 -SkipPytest

$env:ECC_ACCEPTANCE_ROOT = Join-Path (Get-Location) 'audit_artifacts\acceptance [ECC] (test)'
$env:ECC_FROZEN_ACCEPTANCE_ROOT = Join-Path (Get-Location) 'audit_artifacts\frozen [ECC] (test)'
$env:COVERAGE_FILE = Join-Path (Get-Location) 'audit_artifacts\final-coverage\.coverage'
New-Item -ItemType Directory -Force (Split-Path -Parent $env:COVERAGE_FILE) | Out-Null
& $Python -m coverage run --source=src/launcher,src/build_scripts -m pytest src/tests -q -ra --basetemp=audit_artifacts/pytest-final-complete --junitxml=audit_artifacts/tests-final.xml
& $Python -m coverage report --show-missing
& $Python -m coverage xml -o audit_artifacts/coverage-final.xml
```

Source checks are syntax/correctness lint, not a full typing certification.
Static type checking is **NOT RUN** because no established project typing gate
exists. Python 3.12 and hosted GitHub CI outcomes are separate from this local
Python 3.11 execution; see the branch's Actions run for their results.

The development dependency consistency check passed for **83 installed packages**;
the synthetic standalone runtime check passed for **43 packages**. Vulnerability
audits are separate: the development export passed for **82 applicable packages**;
the original runtime metadata audit failed for old setuptools. The final Bandit
scan exited **1** with **0 HIGH, 2 MEDIUM, 18 LOW, 0 scan errors**. The reviewed
medium warnings and dependency applicability are detailed in [security-review.md](security-review.md).

Unchanged expected failures are long application working directories rejected
by Windows CreateProcess and reconstruction of children from an earlier launcher
instance (no persistent process registry). They were not deleted or converted
into passing assertions. A file-symlink regression needs an unavailable Windows
privilege; separate directory-junction regressions did execute. The original
worktree's empty bundled-runtime test is not a failure of the independently
prepared standalone runtime. The opt-in performance suite ran separately above.
