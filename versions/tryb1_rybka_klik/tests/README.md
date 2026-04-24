# Testy i analizy — tryb1_rybka_klik

Foldery z eksperymentami, analizami i testami integracyjnymi dla bota lowiacego
rybke klikem (wariant `post_cnn` oraz `pre_cnn`). Kazdy podfolder zawiera:

- skrypt `*.py` — uruchamialny test/analiza
- `opis.txt` — krotki opis co robi i jak uruchomic
- czasem dodatkowe artefakty (logi CSV, raporty HTML/TXT, zrzuty klatek)

> Uwaga: zawartosc tych folderow jest **historyczna** — powstala przed
> restrukturyzacja repo (stary uklad `versions/post_cnn/`). Sciezki w niektorych
> skryptach i opisach moga wymagac aktualizacji zanim zadzialaja.

---

## Kategorie

### Analizy detekcji (kolor, piksele, bledy)
Jednorazowe analizy klatek — szukanie progow HSV, weryfikacja co bot blednie
wykrywa jako rybke, wyjasnianie napisow MISS/HIT.

- `analiza_kolorow/` — histogram HSV pikseli w obrebie okregu minigry
- `analiza_pikseli/` — rozklad jasnosci / saturacji na roznych klatkach
- `analyze_bad_frames/` — analiza klatek gdzie bot klikal w zle miejsce
- `analyze_miss/` — co odroznia tekst MISS od rybki w HSV

### Kalibracja
Skrypty pomocnicze do dostrajania progow detekcji.

- `calibrate/` — interaktywny tuner progow HSV (suwaki OpenCV)
- `test_kolory/` — wizualizacja klasyfikacji pikseli wg progow
- `test5_kolory/` — wariant kalibracji z innymi progami

### Diagnostyka na zywo
Narzedzia uruchamiane rownolegle z botem dla debugowania.

- `diagnostyka/` — zapisywanie klatek + metadanych podczas rundy
- `diagnostyka_gra/` — diagnostyka w kontekscie pelnej rundy lowienia
- `diagnostyka_live/` — live monitor (bez zapisu na dysk)

### Testy trackingu i reakcji bota
Testy walidujace konkretne zachowania: sledzenie rybki, filtrowanie napisow,
reakcje na zdarzenia HIT/MISS.

- `test8a_tracking/` — tracking rybki przez cala runde (log CSV + raport)
- `test8b_miss/` — bot musi ignorowac tekst MISS
- `test8c_hit/` — bot musi zareagowac na HIT poprawnie
- `test9_long/` — dluga sesja (wiele rund z rzedu, sprawdzanie stabilnosci)
- `test10_clean/` — czyste klatki bez napisow (baseline tracking)
- `test_filter/` — filtr kandydatow na rybke (aspect ratio, jasnosc, outlier jump)

### Walidacja detektora
Koncowa walidacja — czy detektor radzi sobie na zbiorze testowym.

- `walidacja_detektora/` — przejscie po wszystkich zebranych klatkach
  i raport skutecznosci (true positives / false positives)

---

## Uruchomienie pojedynczego testu

Z rootu repo (BeSafeFish):

```powershell
$env:PYTHONPATH = "versions\tryb1_rybka_klik\post_cnn"
py versions\tryb1_rybka_klik\tests\<folder>\<skrypt>.py
```

Szczegoly w `opis.txt` w kazdym folderze.
