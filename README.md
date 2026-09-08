<p align="center">
  <img src="src/assets/launcher/launcher.png" alt="Unified Pipeline Launcher logo" width="160">
</p>

# Unified Pipeline Launcher

Unified Pipeline Launcher is a Windows desktop application for starting,
viewing, restarting, and stopping local Streamlit applications from one screen.

> **Open source:** released under the [MIT License](LICENSE). Contributions are
> welcome; see [CONTRIBUTING.md](CONTRIBUTING.md),
> [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), and [SECURITY.md](SECURITY.md).

This repository contains public demonstration applications only. Do not commit
laboratory, patient, credential, or other sensitive data.

## Requirements

- Windows 10 or 11
- Microsoft Edge
- Git or GitHub CLI
- Internet access during the first installation and package updates
- Write access to the installation folder

A separate Python installation is not required.

## First-Time Installation

Clone the repository and run the installer:

```powershell
gh repo clone vinayvaida27/Unified-Pipeline-Launcher
Set-Location ".\Unified-Pipeline-Launcher"
.\INSTALL.bat
```

Git can be used instead of GitHub CLI:

```powershell
git clone https://github.com/vinayvaida27/Unified-Pipeline-Launcher.git
Set-Location ".\Unified-Pipeline-Launcher"
.\INSTALL.bat
```

You can also open the cloned folder in File Explorer and double-click
`INSTALL.bat`. The installer:

1. Downloads a portable Python runtime.
2. Installs the launcher and enabled applications' packages.
3. Creates `START_LAUNCHER.lnk`.
4. Starts the launcher.
5. Deletes `INSTALL.bat` after a successful installation.

If installation fails, `INSTALL.bat` is kept so it can be run again.

## Daily Use

- Double-click `START_LAUNCHER.lnk` for normal use.
- Use `START_LAUNCHER.vbs` for a silent no-console launch.
- Use `START_LAUNCHER.bat` for a normal command-line launch.
- Use `START_LAUNCHER_DEBUG.bat` to display runtime/startup errors.
- Select **Open** for one app or **Open All** for all visible apps.
- Closing the launcher stops apps that it started.

`START_LAUNCHER.bat` is the canonical startup implementation. VBS delegates to it
with `--silent`, the debug BAT delegates with `--debug`, and the shortcut targets
VBS. The wrappers wait for the launcher and preserve a failing exit status; VBS
shows an actionable error if startup fails.

Startup resolves paths from the installation folder, clears inherited Python
configuration, and validates the bundled interpreter's own standard library.
Source-tree module startup uses `-E -s -m launcher` from the trusted source
directory. Isolated `-I` probes validate the runtime separately; `-I -m launcher`
would lose the source directory needed for package discovery.

Normal portable network launches use the verified bundled runtime without
copying the entire runtime or application tree before showing the window.
The canonical entrypoints pass `--no-local-cache`. Explicit cache operations
remain available through configuration/direct invocation. Existing local
installed deployments keep their runtime local; a network source must never
become that runtime's Python prefix. Maintenance does not automatically switch
between these deployment modes.

The launcher opens apps in an isolated Microsoft Edge Guest window with browser
extensions disabled. App servers bind only to `127.0.0.1`, use Streamlit's CORS
and XSRF protections, and are stopped when the launcher exits. Startup also
removes identity-matched processes left by an earlier crash. Normal app launches
run the bundled Python directly; dependency tools are not invoked when an app is
opened.

## Pull Updates

Close the launcher and its apps before updating. Open PowerShell in the cloned
repository and run:

```powershell
git pull --ff-only
.\UPDATE_PACKAGES.bat
```

`git pull` updates the currently checked-out branch without hard-coding `main`.
`UPDATE_PACKAGES.bat` bootstraps the project's pinned `uv` tool when needed,
updates the portable runtime and recognized virtual environments, and reports
failed checks. Maintenance installation requests `--link-mode=copy` so the local
uv cache also works with mapped/UNC destinations.

Shared-runtime maintenance holds an exclusive updater lock and prepares a
complete sibling candidate. It validates the candidate, retains the old runtime
as `runtime.previous-<id>`, activates the replacement, and validates the final
path. Failed activation attempts restore the prior directory. A missing
`*.dist-info/RECORD` triggers a fresh Python base and a full requirements install
inside staging for the selected release. Windows console scripts are generated
with the final interpreter path so they survive activation.

Close affected apps for every user of a shared deployment and allow space for
the candidate and retained backups. The two directory moves are not one atomic
transaction; keep the reported previous-runtime path for recovery. Development
and app virtual-environment updates still run in place. A failed development
sync no longer automatically clears and rebuilds that environment.

Start the launcher again after both commands finish.

The `ECC` branch contains the current reliability work. Its
[release report](docs/ecc/release-report.md) lists executed checks, unresolved
acceptance work, and a guarded manual update procedure. Local tests do not
establish corporate SMB or local installed-runtime acceptance.

## Add An App

Application folders live directly under `apps`. Copy the included template:

```powershell
Copy-Item -Recurse .\apps\app_template .\apps\my_app
```

Update these files:

- `apps/my_app/app.py`: the Streamlit entry point
- `apps/my_app/requirements.txt`: all Python dependencies
- `apps/my_app/assets/icon.svg`: the launcher icon
- `apps/apps.json`: the application registry

Add an entry to the `applications` array in `apps/apps.json`:

```json
{
  "id": "my-app",
  "name": "My App",
  "folder": "my_app",
  "description": "A short description shown in the launcher.",
  "category": "General",
  "version": "1.0.0",
  "display_order": 11,
  "enabled": true,
  "icon": "assets/icon.svg"
}
```

Bump `version` whenever the app's dependencies or behavior changes. To add a
dependency and refresh the runtime:

```powershell
.\src\scripts\update_dependencies.ps1 -Target app -AppId my-app -Package "plotly>=5,<6"
```

Commit and push the app folder and `apps/apps.json`. In other installations,
use the commands in **Pull Updates**, then restart the launcher.

Application SVG icons are validated by the public quality gate. If a local or
untracked SVG is malformed, the desktop UI falls back to the application's first
letter instead of repeatedly rendering invalid SVG path data.

## Project Structure

```text
Unified-Pipeline-Launcher/
|-- apps/                       App registry and Streamlit apps
|-- INSTALL.bat                 Temporary first-time installer
|-- START_LAUNCHER.vbs          Normal no-console launcher
|-- START_LAUNCHER.bat          Normal command-line launcher
|-- START_LAUNCHER_DEBUG.bat    Troubleshooting launcher
|-- UPDATE_PACKAGES.bat         Python environment updater
|-- README.md
|-- LICENSE
`-- src/
    |-- config/                 Launcher configuration
    |-- launcher/               Desktop application
    |-- scripts/                Install, update, and build support
    |-- tests/                  Automated tests
    |-- pyproject.toml          Dependency and package metadata
    `-- uv.lock                 Reproducible development/build lock
```

## Development

To convert an existing Python script into a launcher-managed Streamlit app, use
[SKILL.md](SKILL.md). It requires a concise five-question intake covering input,
output, workflow, parameters, and app/privacy details before code is changed.

Run the setup script once. It installs the pinned `uv` tool into the launcher's
local tools directory and synchronizes the locked Python 3.11/3.12 development
environment:

```powershell
.\src\scripts\setup_dev.ps1
```

The script prints the exact test command for its controlled `uv.exe`.
Developers who already have the pinned `uv` on `PATH` can use the standard workflow:

```powershell
uv sync --project .\src --locked --link-mode=copy
uv run --project .\src --locked --no-sync python -m pytest .\src\tests
```

`src/pyproject.toml` defines launcher and development dependencies,
`src/uv.lock` pins the complete development/build environment, and each
`apps/<app>/requirements.txt` remains the source for that app's packages.
`src/requirements-launcher.txt` is a generated compatibility export used when
preparing portable shared runtimes.

The optional `verification` group pins coverage, lint, security, browser-test,
and process-inspection tools. Install it only in the development environment:

```powershell
$Uv = & .\src\scripts\ensure_uv.ps1
if ($LASTEXITCODE -ne 0) { throw "Pinned uv setup failed." }
& $Uv sync --project .\src --locked --group verification --link-mode=copy
if ($LASTEXITCODE -ne 0) { throw "Verification environment setup failed." }
& $Uv run --project .\src --locked --no-sync python -m pytest .\src\tests
```

Offscreen Qt, native Windows entrypoint, and real SMB checks are separate test
categories. Native acceptance requires a disposable prepared deployment and
`ECC_ACCEPTANCE_ROOT`; normal hosted CI does not test the corporate share.
See [AGENTS.md](AGENTS.md) for the authoritative path, data-protection, and
verification requirements.

Run the public readiness checks from the repository root:

```powershell
.\src\scripts\public_quality_gate.ps1
```

## Contributing

Please start with [CONTRIBUTING.md](CONTRIBUTING.md). Pull requests should keep
the public apps and documentation free of sensitive data, include focused tests
for behavior changes, and preserve the documented runtime/path constraints.

## Security

Report a possible vulnerability privately using the process in
[SECURITY.md](SECURITY.md). Do not open a public issue containing credentials,
patient data, or an exploitable proof of concept.

## License

Copyright © 2026 vinayvaida27. This project is licensed under the
[MIT License](LICENSE).
