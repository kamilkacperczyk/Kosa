"""
Ekran logowania BeSafeFish.

Obsluguje logowanie i rejestracje uzytkownikow.
Po udanym logowaniu emituje sygnal login_success(username).
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFrame, QSpacerItem, QSizePolicy,
)
from PySide6.QtCore import Signal, Qt

from gui.db import authenticate_user, register_user, init_db


class LoginScreen(QWidget):
    """Ekran logowania z mozliwoscia rejestracji."""

    login_success = Signal(str)  # emituje username po zalogowaniu

    def __init__(self):
        super().__init__()
        init_db()
        self._is_register_mode = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(12)
        layout.setContentsMargins(60, 40, 60, 40)

        # --- Spacer gorny ---
        layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # --- Tytul ---
        title = QLabel("\U0001F41F BeSafeFish")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Automatyczne lowienie — Metin2 Eryndos")
        subtitle.setObjectName("subtitleLabel")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(30)

        # --- Formularz (wycentrowany, max 360px) ---
        form_container = QWidget()
        form_container.setMaximumWidth(360)
        form_layout = QVBoxLayout(form_container)
        form_layout.setSpacing(10)
        form_layout.setContentsMargins(0, 0, 0, 0)

        # Username
        self._username_label = QLabel("Nazwa uzytkownika")
        form_layout.addWidget(self._username_label)

        self._username_input = QLineEdit()
        self._username_input.setPlaceholderText("Wpisz nazwe uzytkownika...")
        self._username_input.setMinimumHeight(40)
        form_layout.addWidget(self._username_input)

        # Password
        form_layout.addSpacing(4)
        self._password_label = QLabel("Haslo")
        form_layout.addWidget(self._password_label)

        self._password_input = QLineEdit()
        self._password_input.setEchoMode(QLineEdit.Password)
        self._password_input.setPlaceholderText("Wpisz haslo...")
        self._password_input.setMinimumHeight(40)
        form_layout.addWidget(self._password_input)

        # Confirm Password (widoczne tylko w trybie rejestracji)
        self._confirm_label = QLabel("Powtorz haslo")
        self._confirm_label.setVisible(False)
        form_layout.addWidget(self._confirm_label)

        self._confirm_input = QLineEdit()
        self._confirm_input.setEchoMode(QLineEdit.Password)
        self._confirm_input.setPlaceholderText("Powtorz haslo...")
        self._confirm_input.setMinimumHeight(40)
        self._confirm_input.setVisible(False)
        form_layout.addWidget(self._confirm_input)

        # Komunikat bledu / sukcesu
        form_layout.addSpacing(4)
        self._message_label = QLabel("")
        self._message_label.setObjectName("errorLabel")
        self._message_label.setAlignment(Qt.AlignCenter)
        self._message_label.setWordWrap(True)
        form_layout.addWidget(self._message_label)

        # Przycisk akcji (Zaloguj / Zarejestruj)
        form_layout.addSpacing(8)
        self._action_button = QPushButton("Zaloguj sie")
        self._action_button.setObjectName("loginButton")
        self._action_button.setMinimumHeight(44)
        self._action_button.clicked.connect(self._on_action)
        form_layout.addWidget(self._action_button)

        # Separator
        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFrameShape(QFrame.HLine)
        form_layout.addSpacing(8)
        form_layout.addWidget(sep)

        # Przelacznik logowanie/rejestracja
        self._toggle_button = QPushButton("Nie masz konta? Zarejestruj sie")
        self._toggle_button.setObjectName("registerButton")
        self._toggle_button.setCursor(Qt.PointingHandCursor)
        self._toggle_button.clicked.connect(self._toggle_mode)
        form_layout.addWidget(self._toggle_button)

        # Wycentruj formularz
        h_layout = QHBoxLayout()
        h_layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))
        h_layout.addWidget(form_container)
        h_layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))
        layout.addLayout(h_layout)

        # --- Spacer dolny ---
        layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Enter = zaloguj
        self._username_input.returnPressed.connect(self._on_action)
        self._password_input.returnPressed.connect(self._on_action)
        self._confirm_input.returnPressed.connect(self._on_action)

    def _toggle_mode(self):
        """Przelacza miedzy trybem logowania a rejestracji."""
        self._is_register_mode = not self._is_register_mode
        self._message_label.setText("")

        if self._is_register_mode:
            self._action_button.setText("Zarejestruj sie")
            self._toggle_button.setText("Masz juz konto? Zaloguj sie")
            self._confirm_label.setVisible(True)
            self._confirm_input.setVisible(True)
        else:
            self._action_button.setText("Zaloguj sie")
            self._toggle_button.setText("Nie masz konta? Zarejestruj sie")
            self._confirm_label.setVisible(False)
            self._confirm_input.setVisible(False)

    def _on_action(self):
        """Obsluguje klikniecie przycisku Zaloguj/Zarejestruj."""
        username = self._username_input.text().strip()
        password = self._password_input.text()

        if not username or not password:
            self._show_error("Wypelnij wszystkie pola.")
            return

        if self._is_register_mode:
            confirm = self._confirm_input.text()
            if password != confirm:
                self._show_error("Hasla sie nie zgadzaja.")
                return

            ok, msg = register_user(username, password)
            if ok:
                self._show_success(msg + " Mozesz sie zalogowac.")
                self._toggle_mode()  # wroc do logowania
                self._username_input.setText(username)
                self._password_input.clear()
            else:
                self._show_error(msg)
        else:
            ok, msg = authenticate_user(username, password)
            if ok:
                self.login_success.emit(username)
            else:
                self._show_error(msg)

    def _show_error(self, msg: str):
        self._message_label.setStyleSheet("color: #e63946;")
        self._message_label.setText(msg)

    def _show_success(self, msg: str):
        self._message_label.setStyleSheet("color: #1b998b;")
        self._message_label.setText(msg)
