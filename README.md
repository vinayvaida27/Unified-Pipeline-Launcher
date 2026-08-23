# Unified Streamlit Launcher

A Windows launcher for sharing many Streamlit apps from one clean folder.

The public folder is intentionally simple:

```text
Unified-Streamlit-Launcher/
  README.md
  LICENSE
  INSTALL.bat
  UPDATE_PACKAGES.bat
  START_LAUNCHER.vbs
  START_LAUNCHER_DEBUG.bat
  apps/
  src/
```

Most users only need the installer, launcher shortcut, package updater, and
`apps/`. The implementation, configuration, tests, and runtime live in `src/`.

## Install On A New System

After cloning the repository, double-click:

```text
INSTALL.bat
```

It downloads the bundled Python runtime when needed, installs launcher and app
packages, creates `START_LAUNCHER.lnk`, and opens the application. The installer
deletes `INSTALL.bat` only after a successful installation. It keeps the file
after a failure so the installation can be retried. Reusable maintenance files
under `src/scripts/` remain because the package updater depends on them.

## Start The Launcher

Double-click:

```text
START_LAUNCHER.vbs
```

This starts with no command window. Network-drive installations automatically
cache the prepared Python runtime and app files under `%LOCALAPPDATA%`; later
launches use the matching local runtime instead of importing packages across
the network.

Apps open in a Microsoft Edge Guest window with extensions disabled. Streamlit
listens only on `127.0.0.1` with CORS and XSRF protection enabled. Closing the
launcher stops the complete app process tree, and the next launch removes any
identity-matched process left by an earlier crash.

For troubleshooting only, use:

```text
START_LAUNCHER_DEBUG.bat
```

## Apps Folder

All user-facing Streamlit apps live in:

```text
apps/
```

Each app is a normal folder:

```text
apps/
  my_new_app/
    app.py
    requirements.txt
    assets/
      icon.svg
```

The launcher reads `apps/apps.json` to know which apps to show.

## Create A New App

1. Copy the template folder:

```powershell
Copy-Item -Recurse .\apps\app_template .\apps\my_new_app
```

2. Edit the app:

```text
apps/my_new_app/app.py
```

Your `app.py` can be any Streamlit app:

```python
import streamlit as st

st.title("My New App")
st.write("Hello from the Unified Streamlit Launcher.")
```

3. Add Python libraries in:

```text
apps/my_new_app/requirements.txt
```

Example:

```text
streamlit>=1.40,<2
pandas>=2.2,<3
plotly>=5,<6
```

4. Add an icon:

```text
apps/my_new_app/assets/icon.svg
```

You can also reuse an existing icon while testing.

## Register The App

Open:

```text
apps/apps.json
```

Add a new entry to the `applications` list:

```json
{
  "id": "my-new-app",
  "name": "My New App",
  "folder": "my_new_app",
  "description": "Short description shown in the launcher.",
  "category": "General",
  "version": "1.0.0",
  "display_order": 11,
  "enabled": true,
  "icon": "assets/icon.svg"
}
```

Important fields:

- `id`: stable unique app id, lowercase letters, numbers, and dashes.
- `name`: label users see in the launcher.
- `folder`: folder name under `apps/`.
- `description`: one sentence for the app card.
- `category`: grouping/filter label.
- `version`: bump this when dependencies or app behavior changes.
- `display_order`: sort order in the launcher.
- `enabled`: set `false` to hide the app without deleting it.
- `icon`: path inside the app folder.

Restart the launcher after editing `apps/apps.json`.

## Update Python Libraries

When you add or change libraries, update requirements and refresh the bundled
runtime. Do not rely on manual `pip install` commands.

For an app dependency:

```powershell
.\src\scripts\update_dependencies.ps1 -Target app -AppId my_new_app -Package "plotly>=5,<6"
```

For launcher/UI dependencies:

```powershell
.\src\scripts\update_dependencies.ps1 -Target launcher -Package "package-name>=1,<2"
```

To reinstall everything already listed in requirements files:

```text
UPDATE_PACKAGES.bat
```

Close the launcher before running it. The updater upgrades the shared runtime
and every recognized repository or per-app virtual environment, then runs
`pip check` and verifies that Streamlit imports successfully. It continues
checking the remaining environments if one fails and reports all failures.

## Pull Updates Without Rebuilding

On a machine that already has the repository:

```powershell
git pull --ff-only origin main
.\UPDATE_PACKAGES.bat
.\src\scripts\create_launcher_shortcut.ps1
```

Users can then double-click:

```text
START_LAUNCHER.lnk
```

or:

```text
START_LAUNCHER.vbs
```

## App Checklist

Before sharing a new app:

- The folder is under `apps/`.
- `app.py` runs with Streamlit.
- `requirements.txt` lists every needed library.
- `assets/icon.svg` exists.
- `apps/apps.json` has a unique `id`.
- The app opens from the launcher.

## Source Code

Source code and maintainer tools live in `src/`. Regular app authors do not
need to edit those files unless they are changing the launcher itself.
