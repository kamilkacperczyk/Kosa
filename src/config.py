"""
Konfiguracja aplikacji Kosa.

Wszystkie stale i parametry konfiguracyjne w jednym miejscu.
Pozniej mozna to zaladowac z pliku config.json.
"""

# --- OKNO GRY ---
# Okno gry Metin2 jest zawsze w lewym gornym rogu ekranu.
# Te wartosci trzeba dostosowac do Twojego rozmiaru okna.
# Mozesz je sprawdzic uruchamiajac: python src/screen_capture.py
GAME_WINDOW_X = 0
GAME_WINDOW_Y = 0
GAME_WINDOW_WIDTH = 1024   # szerokosc okna gry w pikselach
GAME_WINDOW_HEIGHT = 768   # wysokosc okna gry w pikselach

# --- MINIGRA LOWIENIE ---
# Okienko minigry pojawia sie na srodku okna gry.
# Te wartosci to PRZYBLIZONE pozycje wzgledem okna gry.
# Bedziemy je kalibrowac na zywej grze.
FISHING_BOX_X = 400        # x lewego gornego rogu okienka lowienia (wzgledem okna gry)
FISHING_BOX_Y = 250        # y lewego gornego rogu okienka lowienia (wzgledem okna gry)
FISHING_BOX_WIDTH = 230    # szerokosc okienka lowienia
FISHING_BOX_HEIGHT = 260   # wysokosc okienka lowienia

# --- KOLORY (HSV) ---
# OpenCV uzywa HSV: H(0-179), S(0-255), V(0-255)
# Bialy okrag: wysoka jasnosc, niska saturacja
WHITE_CIRCLE_H_MIN = 0
WHITE_CIRCLE_H_MAX = 179
WHITE_CIRCLE_S_MIN = 0
WHITE_CIRCLE_S_MAX = 50
WHITE_CIRCLE_V_MIN = 200
WHITE_CIRCLE_V_MAX = 255

# Czerwony okrag: czerwony w HSV ma dwa zakresy (0-10 i 170-179)
RED_CIRCLE_H_MIN_1 = 0
RED_CIRCLE_H_MAX_1 = 10
RED_CIRCLE_H_MIN_2 = 170
RED_CIRCLE_H_MAX_2 = 179
RED_CIRCLE_S_MIN = 100
RED_CIRCLE_S_MAX = 255
RED_CIRCLE_V_MIN = 100
RED_CIRCLE_V_MAX = 255

# --- KLAWISZE ---
BAIT_KEY = 'f4'            # klawisz robaka (przyneta)
CAST_KEY = 'space'         # klawisz zarzucenia wedki

# --- TIMING ---
SCAN_INTERVAL = 0.05       # co ile sekund robic screenshot (50ms = 20 FPS)
POST_CLICK_DELAY = 0.3     # opoznienie po kliknieciu (zeby gra zdazyla zareagowac)
CAST_DELAY = 1.5           # opoznienie po zarzuceniu wedki (czekamy az minigra sie pojawi)
BAIT_DELAY = 0.5           # opoznienie po uzyciu robaka

# --- GAME LOGIC ---
CLICKS_TO_WIN = 3          # ile trafien potrzeba zeby wygrac
