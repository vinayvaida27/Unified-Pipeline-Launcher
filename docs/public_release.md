# Public Release Workflow

This workflow is for a public GitHub repository where users may clone the
project, pull updates, and run the launcher without rebuilding the EXE.

## First-Time Setup

```powershell
git clone https://github.com/vinayvaida27/Unified-Streamlit-Launcher.git
cd Unified-Streamlit-Launcher
git checkout main

.\scripts\fetch_runtime.ps1
.\scripts\update_dependencies.ps1
wscript.exe .\START_LAUNCHER.vbs
```

`START_LAUNCHER.vbs` starts `runtime\pythonw.exe -m launcher` without a visible
console window.

## Pulling Updates Without Rebuilding

```powershell
cd "D:\pythonProject\HRI\Streamlit_Launcher"
git checkout main
git pull --ff-only origin main

.\scripts\update_dependencies.ps1
wscript.exe .\START_LAUNCHER.vbs
```

This updates only the changed files and refreshes Python libraries declared in
the requirements files. It does not rebuild the EXE or recreate the repository.

## Adding or Updating Libraries

Launcher dependency:

```powershell
.\scripts\update_dependencies.ps1 -Target launcher -Package "PySide6>=6.7,<7"
```

App dependency:

```powershell
.\scripts\update_dependencies.ps1 -Target app -AppId 01_hello_pipeline -Package "streamlit>=1.40,<2"
```

The script updates the correct requirements file, installs launcher and app
dependencies into `runtime\`, and validates:

```powershell
runtime\python.exe -c "from PySide6.QtWidgets import QApplication; import streamlit"
```

## Public Improvement Loop

Use the autoresearch-style loop in `.autoresearch\program.md`:

1. Pick one small improvement hypothesis.
2. Make the smallest useful change.
3. Run `.\scripts\public_quality_gate.ps1`.
4. Keep the change only if the gate passes.
5. Record the result in `.autoresearch\results.tsv`.
