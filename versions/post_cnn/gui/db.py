"""
Baza uzytkownikow BeSafeFish (PostgreSQL / Supabase).

Laczy sie z baza przez DATABASE_URL_ADMIN z pliku .env.
Hasla hashowane po stronie bazy (bcrypt przez pgcrypto).
"""

import os
import psycopg2
from dotenv import load_dotenv

# Zaladuj .env z katalogu post_cnn/
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
load_dotenv(_env_path)

DATABASE_URL = os.getenv("DATABASE_URL_ADMIN")
GUI_SYSTEM_USER_ID = 5  # id usera "Rejestracja_GUI" w tabeli users


def _get_connection():
    """Zwraca polaczenie do PostgreSQL (Supabase)."""
    if not DATABASE_URL:
        raise RuntimeError(
            "Brak DATABASE_URL_ADMIN w .env. Skopiuj .env.example jako .env i uzupelnij dane."
        )
    return psycopg2.connect(DATABASE_URL)


def init_db():
    """Sprawdza polaczenie z baza. Tabele juz istnieja na Supabase (migracja)."""
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
    except Exception as e:
        raise RuntimeError(f"Nie mozna polaczyc z baza danych: {e}")


def register_user(username: str, email: str, password: str) -> tuple:
    """
    Rejestruje nowego uzytkownika przez funkcje create_user_short.

    Returns:
        (success: bool, message: str)
    """
    if len(username) < 3:
        return False, "Nazwa uzytkownika musi miec min. 3 znaki."
    if len(password) < 4:
        return False, "Haslo musi miec min. 4 znaki."
    if not email:
        return False, "Podaj adres email."

    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            "SET LOCAL app.current_user_id = %s", (str(GUI_SYSTEM_USER_ID),)
        )
        cur.execute(
            "SELECT create_user_short(%s, %s, %s, 'user')",
            (username, email, password),
        )
        conn.commit()
        cur.close()
        conn.close()
        return True, "Konto utworzone pomyslnie"
    except psycopg2.errors.UniqueViolation:
        return False, "Uzytkownik o tej nazwie juz istnieje."
    except Exception as e:
        return False, f"Blad rejestracji: {e}"


def authenticate_user(username: str, password: str) -> tuple:
    """
    Loguje uzytkownika (sprawdza haslo przez bcrypt w bazie).

    Returns:
        (success: bool, message: str)
    """
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id FROM users
            WHERE login = %s
              AND password_hash = extensions.crypt(%s, password_hash)
              AND is_active = true
              AND deleted_at IS NULL
            """,
            (username, password),
        )
        row = cur.fetchone()
        cur.close()
        conn.close()

        if row:
            return True, "Zalogowano pomyslnie"
        else:
            return False, "Nieprawidlowa nazwa uzytkownika lub haslo."
    except Exception as e:
        return False, f"Blad logowania: {e}"
