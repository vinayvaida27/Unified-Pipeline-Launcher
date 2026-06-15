# Contributing

Thanks for helping improve Unified Streamlit Launcher. The project is designed
so public contributors can make small, testable changes without requiring users
to install Python packages manually.

## Development Setup

Use Windows PowerShell:

```powershell
.\scripts\setup_dev.ps1
.\scripts\run_launcher_dev.ps1
```

Run the public quality gate before opening a pull request:

```powershell
.\scripts\public_quality_gate.ps1
```

## Adding Python Libraries

Do not install packages by hand and leave the requirements files unchanged.
Every dependency must be declared so other users and the bundled runtime can be
updated repeatably.

Launcher or UI dependency:

```powershell
.\scripts\update_dependencies.ps1 -Target launcher -Package "package-name>=1,<2"
```

App dependency:

```powershell
.\scripts\update_dependencies.ps1 -Target app -AppId 01_hello_pipeline -Package "package-name>=1,<2"
```

To reinstall and validate everything already declared:

```powershell
.\scripts\update_dependencies.ps1
```

The script installs `requirements-launcher.txt` plus every enabled app's
`requirements.txt` into `runtime\`, then validates `PySide6` and `streamlit`.

## Pull Request Checklist

- Keep changes small and focused.
- Add or update tests when behavior changes.
- Run `.\scripts\public_quality_gate.ps1`.
- Do not commit `.venv/`, `runtime/`, `build/`, logs, or `.autoresearch/evidence/`.
- Update docs when the public setup, app registry, or dependency flow changes.
