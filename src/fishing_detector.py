"""
Modul wykrywania stanu minigry lowienia ryb.

Analizuje screenshot okienka "Lowienie" i okresla:
- Czy minigra jest aktywna (czy widac okienko)
- Czy okrag jest bialy (rybka poza) czy czerwony (rybka w srodku)
- Gdzie jest rybka

Uzywa OpenCV z przestrzenia kolorow HSV do wykrywania kolorow.
"""

import numpy as np
import cv2

from src.config import (
    WHITE_CIRCLE_H_MIN, WHITE_CIRCLE_H_MAX,
    WHITE_CIRCLE_S_MIN, WHITE_CIRCLE_S_MAX,
    WHITE_CIRCLE_V_MIN, WHITE_CIRCLE_V_MAX,
    RED_CIRCLE_H_MIN_1, RED_CIRCLE_H_MAX_1,
    RED_CIRCLE_H_MIN_2, RED_CIRCLE_H_MAX_2,
    RED_CIRCLE_S_MIN, RED_CIRCLE_S_MAX,
    RED_CIRCLE_V_MIN, RED_CIRCLE_V_MAX,
)


class FishingDetector:
    """Analizuje okienko minigry lowienia i wykrywa stan gry."""

    # Progi - ile pikseli danego koloru musi byc zeby uznac ze okrag jest tego koloru.
    # Te wartosci trzeba skalirbowac na zywej grze.
    RED_PIXEL_THRESHOLD = 500      # min pikseli czerwonych = okrag czerwony
    WHITE_PIXEL_THRESHOLD = 500    # min pikseli bialych = okrag bialy
    FISHING_ACTIVE_THRESHOLD = 200 # min pikseli (bialy+czerwony) = minigra aktywna

    def __init__(self):
        pass

    def detect_circle_color(self, fishing_frame: np.ndarray) -> str:
        """
        Analizuje kolor okregu w okienku lowienia.

        Args:
            fishing_frame: screenshot okienka lowienia (BGR numpy array)

        Returns:
            'red'   - okrag czerwony (rybka w srodku - KLIKAJ!)
            'white' - okrag bialy (rybka poza - CZEKAJ)
            'none'  - nie wykryto okregu (minigra nieaktywna?)
        """
        hsv = cv2.cvtColor(fishing_frame, cv2.COLOR_BGR2HSV)

        # Wykryj czerwone piksele (czerwony ma 2 zakresy w HSV)
        red_mask_1 = cv2.inRange(
            hsv,
            np.array([RED_CIRCLE_H_MIN_1, RED_CIRCLE_S_MIN, RED_CIRCLE_V_MIN]),
            np.array([RED_CIRCLE_H_MAX_1, RED_CIRCLE_S_MAX, RED_CIRCLE_V_MAX]),
        )
        red_mask_2 = cv2.inRange(
            hsv,
            np.array([RED_CIRCLE_H_MIN_2, RED_CIRCLE_S_MIN, RED_CIRCLE_V_MIN]),
            np.array([RED_CIRCLE_H_MAX_2, RED_CIRCLE_S_MAX, RED_CIRCLE_V_MAX]),
        )
        red_mask = cv2.bitwise_or(red_mask_1, red_mask_2)
        red_count = cv2.countNonZero(red_mask)

        # Wykryj biale piksele
        white_mask = cv2.inRange(
            hsv,
            np.array([WHITE_CIRCLE_H_MIN, WHITE_CIRCLE_S_MIN, WHITE_CIRCLE_V_MIN]),
            np.array([WHITE_CIRCLE_H_MAX, WHITE_CIRCLE_S_MAX, WHITE_CIRCLE_V_MAX]),
        )
        white_count = cv2.countNonZero(white_mask)

        # Decyzja
        if red_count >= self.RED_PIXEL_THRESHOLD:
            return "red"
        elif white_count >= self.WHITE_PIXEL_THRESHOLD:
            return "white"
        else:
            return "none"

    def is_fishing_active(self, fishing_frame: np.ndarray) -> bool:
        """
        Sprawdza czy minigra lowienia jest aktywna.
        Jesli widzimy okrag (bialy lub czerwony) to gra jest aktywna.

        Args:
            fishing_frame: screenshot okienka lowienia (BGR numpy array)

        Returns:
            True jesli minigra jest aktywna
        """
        hsv = cv2.cvtColor(fishing_frame, cv2.COLOR_BGR2HSV)

        # Szukamy bialych pikseli (okrag)
        white_mask = cv2.inRange(
            hsv,
            np.array([WHITE_CIRCLE_H_MIN, WHITE_CIRCLE_S_MIN, WHITE_CIRCLE_V_MIN]),
            np.array([WHITE_CIRCLE_H_MAX, WHITE_CIRCLE_S_MAX, WHITE_CIRCLE_V_MAX]),
        )
        white_count = cv2.countNonZero(white_mask)

        # Szukamy czerwonych pikseli (okrag)
        red_mask_1 = cv2.inRange(
            hsv,
            np.array([RED_CIRCLE_H_MIN_1, RED_CIRCLE_S_MIN, RED_CIRCLE_V_MIN]),
            np.array([RED_CIRCLE_H_MAX_1, RED_CIRCLE_S_MAX, RED_CIRCLE_V_MAX]),
        )
        red_mask_2 = cv2.inRange(
            hsv,
            np.array([RED_CIRCLE_H_MIN_2, RED_CIRCLE_S_MIN, RED_CIRCLE_V_MIN]),
            np.array([RED_CIRCLE_H_MAX_2, RED_CIRCLE_S_MAX, RED_CIRCLE_V_MAX]),
        )
        red_mask = cv2.bitwise_or(red_mask_1, red_mask_2)
        red_count = cv2.countNonZero(red_mask)

        total = white_count + red_count
        return total >= self.FISHING_ACTIVE_THRESHOLD

    def get_debug_info(self, fishing_frame: np.ndarray) -> dict:
        """
        Zwraca szczegolowe informacje debugowe.
        Przydatne do kalibracji progow.

        Args:
            fishing_frame: screenshot okienka lowienia (BGR numpy array)

        Returns:
            dict z informacjami o ilosciach pikseli kazdego koloru
        """
        hsv = cv2.cvtColor(fishing_frame, cv2.COLOR_BGR2HSV)

        # Czerwone
        red_mask_1 = cv2.inRange(
            hsv,
            np.array([RED_CIRCLE_H_MIN_1, RED_CIRCLE_S_MIN, RED_CIRCLE_V_MIN]),
            np.array([RED_CIRCLE_H_MAX_1, RED_CIRCLE_S_MAX, RED_CIRCLE_V_MAX]),
        )
        red_mask_2 = cv2.inRange(
            hsv,
            np.array([RED_CIRCLE_H_MIN_2, RED_CIRCLE_S_MIN, RED_CIRCLE_V_MIN]),
            np.array([RED_CIRCLE_H_MAX_2, RED_CIRCLE_S_MAX, RED_CIRCLE_V_MAX]),
        )
        red_mask = cv2.bitwise_or(red_mask_1, red_mask_2)
        red_count = cv2.countNonZero(red_mask)

        # Biale
        white_mask = cv2.inRange(
            hsv,
            np.array([WHITE_CIRCLE_H_MIN, WHITE_CIRCLE_S_MIN, WHITE_CIRCLE_V_MIN]),
            np.array([WHITE_CIRCLE_H_MAX, WHITE_CIRCLE_S_MAX, WHITE_CIRCLE_V_MAX]),
        )
        white_count = cv2.countNonZero(white_mask)

        color = self.detect_circle_color(fishing_frame)
        active = self.is_fishing_active(fishing_frame)

        return {
            "red_pixels": red_count,
            "white_pixels": white_count,
            "circle_color": color,
            "fishing_active": active,
            "red_mask": red_mask,
            "white_mask": white_mask,
        }


# --- TRYB TESTOWY ---
# Uruchom: python -m src.fishing_detector
# Pokazuje na zywo co wykrywa detektor (wymaga uruchomionej gry)
if __name__ == "__main__":
    from src.screen_capture import ScreenCapture

    print("=== Test detektora lowienia ===")
    print("Uruchom gre i rozpocznij lowienie ryb.")
    print("Nacisnij 'q' zeby zamknac.")
    print()

    capture = ScreenCapture()
    detector = FishingDetector()

    while True:
        # Zrob screenshot okienka lowienia
        fishing_frame = capture.grab_fishing_box()

        # Analizuj
        debug = detector.get_debug_info(fishing_frame)

        # Wyswietl info na klatce
        color = debug["circle_color"]
        active = debug["fishing_active"]
        red_px = debug["red_pixels"]
        white_px = debug["white_pixels"]

        # Kolor ramki zalezy od wykrytego stanu
        if color == "red":
            border_color = (0, 0, 255)  # czerwony
            status = "KLIKAJ!"
        elif color == "white":
            border_color = (255, 255, 255)  # bialy
            status = "Czekaj..."
        else:
            border_color = (128, 128, 128)  # szary
            status = "Brak okregu"

        # Rysuj ramke i tekst
        display = fishing_frame.copy()
        cv2.rectangle(display, (0, 0), (display.shape[1]-1, display.shape[0]-1), border_color, 3)
        cv2.putText(display, status, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, border_color, 2)
        cv2.putText(display, f"Red: {red_px}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        cv2.putText(display, f"White: {white_px}", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(display, f"Active: {active}", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        # Pokaz klatke i maski
        cv2.imshow("Kosa - Fishing Box", display)
        cv2.imshow("Red Mask", debug["red_mask"])
        cv2.imshow("White Mask", debug["white_mask"])

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()
    print("Zamknieto.")
