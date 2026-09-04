# Unified Pipeline Launcher

Unified Pipeline Launcher is a Windows desktop application for starting,
viewing, restarting, and stopping local Streamlit applications from one screen.

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
2. Installs the launcher and all registered app packages.
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

All three launcher entry points resolve paths from their own installation folder,
clear inherited Python/Conda environment variables, use the bundled runtime, and
launch the module with isolated Python startup (`-I -m launcher`). Normal network
launches execute directly from the verified bundled runtime; they do not copy the
entire runtime or all application folders into `%LOCALAPPDATA%` before showing the
launcher window. Local caching remains available only when explicitly enabled in
configuration.

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
updates the portable runtime and any recognized virtual environments, then
validates them. The shared-runtime installer uses `uv --link-mode=copy` when the
runtime is on a mapped/UNC filesystem and rebuilds a damaged runtime when package
metadata such as `*.dist-info/RECORD` is missing.

Start the launcher again after both commands finish.

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

Run the setup script once. It installs the pinned `uv` tool into the launcher's
local tools directory and synchronizes the locked Python 3.11/3.12 development
environment:

```powershell
.\src\scripts\setup_dev.ps1
```

The script prints the exact test command for its controlled `uv.exe`.
Developers who already have `uv` on `PATH` can use the standard workflow:

```powershell
uv sync --project .\src --locked
uv run --project .\src --locked pytest .\src\tests
```

`src/pyproject.toml` defines launcher and development dependencies,
`src/uv.lock` pins the complete development/build environment, and each
`apps/<app>/requirements.txt` remains the source for that app's packages.
`src/requirements-launcher.txt` is a generated compatibility export used when
preparing portable shared runtimes.

Run the public readiness checks from the repository root:

```powershell
.\src\scripts\public_quality_gate.ps1
```
