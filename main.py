from __future__ import annotations

import os
import sys
from pathlib import Path


def _prepare_qt_plugins() -> None:
    try:
        import PySide6
    except ImportError:
        return

    pyside_dir = Path(PySide6.__file__).resolve().parent
    candidates = [
        pyside_dir / "plugins",
        pyside_dir / "Qt" / "plugins",
    ]
    for plugin_dir in candidates:
        platforms_dir = plugin_dir / "platforms"
        if platforms_dir.exists():
            os.environ["QT_PLUGIN_PATH"] = str(plugin_dir)
            os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(platforms_dir)
            break


_prepare_qt_plugins()

from PySide6.QtWidgets import QApplication

from core.config import load_config
from ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    config = load_config()
    window = MainWindow(config)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
