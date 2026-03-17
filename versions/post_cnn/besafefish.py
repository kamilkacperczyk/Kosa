"""
BeSafeFish — punkt wejscia aplikacji.

Uruchomienie:
    python besafefish.py

Wymagania:
    - PySide6
    - Wszystkie zaleznosci z requirements.txt
    - Windows (pydirectinput wymaga Windows)
"""

import sys
import os

# Dodaj katalog post_cnn do PYTHONPATH (zeby importy src.* i gui.* dzialaly)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import ctypes
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from gui.app import BeSafeFishApp
from gui.styles import DARK_THEME


def main():
    # Windows: ustaw AppUserModelID zeby ikona byla widoczna na pasku zadan
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Kosa.BeSafeFish.1.0")
    except Exception:
        pass
    # High DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("BeSafeFish")
    app.setOrganizationName("Kosa")
    app.setStyleSheet(DARK_THEME)

    window = BeSafeFishApp()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
