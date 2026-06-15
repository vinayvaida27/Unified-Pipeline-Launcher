# Security Policy

## Supported Versions

Public security fixes target the `main` branch.

## Reporting a Vulnerability

Please open a private security advisory on GitHub if available. If that is not
available, open an issue with a minimal description and avoid posting secrets,
tokens, private paths, or patient/user data.

## Dependency Updates

Python dependencies are updated through requirements files and
`scripts\update_dependencies.ps1`. This keeps the bundled runtime reproducible
and prevents hidden manual `pip install` state.

For security updates:

```powershell
.\scripts\update_dependencies.ps1 -Target launcher -Package "package-name>=fixed-version,<next-major"
.\scripts\public_quality_gate.ps1
```
