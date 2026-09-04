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
- Use `START_LAUNCHER.vbs` if the shortcut is unavailable.
- Use `START_LAUNCHER_DEBUG.bat` to display startup errors.
- Select **Open** for one app or **Open All** for all visible apps.
- Closing the launcher stops apps that it started.

The launcher opens apps in an isolated Microsoft Edge Guest window with browser
extensions disabled. App servers bind only to `127.0.0.1`, use Streamlit's CORS
and XSRF protections, and are stopped when the launcher exits. Startup also
removes identity-matched processes left by an earlier crash.

## Pull Updates

Close the launcher and its apps before updating. Open PowerShell in the cloned
repository and run:

```powershell
git pull --ff-only origin main
.\UPDATE_PACKAGES.bat
```

`git pull` downloads launcher and app changes. `UPDATE_PACKAGES.bat` updates the
portable runtime and every recognized virtual environment from the checked-in
requirements files. Start the launcher again after both commands finish.

Make app changes in a development clone, commit and push them, and then pull
them into other installations.

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

## Project Structure

```text
Unified-Pipeline-Launcher/
|-- apps/                       App registry and Streamlit apps
|-- INSTALL.bat                 Temporary first-time installer
|-- START_LAUNCHER.vbs          Normal no-console fallback
|-- START_LAUNCHER_DEBUG.bat    Troubleshooting launcher
|-- UPDATE_PACKAGES.bat         Python environment updater
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
