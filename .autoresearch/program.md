# Public Improvement Program

This project uses an autoresearch-style loop for public-facing launcher work:

1. Pick one small hypothesis from `.autoresearch/backlog.md` or create one.
2. Change the smallest set of files needed to test it.
3. Run the fixed quality gate:

```powershell
.\scripts\public_quality_gate.ps1
```

4. Keep the change only when the quality gate passes. Revert or revise failures.
5. Record the outcome in `.autoresearch/results.tsv` with the tested command and evidence path.

## Public Release Targets

Every accepted change should preserve these public-use guarantees:

- A new user can clone the repository, prepare the runtime, and start the launcher without installing system Python packages manually.
- A nontechnical user can open the launcher without seeing a console window.
- App and launcher dependencies are declared in requirements files, never installed by hand as hidden state.
- The launcher must pass tests on Python 3.11 and 3.12 on Windows.
- Release and network-deploy scripts must validate `PySide6` and `streamlit` after dependency installation.

## Dependency Rule

When a change adds or updates a Python library:

- Launcher/UI libraries go in `requirements-launcher.txt`.
- Per-app libraries go in that app's `requirements.txt`.
- Development-only tools go in `requirements-dev.txt` or `requirements-build.txt`.
- Then run:

```powershell
.\scripts\update_dependencies.ps1
```

For a single new package, prefer:

```powershell
.\scripts\update_dependencies.ps1 -Target launcher -Package "package-name>=1,<2"
.\scripts\update_dependencies.ps1 -Target app -AppId 01_hello_pipeline -Package "package-name>=1,<2"
```

Do not commit `runtime/`, `.venv/`, build output, logs, or `.autoresearch/evidence/`.
