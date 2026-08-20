from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QTimer, Qt
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from .project_store import ProjectStore
from .ui.main_window import MainWindow
from .ui.style import APP_STYLESHEET


def resource_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "quiltforge" / "resources"
    return Path(__file__).resolve().parent / "resources"


def main() -> int:
    QCoreApplication.setOrganizationName("ITSZ Studios")
    QCoreApplication.setOrganizationDomain("itsz.studio")
    QCoreApplication.setApplicationName("QuiltForge")
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    # Register Windows fonts explicitly so packaged/headless launches retain the intended UI typography.
    for font_path in ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/seguisb.ttf", "C:/Windows/Fonts/segoeuib.ttf"):
        if Path(font_path).exists():
            QFontDatabase.addApplicationFont(font_path)
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(APP_STYLESHEET)
    window = MainWindow(ProjectStore(), resource_dir())
    project_arguments = [Path(argument) for argument in sys.argv[1:] if argument.lower().endswith(".qforge")]
    if project_arguments and project_arguments[0].exists():
        window.open_project(project_arguments[0])
    window.show()
    if "--smoke-test" in sys.argv:
        QTimer.singleShot(750, app.quit)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
