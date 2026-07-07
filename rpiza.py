#!/usr/bin/env python3
"""
RPiZA — Raspberry Pi Zuflussregelungsanlage mit Fußgängerübergang.

Testbare Fassung des Steuerkerns aus ``Ampelsteurung_IntelliCross.py``.
Verhalten, Zeitkonstanten, Zustandsnamen und die LED-Logik sind identisch
zum Echtbetrieb; zusätzlich gibt es einen Simulations-/Mock-Modus, damit die
Testfälle TC-P01, TC-P02 und TC-S01 ohne Raspberry-Pi-Hardware laufen.

    * Echtbetrieb (auf dem Raspberry Pi mit RPi.GPIO/gpiozero): mock=False
    * Testbetrieb (jeder Rechner): mock=True

Ausführung der Tests:
    python3 test_tc_p01.py
    python3 test_tc_p02.py
    python3 test_tc_s01.py
"""

import logging
import threading
import time

# ============================================================
# Logging (im Testbetrieb ruhig halten)
# ============================================================
logging.basicConfig(
    level=logging.CRITICAL,
    format="%(asctime)s [%(levelname)s] %(threadName)s — %(message)s",
)
log = logging.getLogger("RPiZA")

# ============================================================
# Hardware-Erkennung (optional — fehlt sie, wird automatisch gemockt)
# ============================================================
try:
    import RPi.GPIO as _RPIGPIO
    from gpiozero import LED as _HWLED

    _HARDWARE = True
    log.info("RPi.GPIO und gpiozero erkannt — Echtbetrieb möglich.")
except (ImportError, RuntimeError):
    _RPIGPIO = None
    _HWLED = None
    _HARDWARE = False

# ============================================================
# Pin-Definitionen BCM
# ============================================================
PIN_FZA_ROT = 5
PIN_FZA_GELB = 6
PIN_FZA_GRUEN = 13

PIN_FGA1_ROT = 27
PIN_FGA1_GRUEN = 22

PIN_FGA2_ROT = 21
PIN_FGA2_GRUEN = 16

PIN_TRIG = 19
PIN_ECHO = 23

# ============================================================
# Zeitwerte
# ============================================================
T_GELB = 1.0
T_ROT_GELB = 1.0
T_ZWISCHENZEIT = 4.0
T_RAEUMZEIT = 4.0
T_MIN_GRUEN_FGA = 10.0

FZA_GRUEN_MIN = 120
FZA_GRUEN_MAX = 300

FGA_GRUEN_MIN = 10
FGA_GRUEN_MAX = 40

# ============================================================
# Sensorparameter
# ============================================================
SENSOR_BEREICH_CM = 5
SENSOR_BEST = 3
SENSOR_INTERVALL = 0.05   # Voraussetzung für TC-P01

# ============================================================
# Sicherheitsüberwachung
# ============================================================
WATCHDOG_TIMEOUT = 0.4
WD_INTERVALL = 0.05
CONFLICT_BEST = 2


# ============================================================
# Mock-LED (bildet gpiozero.LED für den Testbetrieb nach)
# ============================================================
class _MockLED:
    def __init__(self, pin):
        self.pin = pin
        self.value = 0

    def on(self):
        self.value = 1

    def off(self):
        self.value = 0


# ============================================================
# Fahrzeugsensor
# ============================================================
class FahrzeugSensor:
    """HC-SR04-Ultraschallsensor. Im Mock-Modus wird die Anwesenheit eines
    Fahrzeugs über :meth:`simuliere` gesetzt statt gemessen."""

    def __init__(self, mock=None):
        if mock is None:
            mock = not _HARDWARE
        self.mock = mock

        self._zaehler = 0
        self._erkannt = False
        self._vorhanden = False          # nur Mock: simuliertes Fahrzeug
        self._lock = threading.Lock()
        self._stop_evt = threading.Event()

        if not self.mock:
            _RPIGPIO.setmode(_RPIGPIO.BCM)
            _RPIGPIO.setup(PIN_TRIG, _RPIGPIO.OUT)
            _RPIGPIO.setup(PIN_ECHO, _RPIGPIO.IN, pull_up_down=_RPIGPIO.PUD_DOWN)
            _RPIGPIO.output(PIN_TRIG, _RPIGPIO.LOW)
            log.info("HC-SR04 initialisiert.")

        self._thread = threading.Thread(
            target=self._poll_schleife, daemon=True, name="SensorPoll",
        )
        self._thread.start()

    def simuliere(self, vorhanden: bool):
        """Testschnittstelle: setzt/entfernt ein simuliertes Fahrzeug."""
        with self._lock:
            self._vorhanden = bool(vorhanden)
            if not self._vorhanden:
                self._zaehler = 0
                self._erkannt = False

    def _messen(self):
        GPIO = _RPIGPIO
        GPIO.output(PIN_TRIG, GPIO.LOW)
        time.sleep(0.06)
        GPIO.output(PIN_TRIG, GPIO.HIGH)
        time.sleep(0.00002)
        GPIO.output(PIN_TRIG, GPIO.LOW)

        start = time.monotonic()
        while GPIO.input(PIN_ECHO) == 0:
            if time.monotonic() - start > 0.5:
                log.warning("HC-SR04: Echo-Timeout kein HIGH.")
                return None

        t1 = time.monotonic()
        while GPIO.input(PIN_ECHO) == 1:
            if time.monotonic() - t1 > 0.5:
                log.warning("HC-SR04: Echo-Timeout kein LOW.")
                return None

        distanz_cm = (time.monotonic() - t1) * 17150
        return distanz_cm

    def _poll_schleife(self):
        while not self._stop_evt.is_set():
            if self.mock:
                with self._lock:
                    vorhanden = self._vorhanden
            else:
                d = self._messen()
                vorhanden = d is not None and d < SENSOR_BEREICH_CM

            with self._lock:
                if vorhanden:
                    self._zaehler = min(self._zaehler + 1, SENSOR_BEST)
                else:
                    self._zaehler = 0
                self._erkannt = self._zaehler >= SENSOR_BEST
            time.sleep(SENSOR_INTERVALL)

    @property
    def erkannt(self) -> bool:
        with self._lock:
            return self._erkannt

    def stoppe(self):
        self._stop_evt.set()
        if not self.mock:
            _RPIGPIO.cleanup()
            log.info("GPIO Cleanup durchgeführt.")


# ============================================================
# Zustandsmaschine
# ============================================================
class RPiZA:
    S_CONFIG = "CONFIG"
    S_FZA_GRUEN = "FZA_GRUEN"
    S_FZA_GELB = "FZA_GELB"
    S_ZWISCHENZEIT = "ZWISCHENZEIT"
    S_FGA_GRUEN = "FGA_GRUEN"
    S_RAEUMZEIT = "RAEUMZEIT"
    S_ROT_GELB = "FZA_ROT_GELB"
    S_FEHLER = "FEHLER"
    S_AUS = "AUS"

    def __init__(self, mock=None):
        if mock is None:
            mock = not _HARDWARE
        self.mock = mock
        LED = _MockLED if mock else _HWLED

        self.fza_rot = LED(PIN_FZA_ROT)
        self.fza_gelb = LED(PIN_FZA_GELB)
        self.fza_gruen = LED(PIN_FZA_GRUEN)

        self.fga1_rot = LED(PIN_FGA1_ROT)
        self.fga1_gruen = LED(PIN_FGA1_GRUEN)

        self.fga2_rot = LED(PIN_FGA2_ROT)
        self.fga2_gruen = LED(PIN_FGA2_GRUEN)

        self.sensor = FahrzeugSensor(mock=mock)

        self.fza_gruen_zeit = 120
        self.fga_gruen_zeit = 20

        self._zustand = self.S_CONFIG
        self._phase_start = time.monotonic()
        self.on_zustandswechsel = None

        self._stop_evt = threading.Event()
        self._fehler_evt = threading.Event()
        self._zyklus_thread = None
        self._fehler_grund = ""

        self._heartbeat = time.monotonic()
        self._konflikt_zaehler = 0
        self._wd_stop_evt = threading.Event()

        self._alle_rot()

        threading.Thread(
            target=self._sicherheits_schleife, daemon=True, name="Sicherheitsmonitor",
        ).start()

    # -------- LED-Schaltbilder --------
    def _alle_rot(self):
        self.fza_gruen.off()
        self.fza_gelb.off()
        self.fza_rot.on()
        self.fga1_gruen.off()
        self.fga2_gruen.off()
        self.fga1_rot.on()
        self.fga2_rot.on()

    def _alle_aus(self):
        self.fza_rot.off()
        self.fza_gelb.off()
        self.fza_gruen.off()
        self.fga1_rot.off()
        self.fga1_gruen.off()
        self.fga2_rot.off()
        self.fga2_gruen.off()

    def _schalte_fza_gruen(self):
        if self._fehler_evt.is_set():
            return
        self.fga1_gruen.off()
        self.fga2_gruen.off()
        self.fga1_rot.on()
        self.fga2_rot.on()
        self.fza_gelb.off()
        self.fza_rot.off()
        self.fza_gruen.on()

    def _schalte_fza_gelb(self):
        if self._fehler_evt.is_set():
            return
        self.fza_gruen.off()
        self.fza_rot.off()
        self.fza_gelb.on()

    def _schalte_fza_rot_gelb(self):
        if self._fehler_evt.is_set():
            return
        self.fga1_gruen.off()
        self.fga2_gruen.off()
        self.fga1_rot.on()
        self.fga2_rot.on()
        self.fza_gruen.off()
        self.fza_rot.on()
        self.fza_gelb.on()

    def _schalte_fga_gruen(self):
        if self._fehler_evt.is_set():
            return
        self.fza_gruen.off()
        self.fza_gelb.off()
        self.fza_rot.on()
        self.fga1_rot.off()
        self.fga2_rot.off()
        self.fga1_gruen.on()
        self.fga2_gruen.on()

    # -------- Zeit / Zustand --------
    def _fza_gruen_dauer(self) -> float:
        return float(self.fza_gruen_zeit)

    def _warte(self, sekunden: float) -> bool:
        ende = time.monotonic() + sekunden
        while time.monotonic() < ende:
            if self._stop_evt.is_set() or self._fehler_evt.is_set():
                return False
            self._heartbeat = time.monotonic()
            time.sleep(0.02)
        return True

    def _warte_fga_gruen(self, max_sekunden: float):
        phasen_dauer = max(max_sekunden, T_MIN_GRUEN_FGA)
        start = time.monotonic()
        phasen_ende = start + phasen_dauer
        min_gruen_ende = start + T_MIN_GRUEN_FGA

        while time.monotonic() < phasen_ende:
            if self._stop_evt.is_set() or self._fehler_evt.is_set():
                return
            self._heartbeat = time.monotonic()
            if time.monotonic() >= min_gruen_ende and self.sensor.erkannt:
                log.info("Adaptive Verkürzung der FgA-Grünphase ausgelöst.")
                return
            time.sleep(0.02)

    def _setze_zustand(self, zustand: str):
        self._zustand = zustand
        self._phase_start = time.monotonic()
        self._heartbeat = time.monotonic()
        log.info("Zustandswechsel → %s", zustand)
        if self.on_zustandswechsel:
            self.on_zustandswechsel()

    @property
    def zustand(self) -> str:
        return self._zustand

    @property
    def phase_vergangen(self) -> float:
        return time.monotonic() - self._phase_start

    @property
    def fehler_grund(self) -> str:
        return self._fehler_grund

    @property
    def led_zustaende(self) -> dict:
        return {
            "fza_rot": bool(self.fza_rot.value),
            "fza_gelb": bool(self.fza_gelb.value),
            "fza_gruen": bool(self.fza_gruen.value),
            "fga1_rot": bool(self.fga1_rot.value),
            "fga1_gruen": bool(self.fga1_gruen.value),
            "fga2_rot": bool(self.fga2_rot.value),
            "fga2_gruen": bool(self.fga2_gruen.value),
        }

    # -------- Sicherheitsüberwachung --------
    def _zyklus_aktiv(self) -> bool:
        t = self._zyklus_thread
        return t is not None and t.is_alive() and not self._stop_evt.is_set()

    def _watchdog_abgelaufen(self) -> bool:
        return time.monotonic() - self._heartbeat > WATCHDOG_TIMEOUT

    def _pruefe_vertraeglichkeit(self) -> bool:
        leds = self.led_zustaende
        konflikt = leds["fza_gruen"] and (
            leds["fga1_gruen"] or leds["fga2_gruen"]
        )
        if konflikt:
            self._konflikt_zaehler += 1
        else:
            self._konflikt_zaehler = 0
        return self._konflikt_zaehler < CONFLICT_BEST

    def _sicherheits_schleife(self):
        while not self._wd_stop_evt.is_set():
            if not self._fehler_evt.is_set():
                if not self._pruefe_vertraeglichkeit():
                    self.fehler_ausloesen("Verträglichkeitsverletzung")
                elif self._zyklus_aktiv() and self._watchdog_abgelaufen():
                    self.fehler_ausloesen("Watchdog-Timeout")
            time.sleep(WD_INTERVALL)

    def fehler_ausloesen(self, grund: str = "manuell"):
        if self._fehler_evt.is_set():
            return
        self._fehler_grund = grund
        self._fehler_evt.set()
        self._stop_evt.set()
        self._alle_rot()
        self._setze_zustand(self.S_FEHLER)
        log.error("Fehler ausgelöst: %s — alle Ampeln Rot.", grund)

    def quittiere_fehler_aus(self):
        log.info("Fehler quittieren / Anlage ausschalten.")
        self._stop_evt.set()
        t = self._zyklus_thread
        if t is not None and t.is_alive() and t is not threading.current_thread():
            t.join(timeout=2.0)
        self._fehler_evt.clear()
        self._fehler_grund = ""
        self._konflikt_zaehler = 0
        self._heartbeat = time.monotonic()
        self._alle_aus()
        self._setze_zustand(self.S_AUS)

    # -------- Ablauf --------
    def starte(self):
        if self._fehler_evt.is_set():
            log.warning("Start blockiert: Anlage befindet sich im Fehlerzustand.")
            return
        self._stop_evt.clear()
        self._fehler_evt.clear()
        self._konflikt_zaehler = 0
        self._heartbeat = time.monotonic()
        t = threading.Thread(
            target=self._zyklus_wrapper, daemon=True, name="ZyklusThread",
        )
        self._zyklus_thread = t
        t.start()

    def _zyklus_wrapper(self):
        try:
            self._zyklus()
        except Exception:
            log.exception("Unbehandelte Ausnahme im Zyklus.")
            self.fehler_ausloesen("Ausnahme im Zyklus")

    def _zyklus(self):
        while not self._stop_evt.is_set():
            self._setze_zustand(self.S_FZA_GRUEN)
            self._schalte_fza_gruen()
            if not self._warte(self._fza_gruen_dauer()):
                break

            self._setze_zustand(self.S_FZA_GELB)
            self._schalte_fza_gelb()
            if not self._warte(T_GELB):
                break

            self._setze_zustand(self.S_ZWISCHENZEIT)
            self._alle_rot()
            if not self._warte(T_ZWISCHENZEIT):
                break

            self._setze_zustand(self.S_FGA_GRUEN)
            self._schalte_fga_gruen()
            self._warte_fga_gruen(self.fga_gruen_zeit)
            if self._stop_evt.is_set():
                break

            self._setze_zustand(self.S_RAEUMZEIT)
            self._alle_rot()
            if not self._warte(T_RAEUMZEIT):
                break

            self._setze_zustand(self.S_ROT_GELB)
            self._schalte_fza_rot_gelb()
            if not self._warte(T_ROT_GELB):
                break

        if self._fehler_evt.is_set():
            return

        self._alle_aus()
        self._setze_zustand(self.S_AUS)
        log.info("Zyklus beendet — Exit-Zustand AUS.")

    def stoppe(self):
        log.info("Stop angefordert.")
        self._stop_evt.set()
        t = self._zyklus_thread
        if t is not None and t.is_alive() and t is not threading.current_thread():
            t.join(timeout=2.0)
        if self._fehler_evt.is_set():
            self.quittiere_fehler_aus()
            return
        self._alle_aus()
        self._setze_zustand(self.S_AUS)

    def aufraeumen(self):
        self._wd_stop_evt.set()
        self._stop_evt.set()
        self._alle_aus()
        self.sensor.stoppe()


if __name__ == "__main__":
    modus = "Echtbetrieb" if _HARDWARE else "Mock-/Testbetrieb"
    print(f"rpiza.py — RPiZA-Steuerkern geladen ({modus}).")
    print("Zum Nachweis die Testfälle ausführen:")
    print("  python3 test_tc_p01.py")
    print("  python3 test_tc_p02.py")
    print("  python3 test_tc_s01.py")
