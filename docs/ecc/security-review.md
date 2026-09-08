# ECC security review

Review date: 2026-09-08. Branch: `ECC`. Comparison base:
`09652ff1a1426200e67c9e521c75bc24e2877455` (`clean_ui`).

The reviewed source can be published as a development branch. This report does
not authorize production deployment: complete the deployment acceptance gates
in [release-report.md](release-report.md), including the real mapped/UNC share,
installed local runtime, deployed application requirements, and runtime
vulnerability remediation. No live runtime or scientific dependency was
modified by this review.

## 1. Application and deployment security

ECC 2.2.1 `security-review`, `security-reviewer`, `python-reviewer`, and
`code-reviewer` guidance was applied to the actual Python/PowerShell diff.
Tools ran in isolated uv tool environments or the worktree development venv,
using uv **0.11.14** and Windows Python **3.11**. Scanner outputs stayed in the
local temporary directory; dependency services received public package names
and versions, not application source, models, or laboratory data.

| Boundary | Reviewed controls and evidence | Residual requirement |
|---|---|---|
| Network source to executable/runtime | Runtime prefix/stdlib canonicalization, environment scrubbing, explicit local-cache behavior | Verify actual share ACLs and mapped/UNC/local installed paths; checksums do not establish publisher identity if the same writer can replace both files and hashes |
| App registry to subprocess | Validated IDs/versions/relative paths; argument-list subprocess creation; loopback binding, CORS and XSRF enabled | Application code remains executable trusted code; private scientific applications were not audited or changed |
| Python `RuntimeDownloader` archive to files | HTTPS initial URL, pinned SHA-256, unsafe member rejection, canonical managed directories, private staging | Administrative configuration and release provenance remain trust roots; these checks do not cover the PowerShell NuGet download |
| Runtime update to running apps | Previous versions retained; staged validation; update locks; fail-closed paths and identity checks | Real file-lock, multiuser, interruption and administrator recovery acceptance remains required |
| User inputs to scientific processing | No scientific processing or model changes in the publication diff | Full private-app input/data-flow review is outside this source change |

The separate administrative `src/scripts/fetch_runtime.ps1` download uses the
official HTTPS NuGet endpoint and structural/import validation, but it does
not verify a trusted pinned archive checksum. That download-integrity gap
remains open; the Python downloader's SHA-256 enforcement does not close it.

### Executed checks

Commands below ran from the worktree root unless noted. The original runtime
metadata path is represented by `$OriginalRuntimeSitePackages`; it pointed to
the existing original checkout's `src/runtime/Lib/site-packages`. That runtime
was neither executed nor modified by the dependency audit.

```powershell
uv export --project src --locked --all-groups --no-emit-project --no-hashes --output-file "$env:TEMP\ecc-dev-audit-final-requirements.txt" --quiet
uv tool run --from pip-audit==2.10.1 pip-audit -r "$env:TEMP\ecc-dev-audit-final-requirements.txt" --no-deps --disable-pip --progress-spinner off --format json --desc off --output "$env:TEMP\ecc-dev-pip-audit-final.json"
uv tool run --from pip-audit==2.10.1 pip-audit --path $OriginalRuntimeSitePackages --progress-spinner off --format json --desc off --output "$env:TEMP\ecc-source-runtime-pip-audit.json"
src\.venv\Scripts\python.exe -m bandit -r src/launcher src/build_scripts -f json -o "$env:TEMP\ecc-bandit-final.json" -q
src\.venv\Scripts\python.exe -m pytest src/tests/test_update_security.py src/tests/test_runtime_downloader.py src/tests/test_update_manager.py -q
src\.venv\Scripts\python.exe -m ruff check src/launcher/runtime_downloader.py src/launcher/update_manager.py src/tests/test_update_security.py src/tests/test_update_manager.py
```

| Check | Tool / exit | Result |
|---|---|---|
| Development/build/verification lock audit | pip-audit 2.10.1 / **0** | 82 applicable exported packages, zero known vulnerabilities, zero skipped packages |
| Original checkout runtime metadata audit | pip-audit 2.10.1 / **1** | 45 distributions; setuptools 65.5.0 produced seven entries representing four unique advisory families |
| Full launcher/build source scan | Bandit 1.9.4 / **1** | Zero HIGH, two MEDIUM B310 URL-scheme warnings, 18 LOW findings, no suppressions |
| Focused update/download security regressions | pytest / **0** | 33 passed, including actual Windows directory junction cases |
| Focused static checks | Ruff 0.16.6 / **0** | Passed |
| Focused coverage | coverage 7.16.0 / **0** | Downloader 87%, updater 89%, combined 88%; not whole-application coverage |
| Intended installed runtime audit | **NOT RUN** | Expected LOCALAPPDATA runtime had no interpreter or installed distribution directory |
| Full Git-history/entropy secret audit | **NOT RUN** | Targeted current publication-source checks are described below |

The B310 findings were reviewed at `HealthChecker._url_ok` (URL constructed
from a launcher-allocated loopback port) and `RuntimeDownloader._download_archive`
(initial HTTPS URL enforced before opening, with archive SHA-256 verification).
They are broad scanner warnings, not reproduced arbitrary-scheme execution.
LOW findings primarily flag subprocess imports/calls. Scanner exit 1 is
recorded explicitly rather than described as an unqualified clean scan.

The security regressions first reproduced unsafe versions, external cached
executables, unsafe ZIP member acceptance, overwritten runtimes/releases,
non-HTTPS downloads, activation of user app directories, and internal cache
junction aliases. Fixes were reviewed independently; a reviewer found the
internal-alias case, which received additional failing Windows tests and a
verified fix. Remaining uncovered branches include some download I/O failures,
invalid metadata and update-manifest parsing paths.

### Confirmed existing-runtime dependency finding

The installed **setuptools 65.5.0** metadata is within these advisory ranges.
Presence is confirmed; exploitation against this launcher was not attempted.

| Advisory | Effect / first fixed version | Applicability |
|---|---|---|
| [CVE-2022-40897](https://github.com/advisories/GHSA-r9hx-vwmv-q579) | Package-index parsing denial of service / 65.5.1 | Relevant when vulnerable package-index functions consume malicious HTML |
| [CVE-2024-6345](https://github.com/advisories/GHSA-cx63-2mw6-8hw5) | Package-URL command injection / 70.0.0 | Relevant when deprecated download functions receive attacker-controlled URLs |
| [CVE-2025-47273](https://github.com/advisories/GHSA-5rjg-fvgr-3xxf) | PackageIndex download path traversal / 78.1.1 | Relevant when the vulnerable download path is used |
| [CVE-2026-59890](https://github.com/advisories/GHSA-h35f-9h28-mq5c) | Source-distribution exclusion bypass / 83.0.0 | Filesystem-dependent, notably macOS APFS/HFS+; not demonstrated as a Windows launcher runtime exploit |

**Separate compatibility proposal, not an applied upgrade:** test the existing
development-lock version `setuptools==84.0.0` in a disposable copy of the
deployed runtime. Preserve every other package pin; check dependency compatibility,
app imports, build/install operations, legacy `pkg_resources` consumers, and
synthetic saved-model/application outputs. Re-audit the complete prepared
runtime. Activate it only through the reviewed staging/backup workflow after
acceptance. The development lock passing does not prove this upgrade is
compatible with every private app.

### Publication diff and pin preservation

Python `tomllib` compared every package-name/version set in
`git show 09652ff:src/uv.lock` with the working `src/uv.lock`: **all 54 existing
package names retained their version sets**. The current lock has 84 package
names: 30 additions for the optional verification tools and their dependencies.
The six direct verification pins are Bandit 1.9.4, coverage 7.16.0,
pip-audit 2.10.1, Playwright 1.62.0, psutil 7.2.2 and Ruff 0.16.6.
Lock entries and applicable exported package counts differ because the audit
excludes the local project and evaluates platform markers.

A prepublication snapshot collected modified tracked files using
`git diff --name-only --diff-filter=ACMR 09652ff` and new files using
`git ls-files --others --exclude-standard`. A local Python scan read those
53 files and reported only locations for private-key headers, GitHub token,
AWS access-key and OpenAI-key patterns: **zero matches**. The same inventory
contained no binary files, changed app/runtime directories, or scientific/data
file extensions. An earlier broader check covered 59 tracked launcher,
scripts, CI and wrapper files with zero high-confidence matches.
The 53-file inventory exactly matched `changed-files.md`; a repeated lock
comparison again found no changes to the 54 existing package version sets.
These checks do not certify arbitrary prose or Git history as free of secrets;
the final staging list must still match the approved source/documentation diff.

## 2. Coding-agent configuration security

This review is separate from application security. ECC **2.2.1** was already
installed; no full/manual ECC installer or additional integration was invoked.
The actual Codex manifest points to `.mcp.json` and
`hooks/codex-hooks.json`. Its shipped Claude `hooks/hooks.json` and example MCP
catalog are not evidence of active Codex hooks/servers.

The Codex hook file declares one `SessionStart` bootstrap. The reviewed chain
includes `plugin-hook-bootstrap.js`, `session-start-bootstrap.js`,
`session-start.js`, and `run-with-flags.js`. These execute with the coding
agent's user privileges and can load local context; ECC is not a sandbox.
No OS policy, TLS verification, antivirus settings, or global plugin files were
changed by this review.

AgentShield **1.4.0** was first downloaded as an npm tarball, checked against
its npm SHA-512 integrity value, and its static `scan` dispatch was inspected.
It was installed only in a temporary tool directory with:

```powershell
npm.cmd install --prefix "$env:TEMP\ecc-agentshield-review-1.4.0\runner" --ignore-scripts --no-audit --no-fund --package-lock true ecc-agentshield@1.4.0
node "$env:TEMP\ecc-agentshield-review-1.4.0\runner\node_modules\ecc-agentshield\dist\index.js" scan --path "$env:TEMP\ecc-agentshield-review-1.4.0\active-codex-surface" --format json
```

The snapshot contained the exact active hook configuration and four scripts;
`.mcp.json` was copied as `mcp.json` because this scanner version's discovery
misses the dotted filename. This is a **six-file static configuration snapshot**,
not a full workstation/plugin dependency audit. No `--opus`, `--deep`,
`--injection`, `--sandbox`, `--fix`, online supply-chain scan or webhook was used.
Install scripts were disabled. AgentShield's transitive npm dependencies were
not separately certified; the temporary scanner is not a production dependency.

AgentShield exited **0**, reporting zero CRITICAL/HIGH, four MEDIUM, one LOW,
and one INFO finding. Its grade was A/96; the narrow snapshot and scanner
heuristics make that unsuitable as a whole-system security rating.

- **Confirmed MEDIUM:** the bundled MCP starts
  `npx -y chrome-devtools-mcp@latest`, an unpinned automatic package execution
  surface unnecessary for this project.
- **Context-dependent/false-positive warnings:** missing Claude permission,
  PreToolUse and Stop blocks are not equivalent to absent Codex controls; the
  chained-command warning counts JavaScript semicolons in the bootstrap.
- **INFO:** the MCP configuration lacks a description.

The project now disables that MCP through the documented configuration:

```toml
[plugins."ecc@ecc".mcp_servers.chrome-devtools]
enabled = false
```

This preserves ECC skills and the installed manifest. The setting is supported
by the [official Codex configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference).
A trusted-project reload/new task must confirm effective server disablement;
this report does not claim an existing session was reconfigured retroactively.

## Release status

No critical/high finding remains open in the downloader/updater changes after
independent rechecking. The vulnerable existing runtime, unavailable actual SMB/local
installation acceptance, unreviewed private app dependency union, and share
write permissions remain deployment gates. Publishing `ECC` does not turn
those **FAIL / NOT RUN** items into production approval.
