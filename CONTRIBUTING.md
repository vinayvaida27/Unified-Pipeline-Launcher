# Contributing

Thanks for helping improve Unified Pipeline Launcher.

## Before you start

- Read [AGENTS.md](AGENTS.md) for runtime, Windows-path, and data-protection constraints.
- Use a feature branch and keep each pull request focused.
- Do not commit laboratory or patient data, credentials, private application folders, generated runtimes, or local caches.

## Development workflow

1. Create a branch from the current target branch.
2. Set up the controlled development environment with `src/scripts/setup_dev.ps1`.
3. Add or update focused regression tests with a behavior change.
4. Run the relevant tests and `src/scripts/public_quality_gate.ps1` before opening a pull request.
5. Describe the user-visible impact, validation performed, and any remaining deployment checks in the pull request.

## Pull request expectations

- Preserve Windows PowerShell 5.1 compatibility.
- Keep the local installed runtime distinct from any network source path.
- Use synthetic fixtures for tests; do not depend on corporate shares or private apps.
- Keep third-party notices and licenses intact when adding dependencies or assets.

## Community standards

By participating, you agree to follow [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
For vulnerabilities, follow [SECURITY.md](SECURITY.md) instead of opening a public issue.
