# Historia wersji bota (tryb 1 — rybka-klik)

Dokument opisuje ewolucje bota dla minigry "lowienie ryb" w Metin2.
Krotki przeglad dla code review i osob wchodzacych w projekt.

## Skrot

```
pre_cnn (2026-03-16)   klasyczny OpenCV          skutecznosc: 80%
     |
     v   + FishShapeDetector (tlo referencyjne + blob, fallback)
     v   + PatchCNN 32x32 ONNX (weryfikacja kandydatow, 99.4% acc)
     v
post_cnn (2026-03-17)  klasyczny + ONNX          skutecznosc: rozwijana
```

## Dlaczego dwa warianty

Ewolucja bota w tym repo wygladala tak, ze przy kazdej wiekszej zmianie
robiony byl **snapshot calego folderu** (pre_cnn, post_cnn itp.) zamiast
zmian w jednym pliku. Dzieki temu starsze wersje zostaja w repo jako punkt
odniesienia — jesli cos w nowej zostalo popsute, latwo mozna porownac
zachowanie z wersja sprzed zmiany.

W kontekscie `tryb1_rybka_klik`:

- **`pre_cnn`** — wersja **przed** wprowadzeniem sieci neuronowych.
  Osadzona w czystym OpenCV: background subtraction + frame differencing
  + filtry konturowe (HIT / MISS). Mierzalna skutecznosc 8/10 (80%) na
  zbiorze testowym z 10 rund. **Nie jest juz rozwijana.**
- **`post_cnn`** — wersja **po** wprowadzeniu CNN. Ten sam pipeline
  klasyczny + dwa dodatkowe warstwy:
  - `FishShapeDetector` — detekcja ksztaltu rybki na tle referencyjnym
    (fallback, gdy bg-sub nic nie znalazl)
  - `PatchCNN` (`fish_patch_cnn.onnx`, 23.9 KB, 89 K parametrow) — siec
    klasyfikacyjna wycinka 32x32 (fish / not_fish), odrzuca false positives
    (napisy MISS/HIT, splashe, szum). Precision 94%, Recall 100%.
  
  Ta wersja jest **aktywnie uzywana** przez aplikacje desktop.

## Co sie zmienilo technicznie

| Komponent                         | `pre_cnn` | `post_cnn` |
|-----------------------------------|-----------|------------|
| Detekcja stanu (bialy/czerwony)   | HSV       | HSV (FishNet CNN nieuzywany) |
| Background subtraction            | TAK       | TAK |
| Frame differencing (fallback)     | TAK       | TAK |
| Filtry tekstu (HIT/MISS)          | TAK       | TAK |
| `FishShapeDetector` (fallback)    | nie ma    | TAK |
| `PatchCNN` weryfikacja kandydatow | nie ma    | TAK |
| Dane treningowe                   | n/d       | 808 patchy, 501 ręcznie zweryfikowanych |
| Czas per-frame (pipeline)         | ~4-18 ms  | ~4-22 ms |

## Co z `FishNetInference`?

W `post_cnn` jest `cnn/inference.py::FishNetInference` — klasyfikator stanu
(WHITE / RED / INACTIVE / HIT_TEXT / MISS_TEXT). **Jest ladowany, ale
nie uzywany** w petli gry — to dead code.

Powod: po zamknieciu okna minigry CNN dalej wykrywal WHITE/RED, co blokowalo
start kolejnej rundy. Wrocono do klasycznego HSV, ktory konczy detekcje
z chwila zniknieciia okna.

Model zostal na przyszlosc — moze sie przydac do detekcji wyniku rundy
(HIT vs MISS) zamiast detekcji stanu gry.

## Co z flagiem `use_cnn` w GUI?

Checkbox "Uzyj PatchCNN" w dashboardzie steruje flaga `use_cnn` przekazywana
do `KosaBot`. W obecnym kodzie ([`versions/tryb1_rybka_klik/post_cnn/src/bot.py`])
flaga odpowiada **tylko za ladowanie** `FishNetInference` — ktory i tak nie jest
uzywany. **PatchCNN** (realnie uzywany) laduje sie niezaleznie od tej flagi.

W praktyce **wylaczenie PatchCNN wymagaloby zmiany w kodzie** (`_verify_fish_patch`
musialby zwracac `(True, 1.0)` gdy flag off). To zadanie na pozniej.

Dopoki to nie zostanie zaimplementowane, flag jest placebo — bot zawsze chodzi
jak `post_cnn`. Zostaje w UI jako zarezerwowany hook na przyszlosc.

## Odniesienia

- [`versions/tryb1_rybka_klik/post_cnn/README.md`](../../versions/tryb1_rybka_klik/post_cnn/README.md)
- [`versions/tryb1_rybka_klik/pre_cnn/README.md`](../../versions/tryb1_rybka_klik/pre_cnn/README.md)
- [`versions/tryb1_rybka_klik/post_cnn/cnn/ARCHITEKTURA_CNN.md`](../../versions/tryb1_rybka_klik/post_cnn/cnn/ARCHITEKTURA_CNN.md)
- TODO / znane bledy: [`versions/tryb1_rybka_klik/post_cnn/TODO.txt`](../../versions/tryb1_rybka_klik/post_cnn/TODO.txt)
