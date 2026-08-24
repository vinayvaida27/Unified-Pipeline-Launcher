from __future__ import annotations

import os
import sys
import time
from dataclasses import replace
from pathlib import Path

import pytest


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from launcher.environment_manager import EnvironmentManager
from launcher.models import ApplicationManifest, ApplicationStatus, LaunchSettings
from launcher.process_manager import ProcessManager
from launcher.ui.main_window import MainWindow


pytestmark = [pytest.mark.integration, pytest.mark.e2e]


@pytest.fixture(scope="session")
def qt_app():
    return QApplication.instance() or QApplication([])


def _fixture_app(tmp_path: Path, app_id: str, label: str) -> ApplicationManifest:
    app_dir = tmp_path / app_id
    app_dir.mkdir()
    entrypoint = app_dir / "app.py"
    entrypoint.write_text(
        f"""import os
import sys
from pathlib import Path

import streamlit as st

st.title('{label}')
st.text(f'App ID: {app_id}')
st.text(f'PID: {{os.getpid()}}')
st.text(f'Executable: {{sys.executable}}')
st.text(f'CWD: {{Path.cwd()}}')
st.text(f'PYTHONNOUSERSITE: {{os.environ.get("PYTHONNOUSERSITE")}}')
if 'count' not in st.session_state:
    st.session_state.count = 0
if st.button('Increment {label}'):
    st.session_state.count += 1
st.text(f'Count: {{st.session_state.count}}')
""",
        encoding="utf-8",
    )
    icon = app_dir / "icon.svg"
    icon.write_text("<svg xmlns='http://www.w3.org/2000/svg'/>", encoding="utf-8")
    requirements = app_dir / "requirements.txt"
    requirements.write_text("streamlit>=1.40,<2\n", encoding="utf-8")
    return ApplicationManifest(
        schema_version=1,
        id=app_id,
        name=label,
        version="1.0.0",
        description=f"Master audit fixture {label}",
        category="Master",
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


def _wait_for(qt_app, predicate, message: str, timeout: float = 20):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        qt_app.processEvents()
        value = predicate()
        if value:
            return value
        QTest.qWait(25)
    pytest.fail(message)


def test_qt_open_all_browser_restart_stop_and_cleanup(qt_app, config, tmp_path):
    playwright = pytest.importorskip("playwright.sync_api")
    behavior = replace(config.launcher, open_browser_after_start=False, maximum_parallel_startups=2)
    config = replace(config, launcher=behavior)
    apps = [
        _fixture_app(tmp_path, "master-a", "Master App A"),
        _fixture_app(tmp_path, "master-b", "Master App B"),
    ]
    process_manager = ProcessManager(tmp_path / "logs")
    window = MainWindow(config, apps, EnvironmentManager(config, Path(sys.executable)), process_manager)
    window.show()

    try:
        window.search.setText("Master App A")
        qt_app.processEvents()
        assert window.cards["master-a"].isVisible()
        assert not window.cards["master-b"].isVisible()
        window.search.clear()
        qt_app.processEvents()

        open_all = next(button for button in window.findChildren(type(window.cards["master-a"].open_button)) if button.text() == "Open All")
        QTest.mouseClick(open_all, Qt.MouseButton.LeftButton)
        states = _wait_for(
            qt_app,
            lambda: [process_manager.get(app.id) for app in apps]
            if all(
                process_manager.get(app.id)
                and process_manager.get(app.id).status == ApplicationStatus.RUNNING
                and app.id not in window._starting_ids
                for app in apps
            )
            else None,
            "Open All did not launch both apps",
        )
        assert states[0].process_id != states[1].process_id
        assert states[0].port != states[1].port

        with playwright.sync_playwright() as runtime:
            browser = runtime.chromium.launch(headless=True)
            context = browser.new_context()
            pages = []
            for app, state in zip(apps, states, strict=True):
                page = context.new_page()
                page.goto(state.url)
                playwright.expect(page.get_by_role("heading", name=app.name)).to_be_visible(timeout=15_000)
                playwright.expect(page.get_by_text(f"App ID: {app.id}", exact=True)).to_be_visible()
                playwright.expect(page.get_by_text("PYTHONNOUSERSITE: 1", exact=True)).to_be_visible()
                pages.append(page)

            pages[0].get_by_role("button", name="Increment Master App A").click()
            playwright.expect(pages[0].get_by_text("Count: 1", exact=True)).to_be_visible()
            playwright.expect(pages[1].get_by_text("Count: 0", exact=True)).to_be_visible()

            first_generation = process_manager.get("master-a")
            QTest.mouseClick(window.cards["master-a"].restart_button, Qt.MouseButton.LeftButton)
            restarted = _wait_for(
                qt_app,
                lambda: process_manager.get("master-a")
                if process_manager.get("master-a")
                and process_manager.get("master-a").status == ApplicationStatus.RUNNING
                and process_manager.get("master-a").process_id != first_generation.process_id
                else None,
                "Restart did not produce a new running generation",
            )
            restart_page = context.new_page()
            restart_page.goto(restarted.url)
            playwright.expect(restart_page.get_by_role("heading", name="Master App A")).to_be_visible(timeout=15_000)
            playwright.expect(restart_page.get_by_text("Count: 0", exact=True)).to_be_visible()

            QTest.mouseClick(window.cards["master-a"].stop_button, Qt.MouseButton.LeftButton)
            _wait_for(qt_app, lambda: process_manager.get("master-a") is None, "Stop did not remove App A")
            assert process_manager.get("master-b").process.poll() is None
            pages[1].get_by_role("button", name="Increment Master App B").click()
            playwright.expect(pages[1].get_by_text("Count: 1", exact=True)).to_be_visible()

            with pytest.raises(playwright.Error):
                restart_page.goto(restarted.url, wait_until="domcontentloaded", timeout=2_000)

            stop_all = next(button for button in window.findChildren(type(window.cards["master-a"].open_button)) if button.text() == "Stop All")
            QTest.mouseClick(stop_all, Qt.MouseButton.LeftButton)
            _wait_for(qt_app, lambda: not process_manager.running_states(), "Stop All left a tracked process")
            assert all(process_manager.port_manager.is_available(state.port) for state in states)
            assert process_manager.port_manager.is_available(restarted.port)
            browser.close()
    finally:
        window.stop_all_apps()
        assert window.thread_pool.waitForDone(5_000)
        window.close()
        window.deleteLater()
        qt_app.processEvents()
