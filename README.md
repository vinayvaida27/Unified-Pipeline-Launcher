# Unified Streamlit Launcher

Windows desktop launcher for many independent Streamlit apps.

The important idea is simple:

- `launcher/` is the reusable desktop framework.
- `apps/` contains Streamlit applications.
- `apps/apps.json` is the only app registry people normally edit.
- `build/Unified-Streamlit-Launcher/` is the generated folder you give to users.

Nontechnical users should run the built `launcher.exe`. They should not install Python, run PowerShell, or edit launcher code.

## Repository Layout

```text
Unified-Streamlit-Launcher/
  launcher/                 # Core PySide6 launcher framework
  apps/                     # Streamlit apps and central registry
    apps.json
    app_template/
    01_hello_pipeline/
    02_second_app/
  config/                   # Global launcher config
    launcher_config.json
    platform_manifest.json
  runtime/                  # Portable Python runtime for production builds
  scripts/                  # Setup/build/release scripts
  build/                    # Generated releases
  docs/                     # User and deployment documentation
  tests/
```

## Developer Quickstart

Use Windows PowerShell:

```powershell
.\scripts\setup_dev.ps1
.\scripts\run_launcher_dev.ps1
```

Development requires Python 3.11 or 3.12. The dev launcher can use the local interpreter while production builds use `runtime/python.exe`.

## Build The EXE Release

1. Prepare or copy an approved portable Python runtime into `runtime/`.
2. Run:

```powershell
.\scripts\build_exe.ps1
```

Output:

```text
build/Unified-Streamlit-Launcher/
  launcher.exe
  config/
  apps/
  assets/
  runtime/
  docs/
```

Users can copy that folder and double-click `launcher.exe`.

The same folder can be published on a network drive. On startup, the bundled runtime and registered app folders are copied into each user's local cache before Streamlit starts, so apps are centrally distributed but locally executed.

## Public Clone Quickstart

For public GitHub use without rebuilding an EXE:

```powershell
git clone https://github.com/vinayvaida27/Unified-Streamlit-Launcher.git
cd Unified-Streamlit-Launcher
git checkout main

.\scripts\fetch_runtime.ps1
.\scripts\update_dependencies.ps1
wscript.exe .\START_LAUNCHER.vbs
```

To pull updates later without rebuilding from scratch:

```powershell
git pull --ff-only origin main
.\scripts\update_dependencies.ps1
wscript.exe .\START_LAUNCHER.vbs
```

## Add Apps After Building

The apps are external to the executable. After a release is built, you can add or replace apps in the release folder:

```text
build/Unified-Streamlit-Launcher/apps/
  apps.json
  my_new_app/
    app.py
    requirements.txt
    README.md
    assets/icon.svg
```

Then add the app to `apps/apps.json` and restart `launcher.exe`.

## Updating Python Libraries

Requirements files are the source of truth. Do not rely on manual `pip install`
commands that only affect one machine.

Add or update a launcher dependency:

```powershell
.\scripts\update_dependencies.ps1 -Target launcher -Package "package-name>=1,<2"
```

Add or update an app dependency:

```powershell
.\scripts\update_dependencies.ps1 -Target app -AppId 01_hello_pipeline -Package "package-name>=1,<2"
```

Refresh everything already declared:

```powershell
.\scripts\update_dependencies.ps1
```

## Documentation

- [Quickstart](docs/quickstart.md)
- [Build EXE](docs/BUILD.md)
- [Creating apps](docs/creating_apps.md)
- [App development](docs/APP_DEVELOPMENT.md)
- [Deployment](docs/deployment.md)
- [Public release workflow](docs/public_release.md)
- [Release process](docs/release_process.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Architecture](docs/architecture.md)

## Validation

```powershell
.\scripts\public_quality_gate.ps1
```

The framework includes tests for config loading, app registry validation, path security, environment paths, process launch commands, health checks, dependency update wiring, and public release checks.
