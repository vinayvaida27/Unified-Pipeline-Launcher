from __future__ import annotations


def test_update_dependencies_refreshes_shared_runtime(source_root):
    script = (source_root / "scripts" / "update_dependencies.ps1").read_text(encoding="utf-8")

    assert "requirements-launcher.txt" in script
    assert 'Join-Path $ReleaseSourceRoot "apps"' in script
    assert 'Join-Path $AppsRoot "apps.json"' in script
    assert "prepare_shared_runtime.ps1" in script
    assert "fetch_runtime.ps1" in script


def test_public_quality_gate_checks_dependency_workflow(source_root):
    script = (source_root / "scripts" / "public_quality_gate.ps1").read_text(encoding="utf-8")

    assert "pytest" in script
    assert "compileall" in script
    assert "requirements-launcher.txt" in script
    assert "prepare_shared_runtime.ps1" in script
    assert "create_launcher_shortcut.ps1" in script


def test_ci_runs_supported_windows_python_versions(source_root):
    workflow = (source_root.parent / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "windows-latest" in workflow
    assert '"3.11"' in workflow
    assert '"3.12"' in workflow
    assert "requirements-dev.txt" in workflow
    assert "public_quality_gate.ps1" in workflow


def test_public_readme_explains_no_rebuild_update(repo_root):
    readme = (repo_root / "README.md").read_text(encoding="utf-8")

    assert "git pull --ff-only origin main" in readme
    assert "update_dependencies.ps1" in readme
    assert "START_LAUNCHER.lnk" in readme


def test_only_approved_root_markdown_is_tracked(repo_root):
    import subprocess

    result = subprocess.run(
        ["git", "ls-files", "--", ":(top,glob)*.md"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )

    assert set(result.stdout.splitlines()) <= {"README.md", "TEST_AUDIT.md"}
