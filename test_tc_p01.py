#!/usr/bin/env python3
"""
================================================================
TC-P01 — NFA-P01 Erkennungslatenz ≤ 200 ms
================================================================
Δt Sensor → Erkennungssignal, 10 Messungen.
Bestehen: alle 10 Δt ≤ 200 ms.

Hinweis: setzt SENSOR_INTERVALL = 0.05 in rpiza.py voraus
(bei 0.1 ergäbe die 3-fach-Entprellung ~250 ms und würde die Grenze reißen).

Ausführung:
    python3 test_tc_p01.py
"""

import time
import unittest

import rpiza


class TC_P01_Erkennungslatenz(unittest.TestCase):

    GRENZE_MS = 200.0
    WIEDERHOLUNGEN = 10

    def test_erkennungslatenz(self):
        messungen = []

        for i in range(self.WIEDERHOLUNGEN):
            sensor = rpiza.FahrzeugSensor(mock=True)
            try:
                # 1) Sensor läuft leer an — es darf noch nichts erkannt sein.
                time.sleep(0.05)
                self.assertFalse(sensor.erkannt, "Sensor erkennt fälschlich ein Fahrzeug")

                # 2) Fahrzeug erscheint → Zeit bis zum Erkennungssignal messen.
                t0 = time.monotonic()
                sensor.simuliere(True)

                ende = time.monotonic() + 2.0
                while not sensor.erkannt:
                    self.assertLess(time.monotonic(), ende, "keine Erkennung binnen 2 s")
                    time.sleep(0.0005)

                dt_ms = (time.monotonic() - t0) * 1000.0

                # 3) Grenzwert prüfen.
                self.assertLessEqual(
                    dt_ms, self.GRENZE_MS,
                    f"Lauf {i+1}: Δt={dt_ms:.1f} ms > {self.GRENZE_MS} ms",
                )
                messungen.append(dt_ms)
                print(f"  Lauf {i+1:2d}: Δt = {dt_ms:7.1f} ms")
            finally:
                sensor.stoppe()

        print(f"\nTC-P01 Erkennungslatenz: n={len(messungen)}  "
              f"max={max(messungen):.1f} ms  Grenze ≤ {self.GRENZE_MS:.0f} ms  → PASSED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
