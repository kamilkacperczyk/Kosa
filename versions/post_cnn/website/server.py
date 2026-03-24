"""
Backend strony BeSafeFish - rejestracja uzytkownikow przez WEB.

Uruchomienie:
    python server.py

Serwuje pliki statyczne (index.html, css, js, img)
oraz endpoint POST /api/register do rejestracji.
"""

import os
import sys

# Dodaj katalog post_cnn do PYTHONPATH (zeby gui.db dzialalo)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import psycopg2
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Zaladuj .env z katalogu post_cnn/
_env_path = os.path.join(BASE_DIR, ".env")
load_dotenv(_env_path)

DATABASE_URL = os.getenv("DATABASE_URL_ADMIN")
WEB_SYSTEM_USER_ID = 7  # id usera "Rejestracja_WEB" w tabeli users

app = Flask(__name__, static_folder=".", static_url_path="")


def _get_connection():
    if not DATABASE_URL:
        raise RuntimeError("Brak DATABASE_URL_ADMIN w .env")
    return psycopg2.connect(DATABASE_URL)


@app.route("/")
def index():
    return app.send_static_file("index.html")


@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json()
    if not data:
        return jsonify({"ok": False, "msg": "Brak danych."}), 400

    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    if len(username) < 3:
        return jsonify({"ok": False, "msg": "Nazwa uzytkownika musi miec min. 3 znaki."})
    if not email:
        return jsonify({"ok": False, "msg": "Podaj adres email."})
    if len(password) < 4:
        return jsonify({"ok": False, "msg": "Haslo musi miec min. 4 znaki."})

    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            "SET LOCAL app.current_user_id = %s", (str(WEB_SYSTEM_USER_ID),)
        )
        cur.execute(
            "SELECT create_user_short(%s, %s, %s, 'user')",
            (username, email, password),
        )
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"ok": True, "msg": "Konto utworzone! Mozesz pobrac aplikacje i sie zalogowac."})
    except psycopg2.errors.UniqueViolation:
        return jsonify({"ok": False, "msg": "Uzytkownik o tej nazwie juz istnieje."})
    except Exception as e:
        return jsonify({"ok": False, "msg": f"Blad rejestracji: {e}"}), 500


if __name__ == "__main__":
    print("BeSafeFish WEB - http://localhost:5000")
    app.run(debug=True, port=5000)
