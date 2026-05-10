# Instrukcje projektowe - BeSafeFish

## Opis projektu

BeSafeFish to aplikacja desktopowa (PySide6/Qt) z botem do gry rybkarskiej.
Architektura: GUI (.exe) -> Flask API (Render) -> PostgreSQL (Supabase).

## Dokumentacja - co czytac przed zmianami

| Plik | Temat | Czytaj gdy... |
|------|-------|---------------|
| `app/docs/deployment-i-architektura.md` | Endpointy API, serwer, gunicorn, Render, PyInstaller | pracujesz nad server.py, deploymentem, .exe |
| `app/docs/struktura-bazy.md` | Tabele, funkcje SQL, diagram, przeplyw biznesowy | pracujesz nad SQL, dodajesz tabele/funkcje |
| `app/docs/zasady-sql.md` | Konwencje nazewnictwa, checklist zmian w bazie | zmieniasz kolumny/tabele/funkcje/enum w SQL |
| `app/docs/regulamin-i-rodo.md` | Regulamin, RODO, checkbox akceptacji, retencja danych | dodajesz rejestracje, zbierasz dane osobowe |
| `app/docs/architektura-i-lekcje.md` | Lekcje z refaktorow, modularnosc, Strategy pattern | projektujesz nowa funkcjonalnosc |
| `app/docs/build-i-release.md` | Build .exe, PyInstaller .spec, checklist release | robisz nowy release, .spec nie dziala |
| `app/docs/lekcje-sesja-v1.2.6.md` | SQL nullable, Qt threading, fail-open, audit log | dotykasz auth, watkowania GUI, schema bazy |
| `SECURITY.md` | Zasady bezpieczenstwa projektu | dotykasz auth, hasel, connection stringow |

**Po dodaniu tabeli, funkcji SQL lub endpointu API - zaktualizuj odpowiedni plik docs.**

---

## Konwencje projektowe

- Wersja musi byc spojna: GUI footer (`dashboard.py`), strona (`index.html`), GitHub Release tag
- `py` zamiast `python` na Windows

---

## Zasady techniczne - GUI desktopowe (PySide6 / Qt)

1. Kazda operacja sieciowa w osobnym watku - nigdy na main thread (zamrozony ekran).
2. Stan lokalny zamiast API gdzie dane zmieniaja sie przewidywalnie (+1, timer). API tylko na start/logowanie.
3. Reset stanu przy restarcie akcji - liczniki, labele, flagi wracaja do wartosci poczatkowych.
4. Health check przy starcie w tle - pokaz "Laczenie..." + retry, nie bialy ekran.
5. Feedback wizualny dla kazdej operacji - uzytkownik musi widziec ze cos sie dzieje.

## Zasady techniczne - Bot / automatyzacja

6. Fail-open - blad API = kontynuuj dzialanie, loguj ostrzezenie. Bot NIE moze sie zatrzymac z powodu bledu sieci.
7. Krotki timeout per-operacja (3-5s), dlugi na start/logowanie (30-60s).
8. Callback pattern - core bota nie importuje HTTP. Warstwa integracji (worker) obsluguje API.
9. Try/except wokol kazdego callbacka - wyjatek w callbacku nie moze crashnac glownej petli.

## Zasady techniczne - Flask / backend API

10. Connection pooling zawsze - ThreadedConnectionPool (psycopg2). Nigdy connect/close per request.
11. Polaczenie z poola w request lifecycle - before_request (pobierz), teardown_request (zwroc, rollback on error).
12. Gunicorn z gthread - workers=N, threads=2, preload.
13. Timeout: darmowy hosting z cold startem = 120s, produkcja = 30s.

## Zasady techniczne - SQL / baza danych

14. Lazy expiration zamiast crona - sprawdzaj przy kazdym uzyciu.
15. Atomowe operacje - sprawdzenie + modyfikacja w jednej transakcji. Nie SELECT + UPDATE osobno (race condition).
16. Auto-assign domyslnych wartosci przy rejestracji - nowy user dostaje plan/role od razu.
17. SECURITY DEFINER + search_path - ustaw search_path explicite (public, extensions).

## Zasady techniczne - DevOps / release

18. Duze pliki (>100MB) do GitHub Releases, nie do repozytorium.
19. Deploy na Render triggerowany tylko zmianami w rootDir - commit poza rootDir nie odpali redeployu.
20. Retry z backoff na start - GUI robi 3 proby z rosnacym odstepem przy cold start.
21. Rollback transakcji przy bledzie - teardown_request z rollback.
22. Build success != paczka dziala - PyInstaller exit 0 mimo brakujacych modulow. Zawsze odpal .exe lokalnie przed releasem.
23. Spadek rozmiaru paczki to alarm - ~290MB rozpakowane / ~118MB .zip. Spadek >30% bez wyjasnienia = sprawdz co zniknelo.
24. PyInstaller .spec - script/datas/icon wzgledem .spec, pathex wzgledem cwd. Build zawsze z roota repo.
