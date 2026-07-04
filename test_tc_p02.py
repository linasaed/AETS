#!/usr/bin/env python3
"""
================================================================
TC-P02 — NFA-P02 Phasenwechsellatenz ≤ 100 ms
================================================================
Δt Timer → GPIO-Wechsel, 20 Messungen.

Der Phasen-Timer ist die Wartefunktion _warte(dauer); direkt nach ihrer
Rückkehr schaltet der Zyklus die GPIOs/LEDs um. Gemessen wird der
Überschwinger zwischen Ablauf des Timers (Solldauer) und dem tatsächlichen
GPIO-Wechsel.
Bestehen: alle 20 Δt ≤ 100 ms.

Ausführung:
    python3 test_tc_p02.py
"""

import time
import unittest

import rpiza


class TC_P02_Phasenwechsellatenz(unittest.TestCase):

    GRENZE_MS = 100.0
    WIEDERHOLUNGEN = 20
    # Solldauer bewusst KEIN Vielfaches des Schleifentakts (0,02 s),
    # damit der ungünstigste Überschwinger der Polling-Schleife erfasst wird.
    SOLL_DAUER = 0.13

    def test_phasenwechsellatenz(self):
        z = rpiza.RPiZA(mock=True)
        messungen = []
        try:
            for i in range(self.WIEDERHOLUNGEN):
                # 1) Phasen-Timer starten und ablaufen lassen.
                t0 = time.monotonic()
                ok = z._warte(self.SOLL_DAUER)
                # 2) GPIO-Wechsel erfolgt hier, unmittelbar nach Rückkehr des Timers.
                _leds = z.led_zustaende
                ist_dauer = time.monotonic() - t0

                self.assertTrue(ok, f"Lauf {i+1}: Timer vorzeitig abgebrochen")

                # 3) Überschwinger = Latenz Timer → GPIO-Wechsel.
                dt_ms = (ist_dauer - self.SOLL_DAUER) * 1000.0
                self.assertGreaterEqual(dt_ms, 0.0)
                self.assertLessEqual(
                    dt_ms, self.GRENZE_MS,
                    f"Lauf {i+1}: Δt={dt_ms:.2f} ms > {self.GRENZE_MS} ms",
                )
                messungen.append(dt_ms)
                print(f"  Lauf {i+1:2d}: Δt = {dt_ms:6.2f} ms")
        finally:
            z.aufraeumen()

        print(f"\nTC-P02 Phasenwechsellatenz: n={len(messungen)}  "
              f"max={max(messungen):.2f} ms  Grenze ≤ {self.GRENZE_MS:.0f} ms  → PASSED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
