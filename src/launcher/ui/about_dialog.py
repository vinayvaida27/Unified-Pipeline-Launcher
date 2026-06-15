"""About dialog."""

from PySide6.QtWidgets import QMessageBox


def show_about(parent, platform_name: str) -> None:
    """Show about text."""

    QMessageBox.about(parent, f"About {platform_name}", f"{platform_name}\nVersion 1.0.0")
