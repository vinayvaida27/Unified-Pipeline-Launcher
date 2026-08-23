from __future__ import annotations

from launcher import secure_browser


def test_opens_local_app_in_extension_free_guest_browser(tmp_path, monkeypatch):
    edge = tmp_path / "msedge.exe"
    edge.touch()
    launches = []
    monkeypatch.setattr(secure_browser, "_find_edge", lambda: edge)
    monkeypatch.setattr(secure_browser.subprocess, "Popen", lambda command, **kwargs: launches.append((command, kwargs)))

    assert secure_browser.open_isolated_browser("http://127.0.0.1:61234/app")

    command, kwargs = launches[0]
    assert command[0] == str(edge)
    assert "--guest" in command
    assert "--disable-extensions" in command
    assert "--inprivate" in command
    assert "--app=http://127.0.0.1:61234/app" in command
    assert kwargs["shell"] is False


def test_refuses_to_open_nonlocal_url(monkeypatch):
    monkeypatch.setattr(
        secure_browser.subprocess,
        "Popen",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("browser must not launch")),
    )

    assert not secure_browser.open_isolated_browser("https://example.com/private")
