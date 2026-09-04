# Unified Pipeline Launcher

Unified Pipeline Launcher is a Windows desktop application for starting,
viewing, restarting, and stopping a collection of local Streamlit apps from one
screen.

## Install

Requirements: Windows 10 or 11, Microsoft Edge, and internet access during the
first installation. A separate Python installation is not required.

1. Clone or download this repository.
2. Double-click `INSTALL.bat`.
3. Wait for the launcher window to open.

The installer downloads the private Python runtime, installs all declared
packages, creates `START_LAUNCHER.lnk`, and starts the launcher. It deletes
`INSTALL.bat` only after a successful installation; after a failure it keeps the
file so the installation can be retried.

## Use

- Double-click `START_LAUNCHER.lnk` or `START_LAUNCHER.vbs` for normal use.
- Use `START_LAUNCHER_DEBUG.bat` only when troubleshooting startup errors.
- Use `UPDATE_PACKAGES.bat` to update the bundled runtime and every recognized
  virtual environment from the checked-in requirements files.

To update an existing clone without rebuilding the application:

```powershell
git pull --ff-only origin main
.\UPDATE_PACKAGES.bat
```

The launcher opens apps in an isolated Microsoft Edge Guest window with browser
extensions disabled. App servers bind only to `127.0.0.1`, use Streamlit's CORS
and XSRF protections, and are stopped when the launcher exits. On startup, the
launcher also removes identity-matched processes left by an earlier crash.

### Domain And Network Drives

The repository can be installed from either a mapped path such as
`Z:\mycology\Unified-Pipeline-Launcher` or its UNC equivalent. During
installation, the generated shortcut uses the stable UNC location when Windows
exposes one, so a changed drive letter does not break it. Python and app code
are cached under `%LOCALAPPDATA%\OrganizationName\UnifiedPipelineLauncher` for
normal launches; the network share remains the source of truth.

Use the mapped or UNC path available on that PC. Do not hardcode `Z:` inside an
app because domain mappings can differ between users.

## Add An App

Application files live in `apps`. Copy the template:

```powershell
Copy-Item -Recurse .\apps\app_template .\apps\my_app
```

Edit `apps/my_app/app.py`, list every dependency in
`apps/my_app/requirements.txt`, and provide an icon at
`apps/my_app/assets/icon.svg`. Then add the app to `apps/apps.json`:

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

Restart the launcher after changing the registry. Bump `version` whenever an
app's dependencies or behavior changes.

To add or change a dependency and refresh the runtime in one command:

```powershell
.\src\scripts\update_dependencies.ps1 -Target app -AppId my-app -Package "plotly>=5,<6"
```

## Project Structure

```text
Unified-Pipeline-Launcher/
|-- INSTALL.bat                 Temporary one-time installer
|-- START_LAUNCHER.vbs          Normal no-console launcher
|-- START_LAUNCHER_DEBUG.bat    Troubleshooting launcher
|-- UPDATE_PACKAGES.bat         Python environment updater
|-- apps/                       App registry and Streamlit apps
|-- README.md
|-- LICENSE
`-- src/
    |-- config/                 Launcher configuration
    |-- launcher/               Desktop application
    |-- scripts/                Install, update, and build support
    |-- tests/                  Automated tests
    `-- pyproject.toml           Python package metadata
```

## Development

Use Python 3.11 or 3.12:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r .\src\requirements-dev.txt
Set-Location .\src
..\.venv\Scripts\python.exe -m pytest
```

Run the public readiness checks from the repository root:

```powershell
.\src\scripts\public_quality_gate.ps1
```
