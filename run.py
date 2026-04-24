"""
Launcher bota - wybiera tryb/wariant i uruchamia.

Struktura katalogow po restrukturyzacji:
  versions/<tryb>/<wariant>/src/bot.py

  gdzie <tryb>    = np. tryb1_rybka_klik, tryb2_dymek_spacja
        <wariant> = np. post_cnn, pre_cnn

Launcher skanuje wszystkie kombinacje <tryb>/<wariant> (te, ktore maja src/)
i dodaje wybrana sciezke do sys.path, dzieki czemu 'from src.X import Y'
dziala poprawnie.

Uzycie:
  py run.py                                          # menu wyboru
  py run.py --version tryb1_rybka_klik/post_cnn      # bezposredni wybor
  py run.py --version tryb1_rybka_klik/post_cnn --debug
  py run.py --version tryb1_rybka_klik/post_cnn --no-cnn

Identyfikator wariantu to relatywna sciezka <tryb>/<wariant> wzgledem
katalogu versions/.
"""

import sys
import os
import ctypes


def _get_versions_dir():
    """Zwraca sciezke do folderu versions/."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "versions")


def get_versions():
    """Skanuje versions/<tryb>/<wariant>/ i zwraca liste dostepnych wariantow.

    Zwraca posortowana liste identyfikatorow w formacie '<tryb>/<wariant>'
    (np. 'tryb1_rybka_klik/post_cnn'), kazdy z istniejacym podfolderem src/.
    """
    versions_dir = _get_versions_dir()
    if not os.path.isdir(versions_dir):
        return []
    variants = []
    for tryb in sorted(os.listdir(versions_dir)):
        tryb_path = os.path.join(versions_dir, tryb)
        if not os.path.isdir(tryb_path):
            continue
        for wariant in sorted(os.listdir(tryb_path)):
            wariant_path = os.path.join(tryb_path, wariant)
            if os.path.isdir(wariant_path) and os.path.isdir(os.path.join(wariant_path, "src")):
                # normalizuj separator do '/' zeby argument CLI byl platform-agnostic
                variants.append(f"{tryb}/{wariant}")
    return variants


def _read_version_desc(version_name):
    """Probuje odczytac krotki opis wariantu.

    Szuka po kolei:
    - `versions/<tryb>/<wariant>/README.md` (pierwsza linia niebedaca naglowkiem)
    - `versions/<tryb>/<wariant>/OPIS_WERSJI.txt` (legacy, dla zgodnosci)
    """
    base = os.path.join(_get_versions_dir(), *version_name.split("/"))
    candidates = [
        (os.path.join(base, "README.md"), ("#", "=")),
        (os.path.join(base, "OPIS_WERSJI.txt"), ("=", "#")),
    ]
    for path, skip_prefixes in candidates:
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith(skip_prefixes):
                        return line[:80]
        except OSError:
            continue
    return ""


def select_version(versions):
    """Wyswietla menu i pyta o wybor wersji."""
    print()
    print("=" * 50)
    print("  KOSA BOT - Wybor wersji")
    print("=" * 50)
    print()
    for i, v in enumerate(versions, 1):
        desc = _read_version_desc(v)
        desc_str = f"  ({desc})" if desc else ""
        print(f"  {i}. {v}{desc_str}")
    print()
    try:
        choice = input(f"Wybierz wersje (1-{len(versions)}): ").strip()
        idx = int(choice) - 1
        if idx < 0 or idx >= len(versions):
            raise ValueError()
        return versions[idx]
    except (ValueError, KeyboardInterrupt, EOFError):
        print("\nAnulowano.")
        sys.exit(0)


def main():
    # --- Zbierz dostepne warianty ---
    versions = get_versions()
    if not versions:
        print("[KOSA] Brak dostepnych wariantow w folderze versions/!")
        print("       Kazdy wariant wymaga: versions/<tryb>/<wariant>/src/")
        sys.exit(1)

    # --- Wybor wersji: z CLI lub menu ---
    selected = None
    if "--version" in sys.argv:
        idx = sys.argv.index("--version")
        if idx + 1 < len(sys.argv):
            # Normalizuj separator '\' -> '/' (Windows CLI moze podac backslash)
            selected = sys.argv[idx + 1].replace("\\", "/")
            if selected not in versions:
                print(f"[KOSA] Wersja '{selected}' nie istnieje!")
                print(f"       Dostepne: {', '.join(versions)}")
                sys.exit(1)

    if selected is None:
        if len(versions) == 1:
            selected = versions[0]
            print(f"[KOSA] Jedyna dostepna wersja: {selected}")
        else:
            selected = select_version(versions)

    # --- Sprawdz uprawnienia Administratora ---
    if not ctypes.windll.shell32.IsUserAnAdmin():
        print("[KOSA] BLAD: Bot wymaga uprawnien Administratora!")
        print("       Uruchom ponownie jako Administrator.")
        sys.exit(1)

    # --- Ustaw sys.path na wybrany wariant ---
    version_path = os.path.join(_get_versions_dir(), *selected.split("/"))
    sys.path.insert(0, version_path)

    debug_mode = "--debug" in sys.argv
    no_cnn = "--no-cnn" in sys.argv
    mode_str = "DEBUG" if debug_mode else "NORMALNY"
    cnn_str = "KLASYCZNY (--no-cnn)" if no_cnn else "CNN"
    print(f"[KOSA] Wersja: {selected} | Tryb: {mode_str} | Detekcja: {cnn_str}")
    print()

    # --- Import i uruchomienie bota ---
    from src.bot import KosaBot

    # Przekaz use_cnn jesli bot go obsluguje (post_cnn)
    import inspect
    bot_params = inspect.signature(KosaBot.__init__).parameters
    kwargs = {"debug": debug_mode}
    if "use_cnn" in bot_params:
        kwargs["use_cnn"] = not no_cnn
    bot = KosaBot(**kwargs)
    bot.run()


if __name__ == "__main__":
    main()
