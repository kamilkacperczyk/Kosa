"""
BotWorker — QThread wrapper dla KosaBot.

Uruchamia bota w osobnym watku, emituje sygnaly do GUI.
Zapewnia thread-safe komunikacje: bot._log() → Signal → GUI._on_log()
"""

import ctypes
from PySide6.QtCore import QThread, Signal


class BotWorker(QThread):
    """Watek roboczy uruchamiajacy KosaBot."""

    # Sygnaly emitowane do GUI (thread-safe przez Qt signal/slot)
    log_message = Signal(str)       # wiadomosc do wyswietlenia w logu
    status_changed = Signal(str)    # "running" / "stopped" / "error"
    finished_signal = Signal()      # bot zakonczyl prace

    def __init__(self, debug: bool = False, use_cnn: bool = True):
        super().__init__()
        self._debug = debug
        self._use_cnn = use_cnn
        self._bot = None

    def _is_admin(self) -> bool:
        """Sprawdza czy proces ma uprawnienia Administratora."""
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False

    def run(self):
        """Uruchamia bota w watku (nie wywoluj bezposrednio — uzyj .start())."""
        try:
            # Sprawdz uprawnienia admina
            if not self._is_admin():
                self.log_message.emit("[BLAD] Bot wymaga uprawnien Administratora!")
                self.log_message.emit("[INFO] Uruchom BeSafeFish jako Administrator.")
                self.log_message.emit("[INFO] PPM na skrot → 'Uruchom jako administrator'")
                self.status_changed.emit("error")
                self.finished_signal.emit()
                return

            self.status_changed.emit("running")
            self.log_message.emit("[BOT] Inicjalizacja...")

            # Import bota tutaj — nie blokuje startu GUI
            from src.bot import KosaBot

            self._bot = KosaBot(
                debug=False,           # GUI mode — bez cv2.imshow
                use_cnn=self._use_cnn,
                log_callback=self._on_log,
            )

            self.log_message.emit("[BOT] Uruchamiam glowna petle...")
            self._bot.run()

        except Exception as e:
            self.log_message.emit(f"[BLAD] {e}")
            self.status_changed.emit("error")
        finally:
            self.status_changed.emit("stopped")
            self.finished_signal.emit()

    def _on_log(self, msg: str):
        """Callback z bota — emituje sygnal do GUI."""
        self.log_message.emit(msg)

    def stop(self):
        """Zatrzymuje bota (thread-safe — ustawia flage)."""
        if self._bot is not None:
            self._bot.stop()
