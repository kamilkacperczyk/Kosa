"""
BeSafeFish — glowne okno aplikacji.

QStackedWidget przelacza miedzy:
    - LoginScreen  (ekran logowania)
    - Dashboard    (panel sterowania botem)
"""

import sys
from PySide6.QtWidgets import QMainWindow, QStackedWidget, QApplication
from PySide6.QtCore import Qt, Slot

from gui.login_screen import LoginScreen
from gui.dashboard import Dashboard


class BeSafeFishApp(QMainWindow):
    """Glowne okno aplikacji z przelaczaniem ekranow."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("BeSafeFish")
        self.setMinimumSize(700, 550)
        self.resize(800, 600)

        # Centralny widget — stos ekranow
        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        # Ekran logowania (zawsze istnieje)
        self._login_screen = LoginScreen()
        self._login_screen.login_success.connect(self._on_login)
        self._stack.addWidget(self._login_screen)

        # Dashboard (tworzony po zalogowaniu)
        self._dashboard = None

        # Start na ekranie logowania
        self._stack.setCurrentWidget(self._login_screen)

    @Slot(str)
    def _on_login(self, username: str):
        """Zalogowano — przejdz na dashboard."""
        # Usun stary dashboard (jesli relogi)
        if self._dashboard:
            self._stack.removeWidget(self._dashboard)
            self._dashboard.cleanup()
            self._dashboard.deleteLater()

        self._dashboard = Dashboard(username)
        self._dashboard.logout_requested.connect(self._on_logout)
        self._stack.addWidget(self._dashboard)
        self._stack.setCurrentWidget(self._dashboard)

        self.setWindowTitle(f"BeSafeFish \u2014 {username}")

    @Slot()
    def _on_logout(self):
        """Wylogowano — wroc do logowania."""
        if self._dashboard:
            self._dashboard.cleanup()
            self._stack.removeWidget(self._dashboard)
            self._dashboard.deleteLater()
            self._dashboard = None

        self._stack.setCurrentWidget(self._login_screen)
        self.setWindowTitle("BeSafeFish")

    def closeEvent(self, event):
        """Czysci zasoby przy zamykaniu okna."""
        if self._dashboard:
            self._dashboard.cleanup()
        event.accept()
