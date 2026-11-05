from PySide6.QtWidgets import QApplication

from launcher.single_instance import SingleInstance, instance_name


def test_instance_name_is_user_and_installation_scoped(tmp_path):
    assert instance_name(tmp_path) == instance_name(tmp_path)
    assert instance_name(tmp_path) != instance_name(tmp_path / "other")


def test_second_instance_notifies_first(tmp_path):
    QApplication.instance() or QApplication([])
    activated = []
    first = SingleInstance(tmp_path, lambda: activated.append(True))
    second = SingleInstance(tmp_path, lambda: None)
    try:
        assert first.acquire()
        assert not second.acquire()
        QApplication.processEvents()
        assert activated == [True]
    finally:
        first._server.close()
        second._server.close()
        from PySide6.QtNetwork import QLocalServer

        QLocalServer.removeServer(first.name)
