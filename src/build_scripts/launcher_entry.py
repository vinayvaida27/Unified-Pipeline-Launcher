"""Frozen-application entry point.

PyInstaller runs the entry script as the top-level ``__main__`` module, which
has no package context -- so the package's own ``__main__.py`` (which uses a
relative ``from .main import main``) cannot be used directly. This thin wrapper
imports the launcher package absolutely and starts it.

It also isolates the bundled Qt from any other Qt on the machine. Many systems
have a second Qt on PATH (Anaconda, Intel/AMD tools, other PySide/PyQt apps);
without isolation Windows can load that foreign ``Qt6Core.dll`` and the bundled
``Qt6Widgets.dll`` then fails with "DLL load failed ... The specified procedure
could not be found." We prepend the bundle directory to the DLL search and drop
inherited Qt environment hints so the launcher always loads its own Qt.
"""

import os
import sys


def _isolate_bundled_qt() -> None:
    if not getattr(sys, "frozen", False):
        return
    bundle_dir = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    # Put the bundled DLLs ahead of anything inherited on PATH.
    os.environ["PATH"] = bundle_dir + os.pathsep + os.environ.get("PATH", "")
    try:
        os.add_dll_directory(bundle_dir)
    except (OSError, AttributeError):
        pass
    # Ignore any external Qt plugin/import hints; use only what we ship.
    for var in (
        "QT_PLUGIN_PATH",
        "QT_QPA_PLATFORM_PLUGIN_PATH",
        "QML2_IMPORT_PATH",
        "QML_IMPORT_PATH",
        "QTDIR",
    ):
        os.environ.pop(var, None)


_isolate_bundled_qt()

from launcher.main import main

if __name__ == "__main__":
    sys.exit(main())
