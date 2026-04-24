# Etap 2: Refaktor bota pod Strategy pattern

**Branch:** `etap2-fishing-modes-strategy` (zakladam nowego)
**Cel:** Wydzielic logike trybu "rybka - klik" z `KosaBot` do osobnego modulu.
**Kryterium sukcesu:** Bot zachowuje sie **identycznie** jak dzis + dodanie nowego trybu w Etapie 3 = napisanie jednego pliku obok, zero ruszania `fish_click.py`.

**Status:** W TRAKCIE

Po kompresji kontekstu: wczytaj ten plik zanim zaczniesz.

---

## Cel wyzszy (pamietaj!)

Kolejne tryby bota (Etap 3 = dymek+spacja, oraz ewentualne przyszle) musza byc
dodawane jako **nowy plik obok istniejacych**, bez modyfikacji kodu innych
trybow. Interfejs `FishingMode` ma byc wystarczajaco ogolny, zeby Tryb 2
(zupelnie inna minigra z spacja N razy) sie w nim zmiescil **bez wyjatkow**.

---

## Ustalenia z uzytkownikiem

- **Bez zmiany zachowania** - bot dziala dzis i ma dzialac po refaktorze identycznie
- Dead code (`FishNetInference`, `_detect_frame()`) zostaje - refaktor nie jest od czyszczenia
- Interfejs luzny (nie sztywna ABC z abstractami - Tryb 2 moze byc zupelnie inny)
- Kazdy tryb w osobnym pliku w `src/fishing_modes/`
- `KosaBot` staje sie dispatcherem

---

## Architektura po refaktorze

### Struktura plikow

```
versions/tryb1_rybka_klik/post_cnn/src/
  bot.py                  (krotki, dispatcher + wspolna petla run())
  fishing_modes/
    __init__.py
    base.py               (opcjonalnie - lekki protocol/base klasa)
    fish_click.py         (cala obecna logika Trybu 1)
  config.py               (bez zmian)
  fishing_detector.py     (bez zmian)
  input_simulator.py      (bez zmian)
  screen_capture.py       (bez zmian)
```

### Kontrakt `FishingMode` (lekki)

Minimum ktore **kazdy** tryb musi miec (uzywane przez `KosaBot.run()`):

```python
class FishingMode:
    """Kontrakt dla trybow. Nie jest ABC - implementacje mozna robic od zera."""

    name: str                                     # "Mini-gra lowienie ryb" - do logow

    def wait_for_start(self, timeout: float) -> bool:
        """Czeka az minigra zacznie sie. Return True = zaczela, False = timeout."""

    def play_round(self) -> bool:
        """Odgrywa jedna runde. Return True = ukonczona, False = przerwana przez stop."""

    def wait_for_end(self, timeout: float = 5.0) -> None:
        """Czeka az okno minigry zniknie (pauza przed nastepna runda)."""
```

Minigry moga sie roznic **wszystkim** poza tymi 3 metodami. Np. Tryb 2 nie uzywa
`capture` ani `input.click()` - uzywa `input.press_space()` - nie muszą dzielić
tej samej dependency injection.

### Przeplyw w `KosaBot.run()`

```python
def run(self):
    self.running = True
    self._log("=" * 50)
    self._log(f"  BOT: tryb '{self.mode.name}'")
    self._log("=" * 50)

    # znajdz okno gry (uniwersalne dla wszystkich trybow Metin2)
    self._focus_game_window()

    try:
        while self.running:
            # sprawdz limit rund
            if self._round_check_callback:
                allowed, msg = self._round_check_callback()
                if not allowed:
                    self._log(f"[BOT] LIMIT: {msg}")
                    break
                if msg:
                    self._log(f"[LIMIT] {msg}")

            self.total_rounds += 1
            self._log(f"\n===== RUNDA {self.total_rounds} =====")

            # delegacja do trybu
            self.input.start_fishing_round()   # F4 + SPACE (uniwersalne Metin2)

            if not self.mode.wait_for_start(timeout=10.0):
                self._log("[BOT] Minigra sie nie pojawila, probuje ponownie...")
                continue

            if not self.mode.play_round():
                break  # przerwano przez stop()

            self.mode.wait_for_end()
            time.sleep(3.0)
    except KeyboardInterrupt:
        self._log("\n[BOT] Przerwano Ctrl+C.")
    finally:
        self.running = False
```

**Uwaga:** `self.input.start_fishing_round()` (F4 bait + SPACE cast) jest
**uniwersalne dla obu minigier w Metin2** - tak rozpoczyna sie kazda runda.
Zostaje w `KosaBot`. Jesli przyszly tryb bedzie mial inny start - wyciagniemy
to do mode'a pozniej.

### Dispatcher

```python
def __init__(self, mode: str = "fish_click", debug=False, use_cnn=True,
             log_callback=None, round_check_callback=None):
    # wspolne dependencies
    self.capture = ScreenCapture()
    self.input = InputSimulator()
    self.debug = debug
    self.running = False
    self.total_rounds = 0
    self._log_callback = log_callback
    self._round_check_callback = round_check_callback

    # dispatcher do konkretnego trybu
    if mode == "fish_click":
        from src.fishing_modes.fish_click import FishClickMode
        self.mode = FishClickMode(
            debug=debug,
            use_cnn=use_cnn,
            log_callback=self._log,
            capture=self.capture,
            input_sim=self.input,
            is_running=lambda: self.running,
        )
    else:
        raise ValueError(f"Nieznany tryb: {mode!r}")
```

### Co trafia do `FishClickMode` (z obecnego `bot.py`)

**Metody do przeniesienia (1:1, bez zmian logiki):**
- `_clamp_to_circle()` - pomocnicza
- `_verify_fish_patch()` - PatchCNN
- `_detect_frame()` - dead code, zostaje
- `wait_for_fishing_minigame()` -> `wait_for_start()`
- `play_fishing_round()` -> `play_round()`
- `_wait_for_minigame_close()` -> `wait_for_end()`
- `_show_debug()` - debug overlay

**Stale do przeniesienia:**
- `SAFE_RADIUS`, `SAME_SPOT_RADIUS`, `SAME_SPOT_MAX_CLICKS`
- `PATCH_SIZE`, `PATCH_HALF`, `PATCH_CNN_THRESHOLD`

**Dependencies ktore `FishClickMode` laduje sam (w __init__):**
- `FishingDetector` (klasyczny HSV)
- `FishNetInference` (dead code, ale zostaje)
- `FishShapeDetector`
- `PatchCNN` (ONNX session)

**Dependencies przekazywane z KosaBot:**
- `capture: ScreenCapture`
- `input_sim: InputSimulator`
- `log_callback: Callable[[str], None]`
- `is_running: Callable[[], bool]` (wrap na `self.running` KosaBot - zeby mode mogl sprawdzac czy przerwano)

---

## Plan commitow

### [ ] Commit 1: refactor: przygotowanie pakietu fishing_modes (pusty szkielet)
- `mkdir src/fishing_modes/`
- `src/fishing_modes/__init__.py` (pusty)
- `src/fishing_modes/base.py` (dokumentacja kontraktu FishingMode, bez ABC)
- Nic w logice - tylko przygotowanie strukturalne

### [ ] Commit 2: refactor: wydzielenie FishClickMode z KosaBot
- `src/fishing_modes/fish_click.py` - klasa `FishClickMode` z cala logika specyficzna dla trybu rybka-klik
- `src/bot.py` - skrocony do dispatchera:
  - __init__ przyjmuje `mode: str`
  - laduje odpowiedni FishingMode
  - run() deleguje do mode
  - stop() zostaje
  - _check_admin zostaje jako helper modulowy
- Smoke test: bot startuje, zglasza "nie znaleziono okna Metin2" (jak dzis)

### [ ] Commit 3: chore: BotWorker przekazuje mode do KosaBot
- `app/gui/bot_worker.py` - przekazanie `mode=self._enabled_modes[0]` do KosaBot zamiast samego use_cnn
- Zgodnosc wsteczna: jesli `enabled_modes` puste, domyslnie `"fish_click"`
- Smoke test: uruchomienie appki -> START -> bot startuje identycznie jak dzis

### [ ] Commit 4: chore: usuniecie ETAP2_PLAN.md po zakonczeniu
- ten plik
- push brancha + merge do main (fast-forward)

---

## Smoke testy

### Po Commit 2 (fish_click.py wydzielone)
- [ ] `py app/besafefish.py` - appka startuje bez bledu
- [ ] Import dziala: `from src.bot import KosaBot; KosaBot(mode="fish_click", ...)`
- [ ] `from src.fishing_modes.fish_click import FishClickMode` dziala

### Po Commit 3 (BotWorker)
- [ ] Logowanie w appce -> wybor Trybu 1 -> START -> bot startuje
- [ ] Bot wola `wait_for_start()` i zglasza "Minigra sie nie pojawila" albo "nie znaleziono okna Metin2"
- [ ] Zamkniecie appki - czyste, bez errorow

### Finalny (z Metin2 jesli uzytkownik ma pod reka)
- [ ] Uruchomienie bota w Metin2 - zachowuje sie identycznie jak przed refaktorem:
  - detekcja bialego/czerwonego kola
  - klikniecie rybki
  - pauzy miedzy rundami
  - same-spot limiter
  - PatchCNN weryfikacja
- [ ] Log pokazuje "Pipeline: HSV -> bg-sub -> shape fallback -> PatchCNN weryfikacja" (albo bardzo podobnie)

---

## Ryzyka i jak je niwelujemy

### Ryzyko 1: Cykliczne importy
`FishClickMode` nie importuje `KosaBot`. Wszystko dostaje przez konstruktor (dependency injection).

### Ryzyko 2: Stan rundy pomieszany (flaga running na bot, petla w mode)
`running` zostaje w `KosaBot`. Mode dostaje callable `is_running: () -> bool`. Wewnatrz mode: `while self._is_running(): ...`. Stop() na bocie przerywa petle w mode poprzez False z callable.

### Ryzyko 3: Subtelna zmiana zachowania przy przenoszeniu metod
Copy-paste logiki 1:1, zero refaktoru wnetrznych metod. Zmienia sie tylko miejsce zamieszkania i sposob dostepu do zaleznosci (przez `self._capture` zamiast `self.capture` ktore byly na bocie).

### Ryzyko 4: Kontrakt okaze sie za waski dla Trybu 2
`play_round()` musi obslugiwac zarowno "klik na rybke" jak i "spacja N razy".
Planuje: return `bool` (True=ok, False=przerwane), bez parametrow. Kazdy tryb
uzywa wlasnych zaleznosci.

Jesli w Etapie 3 okaze sie ze potrzebujemy czegos innego - rozszerzymy
kontrakt. Nie rzezbimy abstrakcji ponad miare teraz.

---

## Po zakonczeniu Etapu 2

1. Merge `etap2-fishing-modes-strategy` -> `main` (fast-forward)
2. Feature branch usunac lub zostawic jako archiwum (decyzja usera)
3. Aktualizacja `versions/tryb1_rybka_klik/post_cnn/README.md` - dopisanie sekcji
   "Struktura" z nowym pakietem `fishing_modes/` (osobny commit docs)
4. Aktualizacja `versions/tryb1_rybka_klik/post_cnn/TODO.txt` - odhaczenie zadan
   ktore refaktor pokryl (np. dead code widoczny w fish_click.py)
5. Przygotowanie do Etapu 3 (Tryb 2 bubble_space - wymaga screenshota dymka
   od usera, detekcji cyferki, press_space_n_times w input_simulator)

---

## Post-mortem (wypelnic po zakonczeniu)

- Jakie niespodzianki wystapily?
- Czy kontrakt FishingMode okazal sie OK, czy wymagal zmiany?
- Ile czasu zajelo?
- Co przydaloby sie zapisac do memory na przyszlosc?
