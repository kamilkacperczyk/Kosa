# Build .exe i release - lekcje i checklist

Dokument powstał po incydencie 2026-04-27, gdy wypuszczony został release v1.2.6 z popsutą paczką (.zip 48 MB zamiast prawidłowych 118 MB) - bot crashował przy starcie z `No module named 'src'`. Userzy pobrali wadliwą wersję.

Cel: nie powtorzyć tej samej akcji.

---

## Co się stało

### Sekwencja błędów

1. **Restrukturyzacja repo (commit `e201114`, 2026-04-24)** przeniosła launcher i .spec z `versions/post_cnn/` do `app/`. Stary `BeSafeFish.spec` miał ścieżki działające w starej strukturze. Po przenosinach trzeba było je zaktualizować - co zostało zrobione, ale niepełnie.

2. **Mój błędny "fix" .spec (commit `6d64437`)**: zauważyłem że build pada z `app\\app\\besafefish.py' not found` i założyłem, że WSZYSTKIE ścieżki w .spec są względem pliku .spec. Zmieniłem wszystko (script, datas, pathex, icon) usuwając prefix `app\\`. Build potem zaczął się udawać.

3. **Build "się udawał" ale paczka była niepelna**: PyInstaller wypisał `Build complete!` i exit code 0, mimo że `pathex='..\\versions\\...'` interpretowane względem cwd nie wskazywało na `BeSafeFish/versions/...` tylko na `Desktop/Repos/versions/...` (folder który **nie istnieje**). PyInstaller nie wykrył braku, tylko **cicho nie wciągnął modułów bota** (`src.bot`, `src.fishing_modes`, etc).

4. **Skok rozmiaru z 107 MB → 48 MB**: traktowane przeze mnie jako "lepsza kompresja" (błędna interpretacja). To był sygnał alarmowy że ~60 MB modułów (cv2, numpy, onnxruntime + src/) zniknęło.

5. **Brak testu .exe lokalnie przed releasem**: wrzuciłem .zip na GitHub, zaktualizowałem stronę, ogłosiłem ukończenie. User pobrał, wszystko ładnie wstało, klik "Start" → crash.

### Dlaczego to się udało prześliznąć

PyInstaller 6.x **nie raportuje braku modułów jako błąd buildu**. Jeśli `pathex` wskazuje na nieistniejący folder, PyInstaller zapisuje cichą notatkę w `build/<name>/warn-<name>.txt` i kontynuuje. EXE się buduje, ale jest niekompletne. Crash dopiero w runtime, gdy kod próbuje `from src.bot import KosaBot`.

---

## Faktyczna reguła ścieżek w PyInstaller 6.x

**Ścieżki w `.spec` są interpretowane względem różnych katalogów w zależności od pola.** To jest niespójność biblioteki, ale jest stała i przewidywalna.

| Pole | Względem czego |
|------|---------------|
| `Analysis(['besafefish.py'])` (script) | **pliku .spec** |
| `datas=[...]` | **pliku .spec** |
| `icon=[...]` | **pliku .spec** |
| `pathex=[...]` | **CWD** (z którego uruchamiamy `py -m PyInstaller`) |
| `binaries=[...]` | **pliku .spec** |
| `hiddenimports` | nieistotne (to nazwy modułów, nie ścieżki) |

### Konsekwencja dla naszego repo

`.spec` siedzi w `app/`, build odpalamy z roota repo (`BeSafeFish/`).

```python
a = Analysis(
    ['besafefish.py'],  # względem app/ (.spec) → app/besafefish.py
    pathex=[
        'app',                                       # względem BeSafeFish/ (cwd) → BeSafeFish/app
        'versions\\tryb1_rybka_klik\\post_cnn',     # względem cwd → BeSafeFish/versions/...
    ],
    datas=[
        ('gui\\fish.ico', 'gui'),                    # względem app/ → app/gui/fish.ico
        ('..\\versions\\tryb1_rybka_klik\\post_cnn\\cnn\\models\\fish_patch_cnn.onnx', 'cnn\\models'),
        # względem app/ → app/../versions/... = BeSafeFish/versions/...
    ],
    icon=['gui\\fish.ico'],  # względem app/
)
```

Druga połowa konfiguracji (icon, datas) wygląda paradoksalnie obok pathex, ale tak musi być.

---

## Co konkretnie pakuje PyInstaller

Po zbudowaniu w `dist/BeSafeFish/` znajdzie się:

```
BeSafeFish/
├── BeSafeFish.exe              ← ~5 MB - bootloader + spakowany PYZ archive (pure-Python)
└── _internal/
    ├── PIL/                    ← biblioteki binarne z .pyd/.dll
    ├── PySide6/
    ├── cv2/
    ├── numpy/                  ← OpenCV, numpy, ONNX runtime - łącznie ~150 MB rozpakowane
    ├── onnxruntime/
    ├── shiboken6/
    ├── win32/
    ├── cnn/models/             ← model ONNX wciągnięty przez datas (300 MB)
    ├── gui/                    ← assets i ikony wciągnięte przez datas
    ├── base_library.zip        ← stdlib spakowany
    └── *.dll, *.pyd            ← runtime DLL Windows + Python
```

**Pure-Python moduły bota (`src.bot`, `src.fishing_modes.fish_click`, `cnn.inference`) są wewnątrz `BeSafeFish.exe`** w archiwum PYZ. Nie ma ich jako osobnych folderów `src/` czy `cnn/` - tylko model ONNX z `datas` jest fizycznie widoczny w `_internal/cnn/models/`.

To jest **mylący punkt**: gdy widzisz że `dist/BeSafeFish/` nie zawiera folderu `src/`, **nie znaczy to że bot nie został spakowany**. Trzeba zaglądnąć do PYZ archive (zob. weryfikacja niżej).

---

## Weryfikacja paczki PRZED releasem (obowiązkowa)

### 1. Build i sprawdzenie struktury

```bash
# Z roota repo
py -m PyInstaller app/BeSafeFish.spec --clean -y
```

```bash
du -sh dist/BeSafeFish/
# Oczekiwane: ~290 MB (Python 3.14 + PySide6 6.10 + cv2 + numpy + onnxruntime + model ONNX)
# ALARM: <200 MB → sprawdz co zniknelo
```

### 2. Sprawdzenie czy moduły bota są w PYZ

```bash
grep -oE "'src\.[a-z._]+'" build/BeSafeFish/PYZ-00.toc | sort -u
```

Oczekiwane (przykład):
```
'src.bot'
'src.config'
'src.fishing_detector'
'src.fishing_modes'
'src.fishing_modes.fish_click'
'src.input_simulator'
'src.screen_capture'
```

**Pusta lista = ALARM.** PyInstaller nie znalazł `src/`. Sprawdź `pathex` w .spec.

### 3. Sprawdzenie hidden imports w `warn-*.txt`

```bash
grep "missing module" build/BeSafeFish/warn-BeSafeFish.txt | grep -vE "Quartz|Xlib|AppKit|olefile|tkinter|matplotlib"
```

**Quartz, Xlib, AppKit** to moduły dla macOS/Linux (nieistotne na Windowsie).
**olefile, tkinter, matplotlib** są intencjonalnie wykluczone w `excludes`.

Wszystko inne pojawiające się w wynikach to potencjalny problem.

### 4. Build debug i odpalenie .exe lokalnie (najważniejszy krok)

To jest **kluczowy test**. Budujemy wariant z konsolą i bez UAC żeby widzieć błędy.

#### Krok 4a - tymczasowo zmodyfikuj .spec:

W `app/BeSafeFish.spec`:
- `console=False` → `console=True`
- `uac_admin=True` → `uac_admin=False`
- `name='BeSafeFish'` w **COLLECT** (drugie wystąpienie, nie EXE) → `name='BeSafeFish_debug'`

#### Krok 4b - zbuduj:

```bash
py -m PyInstaller app/BeSafeFish.spec --noconfirm
```

Powstanie `dist/BeSafeFish_debug/BeSafeFish.exe` (debug, z konsolą, bez UAC).

#### Krok 4c - **odpal z eksploratora Windows i przejdź pełen flow**:

1. Dwuklik `BeSafeFish.exe` (zwykły, nie jako admin)
2. **Czarne okno konsoli** powinno wyskoczyć obok GUI - jeśli GUI crashuje, błąd będzie widoczny w konsoli
3. Zaloguj się
4. **Klik Start** w dashboardzie - **bot MUSI wystartować bez crash**
5. W konsoli zobaczysz logi typu `[BOT] Inicjalizacja...`, `[BOT] Aktywne tryby: fish_click`, `[BOT] Uruchamiam glowna petle...`

Jeśli na którymkolwiek etapie pojawi się traceback z `ModuleNotFoundError`, `ImportError` albo `[BLAD] No module named '...'` - **paczka jest popsuta. NIE wrzucaj jej na release.**

#### Krok 4d - przywróć .spec do produkcji:

Cofnij zmiany z 4a (`console=False`, `uac_admin=True`, `name='BeSafeFish'`).

#### Krok 4e - rebuild produkcji:

```bash
rm -rf dist/BeSafeFish dist/BeSafeFish_debug build
py -m PyInstaller app/BeSafeFish.spec --clean -y
```

### 5. Pakowanie i upload

```bash
cd dist
py -c "import shutil; shutil.make_archive('BeSafeFish', 'zip', '.', 'BeSafeFish')"
ls -la BeSafeFish.zip
# Oczekiwane: ~115-130 MB

cd ..
gh release upload v<X.Y.Z> dist/BeSafeFish.zip --clobber --repo kamilkacperczyk/BeSafeFish
```

### 6. Aktualizacja rozmiaru na stronie

`app/website/index.html` linia z `download-size` - zaktualizuj MB do faktycznego rozmiaru .zip.

---

## Sygnały alarmowe (czerwone flagi)

Następujące zjawiska to **nie ciekawostki, tylko ostrzeżenia**:

### Spadek rozmiaru paczki o >30% między wersjami
v1.2.5 → 107 MB. v1.2.6 popsuty → 48 MB. Spadek 55%. **To było jednoznaczne ostrzeżenie że coś zniknęło.**

Możliwe nieszkodliwe przyczyny: usunięcie zależności z `requirements.txt`, przejście na lighter binding (np. `opencv-python-headless`). Jeśli takiej zmiany nie było, **traktuj spadek jako bug do zdiagnozowania**.

### `Build complete!` z exit 0 ale bez ostrzeżeń
PyInstaller jest "optymistyczny" - nawet gdy nie znajdzie modułu, zapisze warning do pliku i kontynuuje. **Nie polegaj na exit code.** Sprawdź `warn-*.txt` i zawartość PYZ.

### `pathex` wskazuje na ścieżkę zawierającą `..\\` lub spoza repo
Łatwo o pomyłkę kierunku ścieżek względnych. Po edycji .spec zawsze sprawdź log buildu pod kątem linii:
```
106 INFO: Module search paths (PYTHONPATH):
['C:\\Users\\...\\BeSafeFish',
 ...
 'C:\\Users\\...\\BeSafeFish\\app',
 'C:\\Users\\...\\BeSafeFish\\versions\\tryb1_rybka_klik\\post_cnn']
```

Wszystkie ścieżki muszą **zaczynać się od `BeSafeFish\`** (lub jego absolutnego rozszerzenia). Jeśli widzisz `Desktop\\Repos\\versions\\...` (bez `BeSafeFish` w środku) - pathex jest błędne.

### Brak folderu w `_internal/` po buildzie
Ważne: brak folderu `src/`, `cnn/` (poza `cnn/models/`), `gui/` (poza tym z datas) w `dist/BeSafeFish/_internal/` jest **normalny** - są w PYZ archive wewnątrz .exe.
Brak folderu `cv2/`, `numpy/`, `onnxruntime/`, `PIL/` jest **nienormalny** - to biblioteki binarne, muszą być fizycznie obecne.

---

## Najważniejsze lekcje

### 1. Spadek rozmiaru paczki to ALARM, nie ciekawostka
Po incydencie: jeśli paczka jest mniejsza niż poprzednia wersja, zatrzymaj się i sprawdź dlaczego. Domyślne wytłumaczenie "lepsza kompresja" jest niemal zawsze błędne dla projektów Python z natywnymi bibliotekami.

### 2. Build success ≠ paczka działa
PyInstaller exit 0 oznacza tylko że kompilacja się skończyła. Nie weryfikuje runtime. **Zawsze odpal .exe lokalnie i przejdź flow** - login + start bota - przed wrzuceniem na release.

### 3. Niespójność ścieżek w PyInstaller 6.x jest realna i nie do "naprawienia"
Nie próbuj uspójnić - to celowe (lub historyczne). Akceptuj regułę: script/datas/icon = .spec, pathex = cwd.

### 4. Przy dużych refaktorach struktury repo - .spec wymaga osobnej weryfikacji
Restrukturyzacja `versions/post_cnn/ → app/` z 24 kwietnia zmieniła lokalizację .spec. Wszystkie ścieżki w .spec wymagały aktualizacji. To było zrobione, ale bez testu runtime - co zaowocowało problemem 3 dni później.

### 5. Mała trzylinijkowa zmiana w .spec może wyzerować całą paczkę
PyInstaller jest skomplikowany. **Każda zmiana w .spec wymaga pełnego cyklu testowego (build debug → odpal → bot startuje).**

### 6. Hooks PyInstallera nie ratują przed dynamic imports
Bot ładuje moduły przez `sys.path.insert(versions_dir, ...)` w runtime. PyInstaller nie analizuje tego. **Wszystkie moduły wciągane dynamicznie muszą być na liście `hiddenimports`** (cv2, numpy, mss, pyautogui, pydirectinput, pygetwindow, PIL, onnxruntime).

---

## Checklist release v1.X.Y (do skopiowania)

```
[ ] git push wszystkich zmian na main przed buildem (Render auto-deployuje serwer)
[ ] Bump wersji w app/gui/dashboard.py (footer) i app/website/index.html (karta release)
[ ] py -m PyInstaller app/BeSafeFish.spec --clean -y
[ ] du -sh dist/BeSafeFish/ - sprawdzic czy ~290 MB
[ ] grep "'src\." build/BeSafeFish/PYZ-00.toc - sprawdzic czy src.* jest
[ ] Build DEBUG version (console=True, uac_admin=False, name='BeSafeFish_debug')
[ ] Odpalic dist/BeSafeFish_debug/BeSafeFish.exe i przejsc:
    [ ] GUI wstaje
    [ ] Login (poprawny) - dashboard sie laduje
    [ ] Klik Start - bot startuje BEZ crash
[ ] Przywrocic produkcyjny .spec
[ ] Czysty rebuild produkcyjny (rm -rf dist build)
[ ] Pakowanie do .zip (shutil.make_archive)
[ ] gh release create v<X.Y.Z> dist/BeSafeFish.zip --title ... --notes ...
    LUB: gh release upload v<X.Y.Z> dist/BeSafeFish.zip --clobber (jesli release juz istnieje)
[ ] Aktualizacja rozmiaru w app/website/index.html
[ ] Commit + push aktualizacji rozmiaru
```
