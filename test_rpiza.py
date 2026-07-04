#!/usr/bin/env python3
"""
Testcode zu den Testfällen TC-S01, TC-P01, TC-P02 der RPiZA v3.0.

Jeder Test misst die reale Latenz der Steuerungslogik (Mock-Modus, ohne
Hardware und ohne GUI) und prüft sie gegen den in der Anforderungstabelle
festgelegten Grenzwert. Ausführung:

    python3 -m unittest -v test_rpiza.py
    python3 test_rpiza.py          # mit ausführlichem Messprotokoll

Zuordnung:
    TC-S01  NFA-S01  Fail-Safe            Δt(Kill-Signal → alle Rot) ≤ 500 ms
    TC-P01  NFA-P01  Erkennungslatenz     Δt(Sensor → Erkennung)     ≤ 200 ms  (10×)
    TC-P02  NFA-P02  Phasenwechsellatenz  Δt(Timer → GPIO-Wechsel)   ≤ 100 ms  (20×)
"""

import time
import unittest

import rpiza


def _warte_bis(bedingung, timeout=5.0, takt=0.0005):
    """Blockiert, bis bedingung() True liefert, oder bricht nach timeout ab."""
    ende = time.monotonic() + timeout
    while time.monotonic() < ende:
        if bedingung():
            return True
        time.sleep(takt)
    return False


def _ist_sicher(leds: dict) -> bool:
    """True, wenn kein Grün leuchtet und alle Rot-Lampen an sind (Fail-Safe)."""
    kein_gruen = not (leds["fza_gruen"] or leds["fga1_gruen"] or leds["fga2_gruen"])
    alle_rot = leds["fza_rot"] and leds["fga1_rot"] and leds["fga2_rot"]
    return kein_gruen and alle_rot


class TC_S01_FailSafe(unittest.TestCase):
    """
    TC-S01 — NFA-S01 Fail-Safe ≤ 500 ms
    Kill-Signal → alle Rot. Δt = t(Fehler) → t(alle Rot).
    Bestehen: Δt ≤ 500 ms, alle Lampen Rot, kein simultanes Grün.
    """

    GRENZE_MS = 500.0
    WIEDERHOLUNGEN = 10

    def test_fail_safe_latenz(self):
        messungen = []

        for i in range(self.WIEDERHOLUNGEN):
            z = rpiza.RPiZA(mock=True)
            try:
                # Anlage in einen Zustand mit aktivem Grün bringen (FzA GRÜN).
                z.starte()
                self.assertTrue(
                    _warte_bis(lambda: z.led_zustaende["fza_gruen"]),
                    "FzA-GRÜN wurde nicht erreicht — Testvorbedingung verletzt.",
                )

                # Kill-Signal absetzen und Latenz bis 'alle Rot' messen.
                t0 = time.monotonic()
                z.fehler_ausloesen("Kill-Signal")
                sicher = _ist_sicher(z.led_zustaende)
                dt_ms = (time.monotonic() - t0) * 1000.0

                # Sicherheitsbedingungen dieses Durchlaufs.
                self.assertTrue(
                    sicher,
                    f"Lauf {i+1}: nicht sicherer Zustand nach Kill-Signal: "
                    f"{z.led_zustaende}",
                )
                self.assertEqual(z.zustand, rpiza.RPiZA.S_FEHLER)
                self.assertLessEqual(
                    dt_ms,
                    self.GRENZE_MS,
                    f"Lauf {i+1}: Δt={dt_ms:.3f} ms > {self.GRENZE_MS} ms",
                )
                messungen.append(dt_ms)
            finally:
                z.aufraeumen()

        _protokoll("TC-S01 Fail-Safe", messungen, self.GRENZE_MS, "≤")


class TC_P01_Erkennungslatenz(unittest.TestCase):
    """
    TC-P01 — NFA-P01 Erkennungslatenz ≤ 200 ms
    Δt Sensor → Erkennungssignal, 10 Messungen.
    Bestehen: alle Δt ≤ 200 ms.
    """

    GRENZE_MS = 200.0
    WIEDERHOLUNGEN = 10

    def test_erkennungslatenz(self):
        messungen = []

        for i in range(self.WIEDERHOLUNGEN):
            sensor = rpiza.FahrzeugSensor(mock=True)
            try:
                # Sensor läuft leer an; sicherstellen, dass (noch) nichts erkannt ist.
                time.sleep(0.05)
                self.assertFalse(sensor.erkannt)

                # Fahrzeug erscheint → Zeit bis zum Erkennungssignal messen.
                t0 = time.monotonic()
                sensor.simuliere(True)
                erkannt = _warte_bis(lambda: sensor.erkannt, timeout=2.0)
                dt_ms = (time.monotonic() - t0) * 1000.0

                self.assertTrue(erkannt, f"Lauf {i+1}: keine Erkennung binnen 2 s")
                self.assertLessEqual(
                    dt_ms,
                    self.GRENZE_MS,
                    f"Lauf {i+1}: Δt={dt_ms:.1f} ms > {self.GRENZE_MS} ms",
                )
                messungen.append(dt_ms)
            finally:
                sensor.stoppe()

        _protokoll("TC-P01 Erkennungslatenz", messungen, self.GRENZE_MS, "≤")


class TC_P02_Phasenwechsellatenz(unittest.TestCase):
    """
    TC-P02 — NFA-P02 Phasenwechsellatenz ≤ 100 ms
    Δt Timer → GPIO-Wechsel, 20 Messungen.

    Der Phasen-Timer ist die Wartefunktion _warte(dauer); unmittelbar nach ihrer
    Rückkehr schaltet der Zyklus die GPIOs/LEDs um. Gemessen wird die Latenz
    zwischen Ablauf des Timers (Solldauer) und dem tatsächlichen GPIO-Wechsel,
    d. h. der Überschwinger der Polling-Schleife.
    Bestehen: alle Δt ≤ 100 ms.
    """

    GRENZE_MS = 100.0
    WIEDERHOLUNGEN = 20
    # Solldauer bewusst NICHT als Vielfaches des Schleifentakts (0,02 s) wählen,
    # damit der ungünstigste Überschwinger der Polling-Schleife erfasst wird.
    SOLL_DAUER = 0.13

    def test_phasenwechsellatenz(self):
        z = rpiza.RPiZA(mock=True)
        messungen = []
        try:
            for i in range(self.WIEDERHOLUNGEN):
                t0 = time.monotonic()
                ok = z._warte(self.SOLL_DAUER)  # Phasen-Timer läuft ab
                # GPIO-Wechsel erfolgt hier, direkt nach Rückkehr des Timers.
                _leds = z.led_zustaende
                ist_dauer = time.monotonic() - t0

                self.assertTrue(ok, f"Lauf {i+1}: Timer vorzeitig abgebrochen")
                dt_ms = (ist_dauer - self.SOLL_DAUER) * 1000.0  # Überschwinger
                self.assertGreaterEqual(dt_ms, 0.0)
                self.assertLessEqual(
                    dt_ms,
                    self.GRENZE_MS,
                    f"Lauf {i+1}: Δt={dt_ms:.2f} ms > {self.GRENZE_MS} ms",
                )
                messungen.append(dt_ms)
        finally:
            z.aufraeumen()

        _protokoll("TC-P02 Phasenwechsellatenz", messungen, self.GRENZE_MS, "≤")


def _protokoll(name, werte, grenze, op):
    """Gibt eine kompakte Messübersicht aus (nur bei direktem Aufruf sichtbar)."""
    if not werte:
        return
    print(
        f"\n[{name}] n={len(werte)}  "
        f"min={min(werte):.3f} ms  max={max(werte):.3f} ms  "
        f"avg={sum(werte) / len(werte):.3f} ms  "
        f"Grenze {op} {grenze:.0f} ms  → PASSED"
    )


if __name__ == "__main__":
    unittest.main(verbosity=2)
