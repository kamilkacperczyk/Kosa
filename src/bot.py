"""
Glowna petla bota Kosa.

Laczy wszystkie moduly i steruje cala logika automatyzacji lowienia ryb.

Cykl zycia jednej rundy:
1. Uzyj robaka (F4)
2. Zarzuc wedke (SPACJA)
3. Czekaj az okienko "Lowienie" sie pojawi
4. Skanuj okrag:
   - Czerwony = kliknij LPM (rybka w srodku)
   - Bialy = czekaj (rybka poza)
   - Brak = minigra sie skonczyla
5. Po 3 trafieniach lub koncu czasu -> wracamy do kroku 1

Zabezpieczenia:
- pyautogui.FAILSAFE = True (rusz mysz w lewy gorny rog zeby przerwac)
- Klawisz 'q' w oknie podgladu zamyka bota
- Ctrl+C w terminalu tez zamyka
"""

import time
import sys
import cv2

from src.screen_capture import ScreenCapture
from src.fishing_detector import FishingDetector
from src.input_simulator import InputSimulator
from src.config import SCAN_INTERVAL, CLICKS_TO_WIN


class KosaBot:
    """Glowny bot automatyzujacy lowienie ryb w Metin2."""

    def __init__(self, debug: bool = False):
        """
        Args:
            debug: jesli True, pokazuje okno podgladu z wizualizacja
        """
        self.capture = ScreenCapture()
        self.detector = FishingDetector()
        self.input = InputSimulator()
        self.debug = debug
        self.running = False
        self.total_rounds = 0
        self.total_catches = 0

    def wait_for_fishing_minigame(self, timeout: float = 10.0) -> bool:
        """
        Czeka az okienko minigry lowienia sie pojawi.

        Args:
            timeout: maksymalny czas oczekiwania w sekundach

        Returns:
            True jesli minigra sie pojawila, False jesli timeout
        """
        print("[BOT] Czekam na pojawienie sie minigry...")
        start = time.time()
        while time.time() - start < timeout:
            frame = self.capture.grab_fishing_box()
            if self.detector.is_fishing_active(frame):
                print("[BOT] Minigra wykryta!")
                return True
            time.sleep(SCAN_INTERVAL)

        print("[BOT] Timeout - minigra sie nie pojawila.")
        return False

    def play_fishing_round(self) -> bool:
        """
        Gra jedna runde minigry lowienia.
        Skanuje okrag i klika gdy jest czerwony.

        Returns:
            True jesli runda sie zakonczyla normalnie,
            False jesli przerwano (np. klawisz 'q')
        """
        print("[BOT] === Rozpoczynam runde lowienia ===")
        click_count = 0
        no_circle_count = 0
        max_no_circle = 30  # jesli przez 30 klatek nie ma okregu = koniec minigry

        while self.running:
            frame = self.capture.grab_fishing_box()
            color = self.detector.detect_circle_color(frame)

            if color == "red":
                print(f"[BOT] CZERWONY OKRAG! Klikam! ({click_count + 1}/{CLICKS_TO_WIN})")
                self.input.click_fishing_box()
                click_count += 1
                no_circle_count = 0

                if click_count >= CLICKS_TO_WIN:
                    print(f"[BOT] WYGRANA! Trafiono {CLICKS_TO_WIN}/{CLICKS_TO_WIN}!")
                    self.total_catches += 1
                    return True

            elif color == "white":
                no_circle_count = 0
                # Okrag bialy = czekamy, nic nie robimy

            else:
                # Brak okregu
                no_circle_count += 1
                if no_circle_count >= max_no_circle:
                    print("[BOT] Okrag zniknal - minigra sie skonczyla (timeout lub przegrana).")
                    return True

            # Debug: podglad na zywo
            if self.debug:
                if not self._show_debug(frame, color, click_count):
                    return False  # uzytkownik nacisnal 'q'

            time.sleep(SCAN_INTERVAL)

        return False

    def _show_debug(self, frame, color, click_count) -> bool:
        """
        Wyswietla okno debugowe z podgladem.

        Returns:
            False jesli uzytkownik nacisnal 'q' (chce zakonczyc)
        """
        display = frame.copy()

        # Kolor ramki
        if color == "red":
            border = (0, 0, 255)
            text = "KLIKAJ!"
        elif color == "white":
            border = (255, 255, 255)
            text = "Czekaj..."
        else:
            border = (128, 128, 128)
            text = "Brak okregu"

        cv2.rectangle(display, (0, 0), (display.shape[1]-1, display.shape[0]-1), border, 3)
        cv2.putText(display, text, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, border, 2)
        cv2.putText(display, f"Klikniecia: {click_count}/{CLICKS_TO_WIN}", (10, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        cv2.putText(display, f"Rundy: {self.total_rounds} | Zlow: {self.total_catches}", (10, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        cv2.imshow("Kosa Bot", display)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("[BOT] Uzytkownik nacisnal 'q' - koncze.")
            self.running = False
            return False
        return True

    def run(self):
        """
        Glowna petla bota. Powtarza cykl lowienia w nieskonczonosc.
        Zatrzymaj przez:
        - Klawisz 'q' w oknie podgladu (tryb debug)
        - Ctrl+C w terminalu
        - Ruszenie myszy w lewy gorny rog (pyautogui failsafe)
        """
        self.running = True
        print("=" * 50)
        print("  KOSA BOT - Automatyczne lowienie ryb")
        print("=" * 50)
        print()
        print("Zabezpieczenia:")
        print("  - Rusz mysz w LEWY GORNY ROG ekranu = natychmiastowe przerwanie")
        print("  - Ctrl+C w terminalu = przerwanie")
        if self.debug:
            print("  - Klawisz 'q' w oknie podgladu = przerwanie")
        print()
        print("Start za 3 sekundy...")
        time.sleep(3)

        try:
            while self.running:
                self.total_rounds += 1
                print(f"\n{'='*40}")
                print(f"[BOT] RUNDA {self.total_rounds}")
                print(f"{'='*40}")

                # 1. Start rundy: robak + wedka
                self.input.start_fishing_round()

                # 2. Czekaj na minigre
                if not self.wait_for_fishing_minigame():
                    print("[BOT] Minigra sie nie pojawila. Probuje ponownie...")
                    continue

                # 3. Graj runde
                if not self.play_fishing_round():
                    break  # przerwano

                # 4. Krotka pauza miedzy rundami
                print("[BOT] Pauza miedzy rundami...")
                time.sleep(1.0)

        except KeyboardInterrupt:
            print("\n[BOT] Przerwano przez Ctrl+C.")
        except Exception as e:
            print(f"\n[BOT] Blad: {e}")
        finally:
            self.running = False
            if self.debug:
                cv2.destroyAllWindows()
            print()
            print(f"[BOT] Podsumowanie:")
            print(f"  Rundy: {self.total_rounds}")
            print(f"  Udane zlowienia: {self.total_catches}")
            print(f"[BOT] Koniec.")


# --- URUCHOMIENIE ---
# python -m src.bot          -> tryb normalny
# python -m src.bot --debug  -> tryb z podgladem
if __name__ == "__main__":
    debug_mode = "--debug" in sys.argv
    bot = KosaBot(debug=debug_mode)
    bot.run()
