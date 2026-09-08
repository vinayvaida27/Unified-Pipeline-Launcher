# Repository Rules

## Network Path Regression Requirement

The project source may be opened as either
`Z:\Vinay_Vaida\Unified-Pipeline-Launcher` or
`\\wcsmb\Mycology\Vinay_Vaida\Unified-Pipeline-Launcher` (`Z:\` maps to
`\\wcsmb\Mycology\`). The installed runtime remains local under
`%LOCALAPPDATA%\OrganizationName\UnifiedPipelineLauncher`.

For launcher, updater, runtime, PowerShell, Qt resource, or path changes, test
the mapped path, equivalent UNC path, and local installed runtime. Never let a
network source path become `sys.prefix` for the local runtime. Regressions must
cover missing `encodings`, quoted/illegal `Resolve-Path` input, and malformed
SVG warnings.

## Authoritative Instructions and Scope

This file is the authoritative source for project-specific requirements.
`CLAUDE.md` and the project-local ECC rules reference it rather than maintaining
separate copies. ECC is development tooling, never a launcher or app dependency.

Preserve both portable source deployments and the existing local installed
runtime mode. Do not relocate a runtime, change scientific algorithms, model
weights, saved-model formats, clinical rules, classifications, or thresholds as
part of launcher maintenance. Preserve dependency pins unless an upgrade is
explicitly selected and compatibility is verified.

Protect customized `apps/apps.json`, untracked apps, models, data, icons, and
local changes. Never use `git reset --hard`, `git clean`, blanket restores, or
`git add .`. Do not send laboratory/patient data, secrets, or local app contents
to external services or GitHub without explicit user authorization. Use synthetic
fixtures for tests and examples.
Stage only an explicitly reviewed file list. Commit and push only when the user
has authorized those actions; do not force-push.

## Startup and Runtime Contracts

- `START_LAUNCHER.bat` owns startup logic. VBS invokes it with `--silent`, the
  debug BAT invokes it with `--debug`, and the generated shortcut targets VBS.
  Preserve process exit codes and actionable visible failures.
- Resolve paths from the entrypoint location, independent of the caller's
  working directory. Source-tree startup uses `-E -s -m launcher` from the
  trusted source directory. `-I` is appropriate for isolated runtime probes;
  it must not silently remove the source directory from launcher imports.
- Validate the runtime's own prefix and standard library, not just the presence
  of `python.exe`. Clear inherited Python configuration and exclude user-site
  packages. Never accept the network source as the local runtime's prefix.
- Normal launches must not install/resolve dependencies, create per-app
  environments in shared-runtime mode, or automatically copy/hash the complete
  runtime and application tree. Explicit maintenance/cache work must report
  progress and keep Qt widget operations on the GUI thread.
- Process cleanup must match recorded process identity and ownership. Never
  terminate unrelated Python processes or another user's applications.
- Malformed or missing SVGs need fallback rendering and bounded logging. Test
  warning-producing SVGs that Qt partially accepts, and exclude malformed test
  fixtures/backups from production asset scans.

## Maintenance and Dependency Contracts

Windows PowerShell 5.1 is supported. Use literal path operations, reject invalid
path input, check native exit codes, and avoid unsupported .NET APIs such as
`Path.GetRelativePath`. Keep the pinned uv version aligned across scripts and
`src/pyproject.toml` (currently `0.11.14`). Use the controlled development
environment and `--link-mode=copy` for cross-filesystem installation.

`src/uv.lock` controls development/build/verification dependencies; it does not
prove coverage of every application's requirements. Prepare the shared runtime
from the launcher requirements export and enabled applications' requirements.
Keep scanners/test tools in the optional development `verification` group, out
of the production runtime. Compatibility checks are not vulnerability scans.

Runtime replacement must hold a lock for the actual target, build a confined
sibling candidate, validate it before and after activation, and preserve the
previous runtime for rollback. Missing `RECORD` repair must rebuild the selected
target in staging, never another checkout's runtime. Preserve Windows console
entrypoints when moving a candidate: uv `--prefix` installs into the candidate
while `--python` selects the final interpreter path. These directory moves are
not a single atomic transaction. Keep failure recovery and disk-space needs
visible; require a maintenance window with affected applications closed.

Do not automatically clear an existing virtual environment after a failed
sync. Do not claim the retained-runtime protection covers the separate in-place
development/app virtual-environment updates.

## Verification and Release Evidence

Use the ECC workflow: inspect actual callers, plan the smallest fix, reproduce a
failure, implement it, rerun relevant checks, and obtain independent review of
the actual diff. Keep executable RED/GREEN evidence and exact commands/results.
User authorization governs commit/push checkpoints; do not create automatic
checkpoint commits merely because a generic skill recommends them.

Use a separate checkout and disposable synthetic deployments for disruptive
tests. Never repair or replace the live runtime as a test. Distinguish unit,
offscreen Qt, actual Windows/PowerShell, browser, and real SMB acceptance.
A wrapper's zero exit code or successful imports do not prove a native window
appeared. Exercise entrypoints one at a time, closing each previous instance.

Report PASS / FAIL / NOT RUN, including unavailable mapped/UNC/local-installed
acceptance. Record relevant coverage gaps, security findings, measured timings,
rollback instructions, and the reviewed file manifest. Do not weaken failing
tests, invent performance gains, or label unverified changes production-ready.
