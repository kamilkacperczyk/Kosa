# Tryb 1 — rybka-klik

**Oficjalna nazwa w GUI:** "Mini-gra łowienie ryb (rybka - klik)".

## Co to za tryb

Klasyczna minigra w Metin2:

- postac zarzuca wedke (F4 + spacja)
- pojawia sie 279x247 okienko z woda
- w srodku okregu **biega rybka**
- okrag jest **bialy** gdy rybka jest "poza zasiegiem" — czekaj
- okrag robi sie **czerwony** gdy rybka jest "w zasiegu" — trzeba **kliknac** myszka **na rybke**
- 3 celne klikniecia = rybka zlapana; koniec rundy, zaczynamy od nowa

Bot robi to automatycznie: szuka rybki na klatce, czeka na faze czerwona,
klika tam gdzie jest rybka.

## Warianty

Tryb ma dwa warianty (wymienne w GUI):

| Folder | Opis | Status |
|--------|------|--------|
| [`post_cnn/`](post_cnn/README.md) | Nowsza wersja — klasyczna detekcja + PatchCNN (ONNX) do weryfikacji kandydatow na rybke | **Aktywny** (zywa wersja) |
| [`pre_cnn/`](pre_cnn/README.md) | Starsza wersja — sam klasyczny computer vision (bez sieci neuronowych) | Archiwum |

Szczegolowe rozniace w [`../../app/docs/historia-wersji.md`](../../app/docs/historia-wersji.md).

## Testy

Folder [`tests/`](tests/) zawiera 17 podfolderow z eksperymentami/analizami
dotyczacymi tego trybu (kalibracja progow HSV, walidacja trackingu,
diagnostyka na zywo). Opis: [`tests/README.md`](tests/README.md).
