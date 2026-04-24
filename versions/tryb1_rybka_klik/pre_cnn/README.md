# Wariant: PRE CNN (archiwum)

**Status:** Archiwum, nie rozwijany
**Data snapshotu:** 2026-03-16
**Commit:** `092dd3e`
**Wynik:** 8/10 udanych lowien (80% skutecznosc)

## Opis ogolny

Bot do automatycznego lowienia ryb w grze Metin2 (serwer Eryndos).
Wersja **PRE CNN** — oparta wylacznie na klasycznych metodach computer vision
(OpenCV), **bez sieci neuronowych**.

Bot automatycznie:

1. Zaklada robaka (`F4`) i zarzuca wedke (`SPACJA`)
2. Czeka az pojawi sie okienko minigry lowienia
3. Sledzi rybke i klika, gdy okrag jest czerwony (rybka w srodku)
4. Po 3 trafieniach lub koncu czasu — powtarza cykl

## Jak dziala detekcja (krok po kroku)

### 1. Przechwytywanie ekranu
- Biblioteka: `mss` (szybsze niz `pyautogui`)
- Region: 279x247 px (okienko minigry)
- Pozycja okienka: `x=538, y=288` wzgledem lewego gornego rogu okna gry
- Czestotliwosc: co 30 ms (~33 FPS)

### 2. Detekcja aktywnosci minigry
- Zlicza jasne piksele (grayscale > 200)
- `>= 400` jasnych pikseli → minigra aktywna
- `< 400` → brak minigry (czekaj)

### 3. Detekcja koloru okregu (bialy vs czerwony)
- Konwersja do HSV
- Zlicza piksele "prawie biale": S < 40 i V > 220
- `>= 400` takich pikseli → BIALY okrag (rybka poza, czekaj)
- `< 400` takich pikseli → CZERWONY okrag (rybka w srodku, klikaj)

### 4. Sledzenie rybki — Background subtraction (metoda glowna)
- Bufor 15 ostatnich klatek (grayscale)
- Co 3 klatki oblicza MEDIANE pikseli → model tla (rybka sie rusza, mediana ja "wymazuje")
- Biezaca klatka − mediana = roznica
- Binaryzacja progiem 25
- Maska okregu (promien 59 px od srodka) — szuka tylko wewnatrz
- Oczyszczenie morfologiczne (close + open, jadro 3x3)
- Wyciecie UI: gorne 25 px i dolne 20 px (timer, tekst)
- Znajdowanie konturow → kandydaci na rybke
- Filtrowanie: min pole 30 px, sprawdzenie czy to nie tekst
- Najwiekszy blob = rybka

### 5. Sledzenie rybki — Frame differencing (fallback)
- Uzywane tylko w pierwszych klatkach nowej fazy (< 3 w buforze)
- `|biezaca − poprzednia|` z progiem 20
- Filtr: 20 < pole < 1000, bbox < 80x80, w zasiegu okregu

### 6. Filtry przeciw napisom HIT/MISS

**a) Filtr HIT (poziom klatki)**
- Zolte piksele w okregu: H=15-45, S>=80, V>=150
- `>= 50` zoltych pikseli → napis HIT wykryty → nie szukaj rybki

**b) Filtr tekstu (poziom konturu) — 3 kryteria**
- Kryterium 1: aspect ratio > 3.0 i szerokosc > 40 px → tekst
- Kryterium 2: > 15% jasnych pikseli (V>220) w regionie → tekst
- Kryterium 3 (MISS): > 30% jasnych pikseli z niska saturacja (S < 120) → tekst MISS

**c) Filtr statycznej pozycji**
- Jesli pozycja nie zmienila sie o > 3 px przez >= 3 klatki → odrzuc
- Tekst MISS stoi w miejscu, rybka sie rusza

**d) Filtr maksymalnego skoku**
- Jesli pozycja skoczyla o > 50 px w X lub Y → odrzuc (outlier)

### 7. Klikanie
- Biblioteka: `pydirectinput` (DirectInput scan codes, rozpoznawane przez gry)
- Przeliczanie wspolrzednych: `rybka_wewnatrz_okienka` → ekranowe
- Ograniczenie do bezpiecznego okregu (promien 54 px = 64 − 10 marginesu)
- Limit 3 klikniec w to samo miejsce (promien 15 px)
- Metoda szybka: bez fokusowania okna, bez delay

## Konfiguracja (`config.py`)

```
Okno gry:             1358 x 768 px, pozycja (0, 0)
Okienko lowienia:     279 x 247 px, pozycja (538, 288)
Okrag:                srodek (140, 137), promien 64 px
Bezpieczny promien:   54 px (64 - 10 marginesu)

Progi detekcji:
  Aktywnosc minigry:        400 jasnych px (gray > 200)
  Bialy/czerwony okrag:     400 bialych px (S<40, V>220)
  Background subtraction:   bufor 15, mediana co 3, prog 25
  Min pole rybki:           30 px
  Max skok:                 50 px

Filtry tekstu:
  HIT (zolty):         H=15-45, S>=80, V>=150, prog 50 px
  MISS (kontur):       saturacja < 120, proporcja > 30%
  Statyczna pozycja:   prog 3 px, limit 3 klatki
  Jasne px tekstu:     V > 220, prog 50 px

Timing:
  Skanowanie:    30 ms (~33 FPS)
  Delay po kliku: 50 ms
  Robak:         500 ms delay
  Wedka:         1500 ms delay
```

## Pliki zrodlowe

- `src/bot.py` — glowna petla bota (342 linie)
- `src/config.py` — stale konfiguracyjne (92 linie)
- `src/fishing_detector.py` — detekcja ryb i koloru okregu (639 linii)
- `src/input_simulator.py` — symulacja myszy i klawiatury (163 linie)
- `src/screen_capture.py` — przechwytywanie ekranu (105 linii)
- `src/__init__.py` — plik inicjalizacji modulu

Razem: ~1341 linii kodu.

## Wymagania

- Python 3.14
- `opencv-python`, `mss`, `numpy`, `pydirectinput`, `pygetwindow`
- System: Windows (`pydirectinput` wymaga DirectInput)
- Uprawnienia: **Administrator** (Windows UIPI)
- Gra: Metin2 serwer Eryndos, okno w lewym gornym rogu

## Znane ograniczenia

1. Filtr MISS na poziomie klatki (lavender piksele) zbyt agresywny — piksele wody maja
   podobne HSV do tekstu MISS. Filtr frame-level wylaczony, dziala tylko konturowy.
2. Skutecznosc 80% — 2 niepowodzenia wynikaja z:
   - opoznionej detekcji na poczatku fazy (fallback frame diff mniej dokladny)
   - sporadycznych falszywych klikniec w tekst MISS
3. Brak predykcji trajektorii rybki (ekstrapolacja liniowa dostepna ale nieuzywana)
4. Stale hardcoded — wymaga rekalibracji przy zmianie rozdzielczosci

## Uruchomienie

Wymaga **Administrator**. Z rootu repo:

```powershell
cd "versions\tryb1_rybka_klik\pre_cnn"
$env:PYTHONPATH = "."
py -m src.bot --debug
```

Lub przez launcher `start_bot.bat` w rootcie repo.

## Relacja do wariantu `post_cnn`

Ten wariant to **poprzednia generacja** bota. Wariant `post_cnn` (zywy, rozwijany)
rozszerza go o:
- `FishShapeDetector` (fallback lokalizacji rybki)
- `PatchCNN` (weryfikator kandydatow na rybke, ONNX)

Szczegoly: [`../post_cnn/README.md`](../post_cnn/README.md) oraz
[`../../../app/docs/historia-wersji.md`](../../../app/docs/historia-wersji.md).
