# Deployment i architektura - BeSafeFish

## Architektura systemu

```
[Uzytkownik]
    |
    |-- [Strona WWW] -----> [Serwer Render.com] -----> [Supabase PostgreSQL]
    |                         (server.py / Flask)        (baza danych)
    |                         Connection Pool
    |                         gunicorn gthread
    |
    |-- [Aplikacja .exe] --> [Serwer Render.com] -----> [Supabase PostgreSQL]
         (gui/db.py)          (te same endpointy)
         urllib + JSON
```

### Przeplyw danych
1. Uzytkownik wchodzi na strone WWW lub uruchamia aplikacje .exe
2. Rejestracja/logowanie wyslane jako HTTP POST (JSON) do serwera Render
3. Serwer pobiera polaczenie z ThreadedConnectionPool, wykonuje zapytanie, zwraca do poola
4. Aplikacja/strona pokazuje wynik

### Dlaczego NIE laczymy sie bezposrednio z baza?

- Connection string w .exe = kazdy moze go wyciagnac (strings, dekompilacja)
- Uzytkownik musialby recznie konfigurowac .env
- **Rozwiazanie**: Klient -> HTTP/JSON -> serwer API -> baza. Sekrety tylko na serwerze.

## Serwer (Render.com)

### Connection pooling
- `ThreadedConnectionPool(minconn=1, maxconn=4)` — leniwa inicjalizacja
- `before_request`: pobiera polaczenie z poola do `g.db_conn`
- `teardown_request`: zwraca polaczenie (rollback + close przy bledzie)
- Bezpieczne z gunicorn `--preload` (kazdy worker tworzy wlasny pool)

### Gunicorn config (`gunicorn.conf.py`)
- `workers=2, threads=2` — 4 rownolegle requesty (max dla 512MB RAM)
- `worker_class=gthread` — wielowatkowosc w jednym procesie
- `preload_app=True` — wspoldzielony kod, mniej RAM
- `timeout=120` — zapas na cold start

### Rate limit (Flask-Limiter)

Limiter inicjalizowany w `server.py:64` z `Limiter(app=app, key_func=_real_ip, storage_uri="memory://")`.
**Wazne**: Limiter musi byc utworzony **przed** deklaracja `@app.before_request def _before_request()`,
zeby jego rate limit check szedl pierwszy (chroni connection pool).

Dekoratory na endpointach:
| Endpoint | Limit |
|----------|-------|
| `/api/register` | 5/h, 20/dzien per IP |
| `/api/login` | 10/min, 100/h per IP |
| pozostale | brak (TODO Tier 1.5) |

`_real_ip()` (server.py:51) bierze IP z `X-Forwarded-For` (Render za proxy),
fallback na `get_remote_address()`. Pierwszy element XFF to oryginalny klient.

Custom error handler 429 (server.py:72) zwraca JSON `{"ok": false, "msg": "Zbyt wiele prob..."}`
zamiast generycznego HTML "Too Many Requests".

**Storage in-memory:**
- Reset licznikow przy restarcie workera (Render free tier restartuje co kilka godzin) - akceptowalne dla MVP
- Niespojnosc miedzy workerami jesli sa dwa (jeden moze dac przepustke ktora drugi by zablokowal)
- Dla produkcji multi-worker: przesiadka na Redis (`storage_uri="redis://..."`)

### Endpointy API

| Endpoint | Metoda | Opis | Kto uzywa |
|----------|--------|------|-----------|
| `/` | GET | Strona WWW (pliki statyczne) | Przegladarka |
| `/api/register` | POST | Rejestracja uzytkownika | Strona + GUI .exe |
| `/api/login` | POST | Logowanie (zwraca user_id + subscription) | GUI .exe |
| `/api/health` | GET | Sprawdzenie czy serwer dziala | GUI .exe (health check) |
| `/api/subscription/<user_id>` | GET | Aktualny plan usera (z lazy expiration) | GUI .exe |
| `/api/payments/<user_id>` | GET | Historia platnosci (TOP 50) | GUI .exe |
| `/api/plans` | GET | Lista dostepnych planow | GUI .exe |
| `/api/usage/<user_id>` | GET | Dzienne zuzycie rund (bez inkrementacji) | GUI .exe |
| `/api/round/use` | POST | Sprawdzenie limitu + inkrementacja rund | GUI .exe (bot) |

### Parametr `source` w rejestracji
- `source: "web"` (domyslne) → `created_by = Rejestracja_WEB (id=7)`
- `source: "gui"` → `created_by = Rejestracja_GUI (id=5)`

### Zmienne srodowiskowe na Render
| Zmienna | Opis |
|---------|------|
| `DATABASE_URL_ADMIN` | Connection string Supabase (SEKRET) |
| `WEB_SYSTEM_USER_ID` | ID uzytkownika systemowego WEB (domyslnie 7) |
| `GUI_SYSTEM_USER_ID` | ID uzytkownika systemowego GUI (domyslnie 5) |
| `PYTHON_VERSION` | Wersja Pythona na Render (3.12) |

### Darmowy plan Render — ograniczenia
- **Usypianie**: po 15 min bezczynnoci, cold start ~30-50s
- **750 godzin/miesiac**: wystarczy na 1 serwis 24/7
- **512 MB RAM**: wystarczy dla Flask + pool
- **Brak custom domeny z SSL**: tylko `*.onrender.com`
- **Auto-deploy**: push na main przebudowuje (ale TYLKO jesli zmiana w rootDir)

### Co gdy Render padnie?
- Aplikacja .exe: logowanie/rejestracja nie dziala. Bot (lowienie) dziala lokalnie.
- Rozwiazanie: migracja na inny hosting (patrz nizej)
- Alternatywy: Koyeb (free, always-on), Railway ($5/mies), Fly.io (free, ~2-5s cold start)

## Migracja na inny hosting

1. Skopiuj folder `app/website/` na nowy serwer
2. `pip install -r requirements.txt`
3. Ustaw zmienne: `DATABASE_URL_ADMIN`, `WEB_SYSTEM_USER_ID`, `GUI_SYSTEM_USER_ID`
4. Uruchom: `gunicorn -c gunicorn.conf.py server:app` (Linux) lub `waitress-serve server:app` (Windows)
5. **WAZNE**: zaktualizuj `API_URL` w `app/gui/db.py` na nowy adres serwera
6. Przebuduj .exe i wrzuc nowy release na GitHub

## Budowanie .exe (PyInstaller)

Z rootu repo:

```bash
py -m PyInstaller app/BeSafeFish.spec -y
```

Output: `dist/BeSafeFish/BeSafeFish.exe`. Spec zaklada sciezki wzgledem rootu
repo, nie wzgledem `app/` (datas siegaja do `versions/tryb1_rybka_klik/post_cnn/cnn/models/`).

- `onedir` — folder, nie jeden plik (mniejszy, szybciej sie uruchamia)
- `uac_admin=True` — Windows wymaga Administratora
- `excludes=['torch', 'torchvision', 'matplotlib', 'tkinter']`
- Dolacza: ikone, model ONNX (.onnx + .onnx.data)
- Wynikowy .zip ~110 MB → GitHub Releases (nie commit)

## GitHub Releases

- Git limit 100 MB/plik, Releases limit 2 GB/asset
- Link `releases/latest/download/BeSafeFish.zip` — zawsze najnowszy
- Strona linkuje do tego URL — nie trzeba aktualizowac strony przy nowym buildzie

```bash
# Wymien asset w istniejacym release
gh release delete-asset v1.2.0 BeSafeFish.zip --yes
gh release upload v1.2.0 "dist/BeSafeFish.zip" --clobber
```

## Wazne zasady
- Wersja musi byc spojna: GUI footer (dashboard.py), strona (index.html), Release tag
- pgcrypto na Supabase: `extensions.crypt()` (schema `extensions`, nie `public`)
- Przy zmianie serwera: zaktualizuj API_URL w db.py + przebuduj .exe
