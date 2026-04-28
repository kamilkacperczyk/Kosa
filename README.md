# BeSafeFish

Asystent computer vision automatyzujacy czynnosci w grze - aplikacja desktopowa + rejestracja przez strone WWW + baza w chmurze (PySide6, Flask API, PostgreSQL, ONNX).

- Strona WWW: https://kosa-h283.onrender.com
- Pobranie .exe: [GitHub Releases](https://github.com/kamilkacperczyk/BeSafeFish/releases/latest)

## Jak dziala

1. Przechwytuje region mini-gry z ekranu (mss)
2. Rozpoznaje stan: bialy okrag (czekaj), czerwony okrag (klikaj), HIT/MISS (ignoruj)
3. Lokalizuje rybke (background subtraction + PatchCNN ONNX)
4. Klika w rybke gdy okrag jest czerwony (pydirectinput)

## Architektura

```
[Uzytkownik]
    |-- [Aplikacja .exe] --HTTP/JSON--> [Flask API (Render.com)] --psycopg2--> [Supabase PostgreSQL]
    |-- [Strona WWW]     --HTTP/JSON--> [Flask API (Render.com)] --psycopg2--> [Supabase PostgreSQL]
```

Aplikacja .exe NIE laczy sie bezposrednio z baza - komunikuje sie przez API serwera.

## Struktura repo

```
app/                      -- Wszystko co nad trybami (GUI, website, baza, docs)
  besafefish.py           -- Entry point GUI
  BeSafeFish.spec         -- Konfiguracja PyInstaller
  gui/                    -- GUI PySide6 (login, rejestracja, dashboard)
  website/                -- Strona WWW + Flask backend (server.py, render.yaml)
  SQL/                    -- Definicje tabel i funkcji PostgreSQL
  docs/                   -- Dokumentacja projektu

versions/
  tryb1_rybka_klik/       -- Tryb 1: "Mini-gra łowienie ryb (rybka - klik)"
    README.md             -- Opis trybu i jego wariantow
    tests/                -- Analizy, kalibracja, diagnostyka, walidacja
    post_cnn/             -- Aktywny wariant (klasyczny CV + PatchCNN ONNX)
    pre_cnn/              -- Archiwum (sam klasyczny CV, bez CNN)
  tryb2_dymek_spacja/     -- (Planowany) Tryb 2: "Mini-gra spacja (dymek z cyfrą)"
```

## Uruchomienie (deweloper)

Z rootu repo:

```bash
pip install -r requirements.txt
py app/besafefish.py
```

## Budowanie .exe

Z rootu repo:

```bash
py -m PyInstaller app/BeSafeFish.spec --clean -y
```

Wynik: `dist/BeSafeFish/` - spakuj jako .zip i wrzuc do GitHub Releases.

## Baza danych

PostgreSQL na Supabase. 7 tabel: users, subscription_plans, user_subscriptions, payments, daily_usage, login_history, audit_log.

Szczegoly: `app/docs/struktura-bazy.md`

## Monitoring

Dashboard Grafana Cloud podpiety do Supabase PostgreSQL przez dedykowanego read-only usera (`grafana_ro` z `BYPASSRLS` + `GRANT SELECT`).

**Adres:** https://kacperczyk95.grafana.net/

**Dostep:** dashboard jest **prywatny** - tylko admin (Ty) widzi panele po zalogowaniu. Z wzgledow bezpieczenstwa i RODO **nie udostepniam monitoringu publicznie**, poniewaz panele zawieraja dane osobowe uzytkownikow (loginy, czas logowan, przyczyny nieudanych prob) ktorych zgoda na publikacje nie obejmuje.

**Co jest monitorowane:**
- Logowania w czasie (udane vs nieudane jako time series)
- Aktywnosc uzytkownikow (count logowan per user)
- Przyczyny nieudanych logowan (audit z `login_history.failure_reason`)
- Plany subskrypcji w chwili logowania (LATERAL JOIN z `user_subscriptions`)

**Stack:**
- Grafana Cloud Free (10k metryk, 14 dni retencji, bez 2FA built-in - logowanie OAuth)
- PostgreSQL data source przez Supavisor session pooler (port 5432, IPv4)
- Read-only user (`grafana_ro`) na poziomie bazy + `BYPASSRLS` (omijanie domyslnych polityk Supabase)

**Bezpieczenstwo:** tylko `SELECT` na schemacie public, brak `INSERT/UPDATE/DELETE`, brak dostepu do `auth.*` schemata (Supabase internal).

Ponizej zestaw przykladowych panelow (zrzut ekranu z dashboardu admin):

![Dashboard Grafana - BeSafeFish monitoring](app/docs/screenshots/grafana-besafefish-psql-monitoring-screen.png)

## Dokumentacja

| Plik | Opis |
|------|------|
| `app/docs/deployment-i-architektura.md` | Architektura, API, Render, PyInstaller, migracja |
| `app/docs/struktura-bazy.md` | Diagram zaleznosci tabel, funkcje, triggery |
| `app/docs/historia-wersji.md` | Ewolucja bota (pre_cnn → post_cnn), co sie zmienilo |
| `versions/tryb1_rybka_klik/post_cnn/cnn/ARCHITEKTURA_CNN.md` | Architektura sieci CNN, pipeline treningowy |
| `SECURITY.md` | Polityka bezpieczenstwa, pre-commit hook |
