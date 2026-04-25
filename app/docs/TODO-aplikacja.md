# TODO - aplikacja (cross-cutting)

Zadania dotyczace appki jako calosci - architektury, GUI, integracji,
ktore wykraczaja poza pojedynczy tryb minigry. TODO per-wariant-bota
(np. dla post_cnn) zyje w `versions/<tryb>/<wariant>/TODO.txt`.

---

## Pomysly do rozwazenia

### [ ] Wybor "aktywnosci" przed wyborem trybu minigry

**Pomysl:** W dashboardzie po zalogowaniu dodac wczesniejszy etap wyboru
**aktywnosci** (np. "Lowienie ryb", "Walka", "Zbieractwo"), ktory dopiero
otwiera lista trybow nalezacych do tej aktywnosci. Obecnie jest plaska
lista trybow bez kategoryzacji.

**Cel:**
- czytelniejsze GUI gdy bedzie wiecej trybow (np. 5+)
- naturalna kategoryzacja - np. "Lowienie ryb -> rybka-klik / dymek-spacja"
  vs "Walka -> bot-PvE" (tryby z roznych aktywnosci moga miec zupelnie
  inne kontrakty / inny start_round)
- mozliwosc grupowania trybow ktore wymagaja podobnego setupu (np.
  wszystkie tryby "Lowienia ryb" zaczynaja od F4 + SPACE)

**Strona techniczna do przemyslenia:**
- czy aktywnosc to tylko grupa wizualna w GUI, czy tez warstwa abstrakcji
  w kodzie (`app/activities/lowienie_ryb/...`)?
- czy aktywnosci moga miec wspolne metody (np. `find_game_window()` zostaje
  w aktywnosci, tryby ja dziedzicza)?
- struktura katalogow: `versions/tryb1_rybka_klik/` -> moze zmienic na
  `versions/lowienie_ryb/rybka_klik/` + `dymek_spacja/`?

**Status:** pomysl, nie podejmujemy akcji teraz.
**Powod:** YAGNI - mamy 1 aktywnosc i 2 tryby. Az do momentu gdy ujawni
sie 2-ga aktywnosc (z innym setupem niz wedkarstwo), nie wiadomo jak
ja dobrze zaprojektowac. Wracamy do tego kiedy bedzie konkretny przyklad.
