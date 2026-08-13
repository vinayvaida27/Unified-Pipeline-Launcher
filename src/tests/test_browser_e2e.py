from __future__ import annotations

import sys
from pathlib import Path

import pytest

from launcher.models import ApplicationManifest, EnvironmentState, LaunchSettings
from launcher.process_manager import ProcessManager


pytestmark = [pytest.mark.integration, pytest.mark.e2e]


def _app(tmp_path: Path, app_id: str, source: str) -> ApplicationManifest:
    app_dir = tmp_path / app_id
    app_dir.mkdir()
    entrypoint = app_dir / "app.py"
    entrypoint.write_text(source, encoding="utf-8")
    icon = app_dir / "icon.svg"
    icon.write_text("<svg xmlns='http://www.w3.org/2000/svg'/>", encoding="utf-8")
    requirements = app_dir / "requirements.txt"
    requirements.write_text("streamlit>=1.40,<2\n", encoding="utf-8")
    return ApplicationManifest(
        schema_version=1,
        id=app_id,
        name=app_id,
        version="1.0.0",
        description="Browser fixture",
        category="Test",
        type="streamlit",
        entrypoint=entrypoint,
        icon=icon,
        requirements=requirements,
        wheelhouse=app_dir / "wheelhouse",
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}",
        enabled=True,
        display_order=1,
        launch=LaunchSettings("127.0.0.1", "dynamic", True, "none", False, 20),
        app_dir=app_dir,
    )


def _environment(tmp_path: Path, app: ApplicationManifest) -> EnvironmentState:
    python = Path(sys.executable)
    return EnvironmentState(app.id, app.version, python.parent, python, True, tmp_path / "ready.json")


@pytest.mark.parametrize("browser_name", ["chromium", "firefox", "webkit"])
def test_streamlit_widgets_rerun_refresh_and_error_rendering(tmp_path, browser_name):
    playwright = pytest.importorskip("playwright.sync_api")
    interactive = _app(
        tmp_path,
        "interactive-app",
        """import streamlit as st

st.title('Interactive fixture')
if 'count' not in st.session_state:
    st.session_state.count = 0
name = st.text_input('Name')
if st.button('Increment'):
    st.session_state.count += 1
st.write(f'Hello {name or "stranger"}')
st.write(f'Count: {st.session_state.count}')
""",
    )
    broken = _app(tmp_path, "broken-app", "import definitely_missing_audit_package\n")
    manager = ProcessManager(tmp_path / "logs")

    try:
        interactive_state = manager.start(interactive, _environment(tmp_path, interactive))
        broken_state = manager.start(broken, _environment(tmp_path, broken))
        with playwright.sync_playwright() as runtime:
            browser = getattr(runtime, browser_name).launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 900})
            page = context.new_page()
            page.goto(interactive_state.url)
            playwright.expect(page.get_by_role("heading", name="Interactive fixture")).to_be_visible(timeout=15_000)

            name_input = page.get_by_role("textbox", name="Name")
            name_input.fill("Ada")
            name_input.press("Enter")
            playwright.expect(page.get_by_text("Hello Ada", exact=True)).to_be_visible()
            page.get_by_role("button", name="Increment").click()
            playwright.expect(page.get_by_text("Count: 1", exact=True)).to_be_visible()

            page.reload()
            playwright.expect(page.get_by_role("heading", name="Interactive fixture")).to_be_visible(timeout=15_000)
            playwright.expect(page.get_by_text("Count: 0", exact=True)).to_be_visible()

            error_page = context.new_page()
            error_page.goto(broken_state.url)
            playwright.expect(error_page.get_by_text("ModuleNotFoundError", exact=False)).to_be_visible(timeout=15_000)
            browser.close()
    finally:
        manager.stop_all()


@pytest.mark.xfail(strict=True, reason="ProcessManager stops only the direct Streamlit process")
def test_stopping_streamlit_also_stops_its_nested_child(tmp_path):
    playwright = pytest.importorskip("playwright.sync_api")
    psutil = pytest.importorskip("psutil")
    app = _app(
        tmp_path,
        "nested-child-app",
        """import subprocess
import sys
from pathlib import Path

import streamlit as st

pid_file = Path('nested-child.pid')
if not pid_file.exists():
    child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'])
    pid_file.write_text(str(child.pid), encoding='ascii')
st.title('Nested child fixture')
""",
    )
    manager = ProcessManager(tmp_path / "logs")
    child_pid = None

    try:
        state = manager.start(app, _environment(tmp_path, app))
        with playwright.sync_playwright() as runtime:
            browser = runtime.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(state.url)
            playwright.expect(page.get_by_role("heading", name="Nested child fixture")).to_be_visible(timeout=15_000)
            child_pid = int((app.app_dir / "nested-child.pid").read_text(encoding="ascii"))
            browser.close()

        manager.stop(app.id, timeout_seconds=3)

        nested = psutil.Process(child_pid)
        assert not nested.is_running()
    finally:
        manager.stop_all()
        if child_pid and psutil.pid_exists(child_pid):
            nested = psutil.Process(child_pid)
            nested.kill()
            nested.wait(timeout=5)


def test_apps_keep_local_import_identity_but_inherit_unfiltered_environment(tmp_path, monkeypatch):
    playwright = pytest.importorskip("playwright.sync_api")
    monkeypatch.setenv("LAUNCHER_AUDIT_SECRET", "visible-to-child")
    source = """import os
import sys
from pathlib import Path

import identity
import streamlit as st

st.title(f'Identity {identity.VALUE}')
st.text(f'Executable: {sys.executable}')
st.text(f'CWD: {Path.cwd()}')
st.text(f'Secret: {os.environ.get("LAUNCHER_AUDIT_SECRET")}')
"""
    first = _app(tmp_path, "identity-a", source)
    second = _app(tmp_path, "identity-b", source)
    (first.app_dir / "identity.py").write_text("VALUE = 'A'\n", encoding="utf-8")
    (second.app_dir / "identity.py").write_text("VALUE = 'B'\n", encoding="utf-8")
    manager = ProcessManager(tmp_path / "logs")

    try:
        first_state = manager.start(first, _environment(tmp_path, first))
        second_state = manager.start(second, _environment(tmp_path, second))
        with playwright.sync_playwright() as runtime:
            browser = runtime.chromium.launch(headless=True)
            for app, state, identity in ((first, first_state, "A"), (second, second_state, "B")):
                page = browser.new_page()
                page.goto(state.url)
                playwright.expect(page.get_by_role("heading", name=f"Identity {identity}")).to_be_visible(
                    timeout=15_000
                )
                playwright.expect(page.get_by_text(f"Executable: {sys.executable}", exact=True)).to_be_visible()
                playwright.expect(page.get_by_text(f"CWD: {app.app_dir}", exact=True)).to_be_visible()
                playwright.expect(page.get_by_text("Secret: visible-to-child", exact=True)).to_be_visible()
            browser.close()
    finally:
        manager.stop_all()


def test_child_crash_is_contained_and_untracked(tmp_path):
    playwright = pytest.importorskip("playwright.sync_api")
    app = _app(tmp_path, "crash-app", "import os\nos._exit(7)\n")
    manager = ProcessManager(tmp_path / "logs")

    try:
        state = manager.start(app, _environment(tmp_path, app))
        with playwright.sync_playwright() as runtime:
            browser = runtime.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(state.url)
            page.wait_for_timeout(1_000)
            browser.close()
        state.process.wait(timeout=10)
        assert state.process.returncode == 7
        assert manager.get(app.id) is None
    finally:
        manager.stop_all()


def test_large_stdout_and_stderr_do_not_deadlock_the_app(tmp_path):
    playwright = pytest.importorskip("playwright.sync_api")
    app = _app(
        tmp_path,
        "large-output-app",
        """import sys

import streamlit as st

print('O' * (2 * 1024 * 1024), flush=True)
print('E' * (2 * 1024 * 1024), file=sys.stderr, flush=True)
st.title('Large output survived')
""",
    )
    manager = ProcessManager(tmp_path / "logs")

    try:
        state = manager.start(app, _environment(tmp_path, app))
        with playwright.sync_playwright() as runtime:
            browser = runtime.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(state.url)
            playwright.expect(page.get_by_role("heading", name="Large output survived")).to_be_visible(
                timeout=15_000
            )
            browser.close()
        assert state.log_path.stat().st_size >= 4 * 1024 * 1024
        assert state.process.poll() is None
    finally:
        manager.stop_all()


def test_hung_streamlit_script_can_still_be_stopped(tmp_path):
    playwright = pytest.importorskip("playwright.sync_api")
    app = _app(
        tmp_path,
        "hung-app",
        """import time

while True:
    time.sleep(1)
""",
    )
    manager = ProcessManager(tmp_path / "logs")

    try:
        state = manager.start(app, _environment(tmp_path, app))
        with playwright.sync_playwright() as runtime:
            browser = runtime.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(state.url)
            page.wait_for_timeout(1_000)
            assert state.process.poll() is None
            browser.close()

        manager.stop(app.id, timeout_seconds=3)

        assert state.process.poll() is not None
        assert manager.get(app.id) is None
    finally:
        manager.stop_all()
