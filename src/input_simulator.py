"""
Modul symulacji inputow (klikniecia myszy, naciskanie klawiszy).

Uzywa pyautogui do symulowania akcji gracza.
Wszystkie akcje maja wbudowane male opoznienia zeby gra zdazyla zareagowac.
"""

import time
import pyautogui

from src.config import (
    GAME_WINDOW_X, GAME_WINDOW_Y,
    FISHING_BOX_X, FISHING_BOX_Y,
    FISHING_BOX_WIDTH, FISHING_BOX_HEIGHT,
    BAIT_KEY, CAST_KEY,
    POST_CLICK_DELAY, CAST_DELAY, BAIT_DELAY,
)

# Wylacz failsafe pyautogui (domyslnie ruszenie myszy w rog ekranu
# powoduje przerwanie programu - zostawiamy to jako zabezpieczenie)
pyautogui.FAILSAFE = True

# Minimalne opoznienie miedzy akcjami pyautogui (sekundy)
pyautogui.PAUSE = 0.05


class InputSimulator:
    """Symuluje klikniecia myszy i naciskanie klawiszy w grze."""

    def __init__(self):
        # Srodek okienka lowienia (tam klikamy gdy okrag jest czerwony)
        self.fishing_center_x = GAME_WINDOW_X + FISHING_BOX_X + FISHING_BOX_WIDTH // 2
        self.fishing_center_y = GAME_WINDOW_Y + FISHING_BOX_Y + FISHING_BOX_HEIGHT // 2

    def click_fishing_box(self):
        """
        Klikniecie lewym przyciskiem myszy w srodek okienka lowienia.
        Uzywane gdy okrag jest czerwony (rybka w srodku).
        """
        pyautogui.click(self.fishing_center_x, self.fishing_center_y)
        time.sleep(POST_CLICK_DELAY)

    def use_bait(self):
        """
        Nacisniecie klawisza robaka (F4).
        Zuzywa jednego robaka przed zarzuceniem wedki.
        """
        pyautogui.press(BAIT_KEY)
        time.sleep(BAIT_DELAY)

    def cast_rod(self):
        """
        Nacisniecie SPACJI — zarzucenie wedki.
        Po tym rozpoczyna sie minigra lowienia.
        """
        pyautogui.press(CAST_KEY)
        time.sleep(CAST_DELAY)

    def start_fishing_round(self):
        """
        Pelna sekwencja startu rundy:
        1. Nacisnij F4 (uzyj robaka)
        2. Nacisnij SPACJE (zarzuc wedke)
        """
        print("[INPUT] Uzywam robaka (F4)...")
        self.use_bait()
        print("[INPUT] Zarzucam wedke (SPACJA)...")
        self.cast_rod()
        print("[INPUT] Wedka zarzucona, czekam na minigre...")


# --- TRYB TESTOWY ---
# Uruchom: python -m src.input_simulator
# UWAGA: To faktycznie klika i naciska klawisze!
# Masz 5 sekund na przelaczenie sie do okna gry.
if __name__ == "__main__":
    print("=== Test symulatora inputow ===")
    print(f"Srodek okienka lowienia: ({InputSimulator().fishing_center_x}, {InputSimulator().fishing_center_y})")
    print()
    print("UWAGA: Za 5 sekund nastapi klikniecie w srodek okienka lowienia!")
    print("Przelacz sie teraz do okna gry!")
    print()

    for i in range(5, 0, -1):
        print(f"  {i}...")
        time.sleep(1)

    sim = InputSimulator()
    print("Klikam w srodek okienka lowienia!")
    sim.click_fishing_box()
    print("Gotowe.")
