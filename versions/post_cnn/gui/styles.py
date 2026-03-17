"""
Styl QSS dla BeSafeFish — ciemny motyw z akcentami morskimi.

Paleta:
    Tlo:        #1a1a2e (granatowy)
    Panel:      #16213e (ciemnoniebieski)
    Akcent:     #1b998b / #17b890 (morski/teal)
    Akcent2:    #53a8b6 (jasnoniebieski)
    Niebezp.:   #e63946 (czerwony)
    Tekst:      #e0e0e0 (jasnoszary)
"""

DARK_THEME = """
/* === GLOBALNE === */
QWidget {
    background-color: #1a1a2e;
    color: #e0e0e0;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}

/* === PRZYCISKI === */
QPushButton {
    background-color: #16213e;
    color: #e0e0e0;
    border: 1px solid #0f3460;
    border-radius: 6px;
    padding: 8px 20px;
    font-size: 13px;
    min-height: 20px;
}
QPushButton:hover {
    background-color: #0f3460;
    border-color: #53a8b6;
}
QPushButton:pressed {
    background-color: #0a2647;
}
QPushButton:disabled {
    background-color: #2a2a3e;
    color: #666;
    border-color: #333;
}

/* Przycisk START */
QPushButton#startButton {
    background-color: #1b998b;
    color: white;
    font-size: 18px;
    font-weight: bold;
    border: 2px solid #17b890;
    border-radius: 10px;
    padding: 15px 40px;
    min-height: 40px;
}
QPushButton#startButton:hover {
    background-color: #17b890;
}
QPushButton#startButton:pressed {
    background-color: #148f77;
}

/* Przycisk STOP */
QPushButton#stopButton {
    background-color: #e63946;
    color: white;
    font-size: 18px;
    font-weight: bold;
    border: 2px solid #ff6b6b;
    border-radius: 10px;
    padding: 15px 40px;
    min-height: 40px;
}
QPushButton#stopButton:hover {
    background-color: #ff6b6b;
}
QPushButton#stopButton:pressed {
    background-color: #c1121f;
}

/* Przycisk ZALOGUJ */
QPushButton#loginButton {
    background-color: #1b998b;
    color: white;
    font-size: 15px;
    font-weight: bold;
    border: 2px solid #17b890;
    border-radius: 8px;
    padding: 10px 30px;
}
QPushButton#loginButton:hover {
    background-color: #17b890;
}

/* Link rejestracji */
QPushButton#registerButton {
    background-color: transparent;
    color: #53a8b6;
    border: none;
    font-size: 12px;
}
QPushButton#registerButton:hover {
    color: #17b890;
}

/* Przycisk wylogowania */
QPushButton#logoutButton {
    background-color: transparent;
    color: #888;
    border: 1px solid #444;
    border-radius: 4px;
    padding: 4px 12px;
    font-size: 11px;
}
QPushButton#logoutButton:hover {
    color: #e0e0e0;
    border-color: #666;
}

/* === POLA TEKSTOWE === */
QLineEdit {
    background-color: #16213e;
    color: #e0e0e0;
    border: 1px solid #0f3460;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 14px;
    selection-background-color: #1b998b;
}
QLineEdit:focus {
    border-color: #53a8b6;
}

/* === LOG === */
QPlainTextEdit {
    background-color: #0d1117;
    color: #c9d1d9;
    border: 1px solid #21262d;
    border-radius: 6px;
    padding: 8px;
    font-family: "Cascadia Code", "Consolas", monospace;
    font-size: 12px;
    selection-background-color: #1b998b;
}

/* === ETYKIETY === */
QLabel {
    background-color: transparent;
    color: #e0e0e0;
}
QLabel#titleLabel {
    font-size: 28px;
    font-weight: bold;
    color: #53a8b6;
}
QLabel#subtitleLabel {
    font-size: 12px;
    color: #888;
}
QLabel#statusLabel {
    font-size: 14px;
    font-weight: bold;
    padding: 4px 12px;
    border-radius: 4px;
}
QLabel#errorLabel {
    color: #e63946;
    font-size: 12px;
}
QLabel#successLabel {
    color: #1b998b;
    font-size: 12px;
}
QLabel#statsLabel {
    font-size: 13px;
    color: #aaa;
}
QLabel#userLabel {
    font-size: 12px;
    color: #53a8b6;
}

/* === RAMKI === */
QFrame#separator {
    background-color: #0f3460;
    max-height: 1px;
}

/* === SCROLLBAR === */
QScrollBar:vertical {
    background-color: #1a1a2e;
    width: 8px;
    border: none;
}
QScrollBar::handle:vertical {
    background-color: #0f3460;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background-color: #53a8b6;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* === CHECKBOX === */
QCheckBox {
    color: #e0e0e0;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #0f3460;
    border-radius: 3px;
    background-color: #16213e;
}
QCheckBox::indicator:checked {
    background-color: #1b998b;
    border-color: #17b890;
}
"""
