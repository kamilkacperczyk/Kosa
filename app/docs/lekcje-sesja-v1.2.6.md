# Lekcje z sesji v1.2.6 (2026-04-27)

Sesja zaczęła się od ujednolicenia opisów planów (Próbny + Darmowy), przeszła
przez fix loginu (bug serwera + freeze GUI), skończyła wpadką z popsutym .exe
w release v1.2.6. Wnioski podzielone na 4 obszary:

- A) SQL i schema bazy
- B) Wątki w GUI (operacje sieciowe)
- C) Fail-open w warstwie API
- D) Build i release (osobny dokument: [build-i-release.md](build-i-release.md))

---

## A) SQL i schema bazy

### A1. Bug: HTTP 500 przy nieudanym logowaniu z nieznanym loginem

**Commit:** `3814cc8 fix: login_history.user_id NULLABLE`

**Co się działo:**

`/api/login` przy logowaniu na nieistniejący login (np. literówka) próbował
zapisać audit do `login_history` z `user_id = NULL` (bo takiego usera nie ma
w `users`). Schema miała `user_id integer NOT NULL` - INSERT padał, błąd
propagował się jako HTTP 500.

User dostawał generyczny komunikat "Nieznany blad" zamiast czystego
"Nieprawidłowa nazwa użytkownika lub hasło".

**Fix:**

```sql
ALTER TABLE public.login_history
    ALTER COLUMN user_id DROP NOT NULL;
```

Plus aktualizacja definicji w `app/SQL/tables/login_history.sql` i
`app/SQL/supabase_migration.sql` (zbiorczy skrypt do postawienia bazy od zera).
Plik migracji: `app/SQL/migrations/2026_04_27_login_history_user_id_nullable.sql`.

FK do `users.id` zostaje - NULL nie łamie FK constraint.

### Lekcje SQL z tej sesji

#### L-A1. Kolumny audit/log: domyślnie NULLABLE dla pól zewnętrznych

Audit logu nie ma od czego zaczynać - wpis ma sens nawet gdy "kto" lub "co"
jest nieznane (próba logowania na nieistniejący login, próba operacji bez
zalogowania). Takie pola muszą być NULLABLE.

**Złe:**
```sql
CREATE TABLE login_history (
    user_id integer NOT NULL  -- blokuje audit przy nieznanym loginie
);
```

**Dobre:**
```sql
CREATE TABLE login_history (
    user_id integer  -- NULL gdy proba logowania na nieistniejacy login
);
```

To dotyczy:
- `login_history.user_id` (już naprawione)
- `audit_log.actor_id` (jeśli kiedyś dodamy ślady akcji bez zalogowanego usera)
- `audit_log.target_id` (jeśli akcja dotyczy obiektu który już nie istnieje)

#### L-A2. Definicja w 3 miejscach musi być spójna

Schemat tabeli żyje w trzech plikach:
- `app/SQL/tables/<tabela>.sql` - kanoniczna definicja pojedynczej tabeli
- `app/SQL/supabase_migration.sql` - zbiorczy skrypt do postawienia bazy od zera
- Faktyczna baza Supabase (produkcja)

Po migracji **wszystkie trzy** muszą być spójne. Inaczej ktoś (Ty za pół roku
albo CI postawione od zera) dostanie inną bazę niż produkcja.

Checklist po migracji:
1. Plik migracji w `app/SQL/migrations/<data>_<opis>.sql` (rekord zmiany)
2. Aktualizacja `app/SQL/tables/<tabela>.sql` (kanoniczna definicja)
3. Aktualizacja `app/SQL/supabase_migration.sql` (skrypt zbiorczy)
4. Odpalenie migracji na Supabase (SQL Editor → Run)
5. Weryfikacja: API przestaje zwracać HTTP 500 → curl test

#### L-A3. Komentarze SQL powinny opisywać semantykę, nie tylko techniczne

W tej sesji poprawiłem komentarz `subscription_plans.is_active` z
"Czy plan jest aktywny i dostepny do zakupu" → "Czy plan jest aktywny i
widoczny dla uzytkownikow" - bo "do zakupu" było nieaktualne (plany są bezpłatne).

Komentarz powinien opisywać **kiedy/po co** kolumny używamy, nie tylko **co**
zawiera. Stary komentarz "do zakupu" wprowadzał w błąd kogoś czytającego
schemat (myślałby, że są płatne plany).

#### L-A4. NULL nie łamie FK

Częsta obawa: "skoro `user_id` ma FK do `users.id`, to NULL chyba pęknie?"
Nie. PostgreSQL FK constraint ignoruje NULL - dopiero gdy wpiszesz konkretną
wartość, sprawdza czy istnieje w tabeli docelowej.

Czyli można mieć `user_id integer REFERENCES users(id)` i jednocześnie
NULLABLE - wpisy z NULL są dozwolone, wpisy z 999999 (nieistniejący ID) padną.

---

## B) Wątki w GUI (PySide6)

### B1. Bug: GUI zamarza podczas logowania

**Commit:** `bad6c4f feat: login/register w osobnym watku QThread + animowany spinner`

**Co się działo:**

`_on_action()` w `login_screen.py` wołał `authenticate_user()` synchronicznie
na main threadzie. Każdy request HTTP blokował Qt event loop.

Przy szybkim łączu (request 200ms) - niewidoczne. Ale:
- Cold start Render free tier: 30-60 sekund freeze GUI
- Wolny internet: 2-5 sekund freeze (Windows oznacza okno jako "Not responding")
- Padnięty backend: 60s do timeoutu (ustawione w `db.py`)

Identyczny wzorzec dla `register_user()`.

**Fix:**

1. Nowa klasa `_AuthThread(QThread)` - wykonuje login lub register w tle,
   emituje signal `result(action, ok, msg, user_id, subscription)` po zakończeniu.

2. `_start_auth(action, **kwargs)` - spawn wątku, blokowanie przycisku ("Logowanie..."),
   start spinnera.

3. `_on_auth_done(...)` - slot połączony z signal'em, pokazuje wynik (sukces lub
   błąd), włącza przycisk z powrotem.

4. Nowy widget `Spinner(QWidget)` - kręcące się kółko (QPainter + QTimer 25 FPS),
   wirujący łuk 90° po obwodzie. Cień pasuje do dark theme.

5. Guard `_auth_in_progress` - blokuje podwójne kliknięcia w trakcie requestu.

### Lekcje wątków GUI

#### L-B1. KAŻDA operacja sieciowa w QThread

To było już w `CLAUDE.md` jako zasada #1, ale dotychczas tylko health check
przy starcie miał osobny wątek (`_ServerCheckThread`). Login był pominięty.

**Pełna lista miejsc gdzie GUI woła API i potrzebuje wątku:**
- ✅ Health check przy starcie (`_ServerCheckThread`)
- ✅ Login + Register (`_AuthThread`)
- ⚠ `subscription_tab.py` - `get_subscription`, `get_payments`, `get_plans`,
  `get_daily_usage` - **prawdopodobnie też synchronicznie na main thread**.
  Do sprawdzenia w przyszłości.
- ⚠ `bot_worker.py` - `use_round` (krótki timeout 5s, ale i tak)
- Każdy nowy endpoint który dodamy

**Reguła:** zanim dodasz wywołanie z `gui.db` w slotcie GUI - zatrzymaj się
i pomyśl czy nie powinien iść przez QThread.

#### L-B2. Wizualny feedback dla każdej operacji

Sam wątek nie wystarczy. User musi widzieć **że apka żyje**, nawet gdy
request trwa 30s. Inaczej wciska Ctrl+Alt+Del i killuje proces.

Minimum dla operacji >1s:
- Disable przycisku (żeby nie kliknął ponownie)
- Tekst przycisku zmienia się na opisowy ("Logowanie..." zamiast "Zaloguj się")
- **Spinner lub progressbar** - musi się ruszać (statyczna ikona "loading"
  wygląda jak zamrożona)

Spinner zaimplementowany w `Spinner` class w `login_screen.py` - jest
generyczny, można go reużyć w innych miejscach (subscription_tab przy
ładowaniu planów, dashboard przy odświeżaniu danych).

#### L-B3. Guard przeciwko podwójnym kliknięciom

`_auth_in_progress = True/False` - flag w klasie. Bez tego user może
kliknąć "Zaloguj się" 5 razy podczas cold startu i odpalić 5 wątków
jednocześnie. To nie tylko obciąża serwer, ale też powoduje race conditions
w UI (5 callbacków próbuje zmienić ten sam stan).

Wzorzec do reużycia w każdym async slotcie GUI:
```python
def _start_operation(self):
    if self._operation_in_progress:
        return  # ignoruj
    self._operation_in_progress = True
    self._button.setEnabled(False)
    # ... spawn wątku

def _on_done(self, ...):
    self._operation_in_progress = False
    self._button.setEnabled(True)
    # ... pokaz wynik
```

#### L-B4. Signal przekazuje wszystkie dane jednym shotem

Pierwszy szkic miał `_AuthThread` z osobnymi signalami `success/failure`. Lepsze
rozwiązanie: jeden signal `result(action, ok, msg, user_id, subscription)` -
slot dostaje cały pakiet i sam decyduje co robić.

To upraszcza:
- Jeden connect zamiast dwóch
- Slot widzi cały kontekst (czy login czy register)
- Łatwiej rozszerzyć (kolejne pole = +1 argument signal)

---

## C) Fail-open w warstwie API

### C1. Bug: błąd INSERT do `login_history` blokował logowanie

**Commit:** `82ab748 fix: fail-open audit logowania w login_history`

**Co się działo:**

W `server.py:/api/login` po sprawdzeniu hasła był INSERT do `login_history`.
Jeśli ten INSERT padł (z dowolnego powodu - bug A1, zbyt długi user_agent,
problem z sekwencją, itd.), wyjątek leciał do outerowego `except` i zwracał
HTTP 500. **User z poprawnym hasłem nie mógł się zalogować.**

To jest błąd architektoniczny - audit (zapis historii) ma być wsparciem dla
głównej operacji (zalogowania), nie blokerem.

**Fix:**

```python
def _log_login_attempt(conn, user_id, success, ip_address, user_agent, failure_reason=None):
    """Zapisuje wpis do login_history - fail-open."""
    try:
        cur = conn.cursor()
        # ... INSERT ...
        conn.commit()
        cur.close()
    except Exception as e:
        try:
            conn.rollback()  # ZAWSZE rollback po blędzie psql - inaczej cały
        except Exception:    # connection jest aborted
            pass
        print(f"[WARN] login_history insert failed: {e}",
              file=sys.stderr, flush=True)
        # NIE re-raise - logowanie usera idzie dalej
```

Wywoływane zamiast inline INSERT-ów w `/api/login`.

### Lekcje fail-open

#### L-C1. Audit jest best-effort, nigdy blocker główniej operacji

Zapisz w pamięci listę operacji **wspierających** (best-effort) vs **głównych**
(blocker przy błędzie):

| Operacja | Typ | Co przy błędzie |
|----------|-----|-----------------|
| Sprawdzenie hasła | główna | HTTP 401, user nie loguje |
| Pobranie subskrypcji | główna | HTTP 500, user widzi błąd |
| Zapis `login_history` | wspierająca | log + kontynuuj |
| Inkrementacja `daily_usage` przy `/api/round/use` | główna | HTTP 429, bot nie startuje |
| Audit do `audit_log` (trigger SQL) | wspierająca | log + kontynuuj |

Jeśli operacja jest "wspierająca" - opakuj w try/except, rollback, log do
stderr, kontynuuj.

#### L-C2. ZAWSZE rollback po błędzie psycopg2

Tu jest haczyk PostgreSQL: po błędzie SQL **cała transakcja jest aborted**.
Następne `cur.execute(...)` na tym samym connection rzuci błąd
"current transaction is aborted, commands ignored until end of transaction
block".

Rozwiązanie: po błędzie zawsze `conn.rollback()`. Wtedy connection wraca do
użyteczego stanu i kolejne queries działają.

Wzorzec helpera:
```python
try:
    cur.execute(...)
    conn.commit()
except Exception as e:
    try:
        conn.rollback()
    except Exception:
        pass  # rollback też może paść jeśli connection martwe
    # log + kontynuuj
```

#### L-C3. Log do stderr na Render = automatycznie w logach platformy

Render zbiera stdout i stderr z workerów Gunicorn i pokazuje w dashboard
("Logs" tab). Czyli nie trzeba konfigurować osobnego loggera - wystarczy:

```python
print(f"[WARN] ...", file=sys.stderr, flush=True)
```

`flush=True` jest ważne - bez tego output jest buforowany i może nie pojawić
się w logach przed crashem workera. Render free tier ma agresywny restart
przy braku ruchu.

#### L-C4. Lista miejsc w server.py do sprawdzenia pod kątem fail-open

W tej sesji naprawiony tylko `_log_login_attempt`. Inne miejsca, które
mogą mieć ten sam bug (audit jako blocker):

- `/api/register` - tworzenie usera + audit. Czy audit może wybić rejestrację?
- `/api/round/use` - inkrementacja `daily_usage` + zapis przyrostu rund w `audit_log`?
- Triggery SQL `audit_*` - czy zapis do `audit_log` może wybić główną operację?

Do sprawdzenia w przyszłości - nie blokuje, ale warto przejrzeć przed
kolejnym releasem.

---

## D) Build i release

Pełny dokument: **[build-i-release.md](build-i-release.md)**.

Kluczowe punkty (powtórka):

### L-D1. Build success ≠ paczka działa

PyInstaller wypisuje `Build complete!` i exit 0 nawet gdy nie znalazł
modułów - tylko zapisuje ostrzeżenie do `warn-*.txt`. **Sprawdzaj zawartość
paczki, nie tylko exit code.**

### L-D2. Spadek rozmiaru paczki to ALARM

v1.2.5: 107 MB → popsuta v1.2.6: 48 MB. Spadek 55%. To było jednoznaczne
ostrzeżenie że ~60 MB modułów zniknęło. Tłumaczenie "lepsza kompresja" było
błędne.

**Reguła:** spadek >30% bez zmiany w `requirements.txt` = bug do zdiagnozowania.

### L-D3. PyInstaller .spec - niespójne ścieżki

W `app/BeSafeFish.spec` PyInstaller 6.x interpretuje:
- `Analysis(['besafefish.py'])` (script), `datas`, `icon` → względem **.spec**
- `pathex` → względem **CWD** (z którego uruchamiasz `py -m PyInstaller`)

Build ZAWSZE z roota repo: `py -m PyInstaller app/BeSafeFish.spec --clean -y`.

### L-D4. Test runtime przed releasem - obowiązkowy

Build debug version (`console=True`, `uac_admin=False`) → odpal `.exe` →
zaloguj → klik **Start** → bot ma startować bez crash. Bez tego testu nie
wrzucaj na release.

---

## Meta-lekcja: dlaczego nie zauważyłem

Po fakcie wszystkie te lekcje wydają się oczywiste. Pytanie:
**dlaczego się przeoczyły w trakcie?**

### Heurystyki które zawiodły

1. **"Build się udał = paczka jest dobra"** - błędne. PyInstaller exit 0
   oznacza tylko że kompilacja skończyła się bez fatal error. Nie weryfikuje
   poprawności runtime.

2. **"Mniejsza paczka = lepsza kompresja"** - błędne dla projektów Python
   z natywnymi bibliotekami. Cv2, numpy, onnxruntime są już skompresowane
   - dalsza redukcja oznacza usunięcie zawartości, nie kompresję.

3. **"Zmiana w jednym pliku = mała zmiana"** - błędne dla `.spec`.
   PyInstaller jest skomplikowany, każda zmiana wymaga pełnego cyklu
   testowego.

4. **"Dokumentacja w komentarzu .spec mówi X"** - błędne, jeśli
   dokumentacja jest sprzed restrukturyzacji repo i nie była aktualizowana.
   Memory miało rację, komentarz w .spec się mylił.

5. **"Memory mówi X"** - memory mogą być nieaktualne. Zawsze weryfikuj
   przeciwko kodowi.

### Co mogło to wyłapać wcześniej

- **Test runtime jako część workflow** - przed wrzuceniem na release zawsze
  odpal .exe. Bez tego = blind release.
- **Porównanie z poprzednią wersją** - `v1.2.5: 107 MB, v1.2.6: 48 MB` -
  diff rozmiaru powinien być pierwszą rzeczą do sprawdzenia.
- **CI/CD który buduje paczkę i odpala smoke test** - dłuższy projekt:
  GitHub Actions z Windows runnerem buduje .exe, odpala go z `--smoke-test`
  flagą która tylko sprawdza czy GUI startuje i bot się inicjalizuje
  (bez prawdziwego API). To by wyłapało regresję automatycznie.

### Lekcja dla AI (mojej przyszłej iteracji)

**Gdy widzisz coś nieoczekiwanego (spadek rozmiaru, mniej plików, dziwna
liczba) - traktuj to jako sygnał, nie ciekawostkę.** Pierwsza myśl powinna
brzmieć "co się popsuło?" a nie "ciekawe, dlaczego tak się stało".

Optymizm w debuggingu prowadzi do wpadek. Jeśli coś wygląda dziwnie -
zatrzymaj się i sprawdź zanim ogłosisz sukces.

---

## Co poszło **dobrze** w tej sesji (warto powtarzać)

Nie wszystko było wpadką. Kilka rzeczy działało jak powinno:

### + Osobne commity per zmiana

Sesja miała 9 commitów na main (regulamin, dotenv CVE, link, SQL fix,
login async, fail-open, bump, .spec fix x2, rozmiar zip x2). Każdy commit
ma jeden cel, jeden commit message, łatwo cofnąć pojedynczą zmianę.

To pomogło przy diagnozowaniu wpadki - widać było dokładnie który commit
złamał build (`6d64437 fix: BeSafeFish.spec`), bez przeszukiwania zbiorczych
commitów.

### + Memory zapisane od razu

Po incydencie `feedback_pyinstaller_spec_paths.md` i
`feedback_release_runtime_test.md` powstały od razu, nie "później".
Przyszłe sesje (i przyszły ja) zaczynają pracę z tym kontekstem.

### + Dokument w repo > tylko memory

Memory są prywatne (na moim koncie). Dokument w repo (`build-i-release.md`,
ten plik) widzi każdy kto klonuje projekt - Ty, ja w innej maszynie,
hipotetyczny kontrybutor. **Wnioski z incydentu powinny żyć w repo.**

### + Pre-commit hook złapał potencjalne fałszywe alarmy

Hook `password\s*[:=]` blokował commity z `password = self._password_input.text()`
- false positive (lokalna zmienna). To irytujące, ale **lepszy false positive
niż false negative**. Hook robi swoją robotę.

Potencjalna poprawka na przyszłość: regex może być sprytniejszy
(`password\s*=\s*["']` zamiast `password\s*=`), żeby pomijał lokalne zmienne.
Ale to side-quest.
