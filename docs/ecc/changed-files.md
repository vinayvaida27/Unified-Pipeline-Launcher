# Reviewed publication file list

Comparison base: `09652ff1a1426200e67c9e521c75bc24e2877455`. Branch: `ECC`.

This is the explicit 53-file source/documentation list prepared for staging. No application directory, registry, data, runtime binary, generated log, or audit artifact is included.

| File | Reason |
|---|---|
| `.claude/rules/common/security.md` | Adapt ECC common/Python workflow guidance and reference AGENTS.md. |
| `.claude/rules/common/workflow.md` | Adapt ECC common/Python workflow guidance and reference AGENTS.md. |
| `.claude/rules/python/testing.md` | Adapt ECC common/Python workflow guidance and reference AGENTS.md. |
| `.codex/config.toml` | Disable ECC's unnecessary unpinned browser MCP for this project. |
| `.github/workflows/ci.yml` | Separate controlled unit/Qt, Windows, browser, and security gates; include ECC. |
| `.gitignore` | Track intended ECC rules/reports and ignore generated verification output. |
| `AGENTS.md` | Authoritative startup, uv, data, network, recovery and evidence requirements. |
| `CLAUDE.md` | Reference authoritative project instructions. |
| `README.md` | Describe tested startup and guarded maintenance/verification workflows. |
| `START_LAUNCHER.bat` | Canonical validated startup, isolated probes, safe paths and true exit status. |
| `START_LAUNCHER.vbs` | Delegate through explicit cmd invocation and report failures. |
| `START_LAUNCHER_DEBUG.bat` | Delegate debug mode to the canonical entrypoint. |
| `docs/ecc/changed-files.md` | Record the plan, reviewed manifest, executed release evidence or separate security review. |
| `docs/ecc/implementation-plan.md` | Record the plan, reviewed manifest, executed release evidence or separate security review. |
| `docs/ecc/release-report.md` | Record the plan, reviewed manifest, executed release evidence or separate security review. |
| `docs/ecc/security-review.md` | Record the plan, reviewed manifest, executed release evidence or separate security review. |
| `src/build_scripts/build.py` | Include canonical startup and runtime support files in portable releases. |
| `src/launcher/app_discovery.py` | Allow missing icon files to reach the UI fallback while preserving path/schema validation. |
| `src/launcher/environment_manager.py` | Validate executable/stdlib/prefix confinement and scrub inherited Python settings. |
| `src/launcher/local_cache.py` | Stage, validate, lock, retain previous cache and recover failed activation. |
| `src/launcher/main.py` | Keep startup I/O responsive, validate every runtime path, surface errors and log timings. |
| `src/launcher/process_manager.py` | Protect replacement processes and unrelated processes during races and cleanup. |
| `src/launcher/runtime_downloader.py` | Confine versions/paths, reject unsafe archives, isolate staging and preserve existing installs. |
| `src/launcher/ui/app_card.py` | Use the shared warning-aware SVG renderer and existing letter fallback. |
| `src/launcher/ui/svg.py` | Detect partly accepted SVG warnings and emit bounded actionable fallback logging. |
| `src/launcher/update_manager.py` | Confine releases and cached markers, reject aliases and preserve installed versions. |
| `src/pyproject.toml` | Pin optional development verification tools and declare acceptance markers. |
| `src/scripts/check_svg_icons.py` | Scan actual registered/launcher assets through Qt warning-aware validation. |
| `src/scripts/common.ps1` | Provide confined staging, target lock, validation and rollback helpers. |
| `src/scripts/deploy_network.ps1` | Use a literal working directory for source-import validation. |
| `src/scripts/fetch_runtime.ps1` | Validate official standalone Python in staging before activation. |
| `src/scripts/generate_checksums.ps1` | Use the Windows PowerShell 5.1 relative-path helper. |
| `src/scripts/prepare_shared_runtime.ps1` | Prepare and repair the selected runtime in staging, preserving console entrypoints. |
| `src/scripts/public_quality_gate.ps1` | Require controlled Python, validate registered SVGs and parse PS5.1-compatible scripts. |
| `src/scripts/update_all_environments.ps1` | Remove automatic destructive venv clearing; keep explicit copy mode. |
| `src/scripts/verify_release.ps1` | Verify canonical wrappers/support files with literal paths. |
| `src/tests/test_app_discovery.py` | Behavioral regression coverage or current workflow assertions for the corresponding change. |
| `src/tests/test_build_environment.py` | Reject inherited foreign DLL paths and Python options in the PyInstaller subprocess. |
| `src/tests/test_build_scripts.py` | Behavioral regression coverage or current workflow assertions for the corresponding change. |
| `src/tests/test_config_loader.py` | Behavioral regression coverage or current workflow assertions for the corresponding change. |
| `src/tests/test_environment_manager.py` | Behavioral regression coverage or current workflow assertions for the corresponding change. |
| `src/tests/test_local_cache.py` | Behavioral regression coverage or current workflow assertions for the corresponding change. |
| `src/tests/test_native_startup.py` | Behavioral regression coverage or current workflow assertions for the corresponding change. |
| `src/tests/test_powershell_runtime_updates.py` | Behavioral regression coverage or current workflow assertions for the corresponding change. |
| `src/tests/test_process_manager.py` | Behavioral regression coverage or current workflow assertions for the corresponding change. |
| `src/tests/test_public_workflow.py` | Behavioral regression coverage or current workflow assertions for the corresponding change. |
| `src/tests/test_runtime_integration.py` | Behavioral regression coverage or current workflow assertions for the corresponding change. |
| `src/tests/test_startup_progress.py` | Behavioral regression coverage or current workflow assertions for the corresponding change. |
| `src/tests/test_svg_reliability.py` | Behavioral regression coverage or current workflow assertions for the corresponding change. |
| `src/tests/test_update_manager.py` | Behavioral regression coverage or current workflow assertions for the corresponding change. |
| `src/tests/test_update_security.py` | Behavioral regression coverage or current workflow assertions for the corresponding change. |
| `src/tests/test_windows_entrypoints.py` | Behavioral regression coverage or current workflow assertions for the corresponding change. |
| `src/uv.lock` | Lock verification tools; preserve all existing package versions. |
