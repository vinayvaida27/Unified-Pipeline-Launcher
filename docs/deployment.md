# Deployment Guide

Goal: ship one folder that contains `launcher.exe` **and** a private Python
runtime, so non-technical users just double-click `launcher.exe` and never
install Python.

## Why a bundled runtime

The launcher runs every Streamlit app on its **own** Python. The release must
therefore carry a complete, relocatable CPython in `runtime/`.

Important: the python.org "embeddable ZIP" will **NOT** work -- it has no `pip`
and no `venv`. Use a full, relocatable build. The official **NuGet `python`
package** is the easiest correct source.

## Step 1 - Install Python into `runtime/`

From the project root in PowerShell:

```powershell
.\scripts\fetch_runtime.ps1
# or pin a specific version:
.\scripts\fetch_runtime.ps1 -Version 3.12.7
```

This downloads the official CPython NuGet package, copies it into `runtime/`,
bootstraps pip, and validates `venv` + `pip` + `ssl`. Afterwards you have:

```text
runtime/
  python.exe
  Lib/
  DLLs/
  runtime_info.json
```

If your organization provides its own approved extracted runtime, use
`.\scripts\prepare_runtime.ps1 -RuntimeSource C:\path\to\extracted-python`
instead.

## Step 2 - Build the release folder

```powershell
.\scripts\build_exe.ps1
```

This runs the tests, builds `launcher.exe` with PyInstaller, copies
`apps/`, `config/`, `assets/`, `docs/`, and `runtime/` next to it, and writes
checksums. Output:

```text
build/Unified-Streamlit-Launcher/
  launcher.exe
  runtime/python.exe
  apps/
  config/
  assets/
  docs/
  checksums.sha256
```

## Step 3 - Distribute

**Recommended: one-click installer (single Setup.exe).** This is the simplest
thing to hand a non-technical user -- one file, double-click, done. Install
NSIS once (`winget install NSIS.NSIS`), then:

```powershell
.\scripts\build_installer.ps1
```

This builds the release, verifies a bundled runtime is present, and compiles
`build\UnifiedStreamlitLauncherSetup.exe`. The installer:

- installs per-user into `%LOCALAPPDATA%\UnifiedStreamlitLauncher` (no admin
  prompt),
- creates Start Menu and Desktop shortcuts,
- registers an uninstaller in Add/Remove Programs,
- offers to launch the app on finish.

Users just double-click `UnifiedStreamlitLauncherSetup.exe`. Code-signing the
Setup.exe is recommended before wide distribution.

Other options:

**Copy the folder.** Give users the whole `build/Unified-Streamlit-Launcher/`
folder (USB, zip, or network share). They double-click `launcher.exe`.

**Network share.** Put the folder on `\\server\share\...`, read-only for
users. Many users run the same `launcher.exe`; each gets a private local cache,
runtime copy, and venvs under
`%LOCALAPPDATA%\OrganizationName\UnifiedStreamlitPlatform\`.

**Public clone / no rebuild.** For public GitHub users who already have a clone,
pull the latest files and refresh only dependencies:

```powershell
git pull --ff-only origin main
.\scripts\update_dependencies.ps1
wscript.exe .\START_LAUNCHER.vbs
```

This path does not rebuild the EXE. It updates requirements-driven libraries in
the existing bundled runtime and starts the launcher through `pythonw.exe`.

## Alternative - no bundled runtime (auto-download)

If you would rather not bundle Python in the folder, enable the download
fallback instead. The launcher will fetch a pinned official CPython into each
user's cache on first run (needs internet on first launch, no admin rights):

```powershell
.\scripts\pin_runtime_download.ps1            # downloads once, pins the SHA-256
.\scripts\build_exe.ps1
```

This sets `runtime.download.enabled = true` in `config/launcher_config.json`.
Bundling (Steps 1-2) is still preferred for offline and air-gapped sites.

## What the end user does

1. Open the folder (or run the installer).
2. Double-click `launcher.exe`.
3. Click **Open** on an app. First launch builds that app's environment
   (one-time, slower); later launches are instant.

No Python install, no PowerShell, no admin rights. A Python already installed
on the machine is never used.

## Updating libraries after adding apps

When you add a dependency, update the appropriate requirements file and refresh
the shared runtime:

```powershell
.\scripts\update_dependencies.ps1 -Target app -AppId 01_hello_pipeline -Package "package-name>=1,<2"
```

For launcher/UI packages:

```powershell
.\scripts\update_dependencies.ps1 -Target launcher -Package "package-name>=1,<2"
```

The script installs `requirements-launcher.txt` plus app requirements and then
validates `PySide6` and `streamlit`.

## Verify the "never use system Python" guarantee

On a test machine that **has** Python installed, open an app, then in Task
Manager / Process Explorer confirm every `python.exe` path is under
`%LOCALAPPDATA%\...\UnifiedStreamlitPlatform\` -- never `C:\PythonXX` or the
Microsoft Store path.
