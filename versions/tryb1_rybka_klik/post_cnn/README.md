# Wariant: POST CNN

**Status:** DZIALAJACY (przetestowany na zywo)
**Data utworzenia:** 2026-03-16
**Ostatnia aktualizacja:** 2026-03-17 (pierwotnie) / 2026-04-24 (restrukturyzacja repo)
**Baza:** kopia `pre_cnn` + modul CNN + PatchCNN weryfikacja

## Opis ogolny

Bot do automatycznego lowienia ryb w grze Metin2 (serwer Eryndos).
Wersja POST CNN — wielowarstwowy pipeline detekcji rybki:

1. Klasyczny detektor HSV — stan gry (bialy / czerwony / brak okregu)
2. Background subtraction — pozycja rybki (mediana 15 klatek)
3. FishShapeDetector — fallback pozycji (tlo referencyjne + blob)
4. FishPatchCNN (ONNX) — weryfikacja kandydatow 32x32 (fish / not_fish)

Pipeline jest aktywny w `play_fishing_round()` — kazda klatka przechodzi
przez wszystkie warstwy. CNN odrzuca false positives (napisy, splash, szum).

## Aktywny pipeline detekcji

```
Klatka
  |
  v
detect_circle_color() [HSV]       -> "white" / "red" / "none"
  |
  v
find_fish_position() [bg-sub]     -> (x,y) lub None
  | (jesli None)
  v
find_fish_simple() [FishShape]    -> (x,y) lub None
  | (jesli znaleziono kandydata)
  v
_verify_fish_patch() [PatchCNN]   -> akceptuj / odrzuc (prob > 0.5)
  | (jesli potwierdzony)
  v
_clamp_to_circle()                -> bezpieczna pozycja (max r=54px)
  |
  v
click_at_fish_fast()              -> klik LPM przez pydirectinput
```

## Co robi kazdy komponent

### `detect_circle_color()` — `fishing_detector.py`
Konwersja BGR → HSV, liczy jasne piksele (S<40, V>220).
`>=400` px → `"white"`; `<400` px → `"red"`.
Najpierw sprawdza `is_fishing_active()` (jasnosc >400 = minigra aktywna).
Czas: ~0.5 ms.

### `find_fish_position()` — `fishing_detector.py`
Background subtraction: mediana z bufora 15 klatek (co 3 klatki).
`absdiff` → threshold 25 → morph close+open → findContours.

Filtry:
- text overlay (zolty HIT)
- text contour (jasny MISS)
- max jump (50 px)
- stale position (3 klatki nieruchomo = odrzuc)

Fallback: frame differencing (pierwsze 3 klatki po zmianie fazy).
Czas: 2-18 ms (z recomputem mediany: ~15 ms).

### `find_fish_simple()` — `fish_shape_detector.py`
Tlo referencyjne (mediana 50 klatek, cache `.npy`).
Roznica kanalow HSV S/V (`DIFF_THRESH=18`, `COMBINED=28`).
Blob detection, filtr area 18-1000 px², najblizszy rozmiarowi ~180 px².
Czas: ~0.8 ms.

### `_verify_fish_patch()` — `bot.py` + `fish_patch_cnn.onnx`
Wycina 32x32 patch wokol kandydata (safe crop z paddingiem).
Normalizacja BGR → float32 [0,1], HWC → CHW.
ONNX Runtime, 1 logit → sigmoid → prob > 0.5 = fish.
Czas: ~0.04 ms.

## Nieaktywny / dead code

### `_detect_frame()` w `bot.py` (linie ~241-300)
Metoda hybrydowa CNN+klasyczny, nigdzie nie wywolywana.
Uzywa `FishNetInference` do stanu — ale `play_fishing_round()` uzywa
`detect_circle_color()` (HSV) zamiast tego.
Powod: CNN kolor dalej wykrywal WHITE/RED po zamknieciu minigry, co blokowalo
start kolejnej rundy. Wrocono do klasycznego HSV.

### `FishNetInference` w `cnn/inference.py`
Ladowany w `__init__` (`self.cnn`), drukuje "TRYB HYBRYDOWY".
Nigdy nie uzywany w petli gry — dead code. Model 113 K params, 5 klas,
<5 ms, dziala poprawnie. Regresja pozycji (fish_x/y) ma ~34 px blad — nieuzywalna.

### `FishShapeDetector.find_fish()` (pelna wersja z template matching)
Zdefiniowana, ale bot uzywa tylko `find_fish_simple()` (szybsza, ~0.8 ms vs ~26 ms).

### Pozostale nieuzywane
- `_is_red_blob()` w `fishing_detector.py`
- `predict_fish_position()` w `fishing_detector.py`
- `total_catches` w `bot.py` — inicjalizowane na 0, nigdy nie inkrementowane

## Zabezpieczenia

- `_clamp_to_circle()` — klik max 54 px od srodka (`SAFE_RADIUS=54`)
- Same-spot limiter — max 3 kliki w promieniu 15 px, reset na white
- PatchCNN verifier — odrzuca false positives (napisy, splash)
- Stale position filter — 3+ klatki nieruchomo = tekst (odrzuc)
- Max jump filter — skok >50 px = anomalia (odrzuc)
- Admin check — wymaga PowerShell jako Administrator
- `pyautogui.FAILSAFE` — mysz w lewy gorny rog = stop (domyslne)
- Klawisz `q` — zamyka bota w trybie debug
- Ctrl+C — zamyka bota z terminala

## Pliki zrodlowe

- `src/bot.py` — glowna petla + PatchCNN weryfikacja (~636 linii)
- `src/config.py` — stale (okno, HSV thresholds, timingi) (~94 stalych)
- `src/fishing_detector.py` — klasyczny detektor: bg-sub + text filtry (~587 linii)
- `src/input_simulator.py` — `pydirectinput` + Win32 focus (Alt-trick)
- `src/screen_capture.py` — `mss grab`, 279x247 fishing box
- `cnn/fish_shape_detector.py` — detektor ksztaltu (tlo ref + blob, ~446 linii)
- `cnn/inference.py` — FishNet ONNX wrapper (NIEUZYWANY w grze)
- `cnn/train_patch_cnn.py` — trening PatchCNN + eksport ONNX
- `cnn/patch_dataset.py` — generator / review / augment patchow 32x32
- `cnn/model.py` — FishNet architektura PyTorch (NIEUZYWANY)
- `cnn/dataset.py` — FishNet dataset (NIEUZYWANY)
- `cnn/train.py` — FishNet trening (NIEUZYWANY)
- `cnn/export_onnx.py` — FishNet eksport (NIEUZYWANY)
- `cnn/label_tool.py` — GUI etykietowania klatek (NIEUZYWANY)
- `cnn/models/fishnet.onnx` — FishNet model (47.6 KB, NIEUZYWANY)
- `cnn/models/fish_patch_cnn.onnx` — PatchCNN model (23.9 KB, **AKTYWNY**)

## Dane treningowe (PatchCNN)

- 808 patchow 32x32 wygenerowanych z 202 klatek (`manifest.json`)
- 501 recznie zweryfikowanych przez uzytkownika
- 47 potwierdzonych fish + 454 potwierdzonych not_fish
- 82 blednie oznaczonych fish → not_fish (napisy MISS, splash, szum)
- Oversampling fish do 454 (balansowanie klas)
- Online augmentacja: flip, rotacja, jasnosc, shift

## Wyniki PatchCNN

| Metryka   | Wartosc |
|-----------|---------|
| Accuracy  | 99.4% |
| Precision | 94% (3 false positives, 0 false negatives) |
| Recall    | 100% |
| F1        | 0.969 |
| Model     | 89 K params, 23.9 KB ONNX, 0.04 ms inference |

## Wydajnosc per-frame

| Etap                       | Czas |
|----------------------------|------|
| `mss grab`                 | ~1-3 ms |
| `detect_circle_color`      | ~0.5 ms |
| `find_fish_position`       | ~2-18 ms (mediana co 3 klatki: ~15 ms) |
| `find_fish_simple`         | ~0.8 ms (tylko gdy bg-sub nie znajdzie) |
| `_verify_fish_patch`       | ~0.04 ms |
| **Suma**                   | **~4-22 ms** (budzet: 30 ms przy 33 FPS) |

## Uruchomienie

Wymaga PowerShell jako **Administrator**. Z rootu repo:

```powershell
cd "versions\tryb1_rybka_klik\post_cnn"
$env:PYTHONPATH = "."
py -m src.bot --debug
```

Flagi CLI (`bot.py`):
- `--debug` — okno podgladu z wizualizacja
- `--no-cnn` — wylacza FishNet (sam klasyczny, PatchCNN dalej aktywny)

Uruchomienie przez GUI: `py app/besafefish.py` (wybor trybu w dashboardzie).

## Wymagania

- Python 3.14, Windows, Administrator
- `opencv-python` 4.13.0, `mss` 10.1.0, `numpy` 2.4.2
- `pydirectinput` 1.0.4, `pygetwindow` 0.0.9
- `onnxruntime` 1.21.1+ (do PatchCNN)
- `torch` + `torchvision` (TYLKO do treningu, CPU-only)

## Znane problemy

1. FishNet CNN (stan) — nieuzywany, bo blokowal start 2. rundy
2. `total_catches` — nigdy nie inkrementowany (zawsze 0)
3. `_detect_frame()` — dead code, nie wywolywany
4. `last_fish_pos` — nie resetowany przy zmianie fazy white → red
5. Brak FPS countera w debug overlay
6. Brak logowania do pliku (tylko `print`)
7. Hardcoded koordynaty okna (0, 0) i fishing boxa (538, 288)
8. `pyautogui.FAILSAFE` nie ustawiony jawnie (polega na default)
9. `ensure_focus()` tylko raz na poczatku rundy

Zadania do zrobienia: patrz [`TODO.txt`](TODO.txt).
