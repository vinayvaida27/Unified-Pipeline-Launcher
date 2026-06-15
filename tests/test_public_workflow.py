from __future__ import annotations


def test_update_dependencies_refreshes_shared_runtime(repo_root):
    script = (repo_root / "scripts" / "update_dependencies.ps1").read_text(encoding="utf-8")

    assert "requirements-launcher.txt" in script
    assert "apps\\apps.json" in script
    assert "prepare_shared_runtime.ps1" in script
    assert "fetch_runtime.ps1" in script


def test_public_quality_gate_checks_dependency_workflow(repo_root):
    script = (repo_root / "scripts" / "public_quality_gate.ps1").read_text(encoding="utf-8")

    assert "pytest" in script
    assert "compileall" in script
    assert "CONTRIBUTING.md" in script
    assert "prepare_shared_runtime.ps1" in script


def test_ci_runs_supported_windows_python_versions(repo_root):
    workflow = (repo_root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "windows-latest" in workflow
    assert '"3.11"' in workflow
    assert '"3.12"' in workflow
    assert "requirements-dev.txt" in workflow
    assert "public_quality_gate.ps1" in workflow


def test_autoresearch_program_defines_keep_or_revise_gate(repo_root):
    program = (repo_root / ".autoresearch" / "program.md").read_text(encoding="utf-8")

    assert "public_quality_gate.ps1" in program
    assert "Keep the change only when the quality gate passes" in program
    assert "update_dependencies.ps1" in program


def test_public_docs_explain_no_rebuild_update(repo_root):
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    public_doc = (repo_root / "docs" / "public_release.md").read_text(encoding="utf-8")

    assert "git pull --ff-only origin main" in readme
    assert "update_dependencies.ps1" in readme
    assert "does not rebuild the EXE" in public_doc
