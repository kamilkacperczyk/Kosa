"""
Lokalna baza uzytkownikow (SQLite).

MVP: przechowuje login/haslo lokalnie.
Docelowo: PostgreSQL (info w TODO.txt — "baza to bedzie postgres ale na razie lokalnie").
"""

import sqlite3
import hashlib
import secrets
import os
from datetime import datetime

# Baza danych obok modulu gui/
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.db")


def _get_connection():
    """Zwraca polaczenie do SQLite z WAL mode."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Tworzy tabele users jesli nie istnieje + seeduje konto testowe."""
    conn = _get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

    # Konto testowe — zawsze dostepne
    _seed_test_user("REDACTED-USER", "REDACTED-PASS")


def _seed_test_user(username: str, password: str):
    """Tworzy konto testowe jesli jeszcze nie istnieje (ciche — bez bledu)."""
    conn = _get_connection()
    exists = conn.execute(
        "SELECT 1 FROM users WHERE username = ?", (username,)
    ).fetchone()
    if not exists:
        salt = secrets.token_hex(16)
        pw_hash = _hash_password(password, salt)
        conn.execute(
            "INSERT INTO users (username, password_hash, salt, created_at) VALUES (?, ?, ?, ?)",
            (username, pw_hash, salt, datetime.now().isoformat()),
        )
        conn.commit()
    conn.close()


def _hash_password(password: str, salt: str) -> str:
    """PBKDF2-HMAC-SHA256, 100k iteracji."""
    dk = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100_000,
    )
    return dk.hex()


def register_user(username: str, password: str) -> tuple:
    """
    Rejestruje nowego uzytkownika.

    Returns:
        (success: bool, message: str)
    """
    if len(username) < 3:
        return False, "Nazwa uzytkownika musi miec min. 3 znaki."
    if len(password) < 4:
        return False, "Haslo musi miec min. 4 znaki."

    salt = secrets.token_hex(16)
    password_hash = _hash_password(password, salt)

    try:
        conn = _get_connection()
        conn.execute(
            "INSERT INTO users (username, password_hash, salt, created_at) VALUES (?, ?, ?, ?)",
            (username, password_hash, salt, datetime.now().isoformat()),
        )
        conn.commit()
        conn.close()
        return True, "Konto utworzone pomyslnie!"
    except sqlite3.IntegrityError:
        return False, "Uzytkownik o tej nazwie juz istnieje."


def authenticate_user(username: str, password: str) -> tuple:
    """
    Loguje uzytkownika.

    Returns:
        (success: bool, message: str)
    """
    conn = _get_connection()
    row = conn.execute(
        "SELECT password_hash, salt FROM users WHERE username = ?",
        (username,),
    ).fetchone()
    conn.close()

    if row is None:
        return False, "Nieprawidlowa nazwa uzytkownika lub haslo."

    stored_hash, salt = row
    computed_hash = _hash_password(password, salt)

    if computed_hash == stored_hash:
        return True, "Zalogowano pomyslnie!"
    else:
        return False, "Nieprawidlowa nazwa uzytkownika lub haslo."
