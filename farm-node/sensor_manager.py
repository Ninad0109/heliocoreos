#!/usr/bin/env python3
"""
HelioCore OS — Sensor Manager (Real Hardware)

GPIO Pin Mapping (BCM mode):
  LDR left_bottom   → GPIO 6
  LDR left_top      → GPIO 26
  LDR right_top     → GPIO 17
  LDR right_bottom  → GPIO 5
  Rain sensor       → GPIO 15

Telemetry output:
  ldr_left   = left_top + left_bottom     (0–2)
  ldr_right  = right_top + right_bottom   (0–2)
  ldr_top    = left_top + right_top       (0–2)
  ldr_bottom = left_bottom + right_bottom (0–2)
  rain       = 0 (dry) / 1 (rain detected)
"""
import time

try:
    import RPi.GPIO as GPIO
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False

# ── GPIO pin definitions ──
PIN_LDR_LEFT_BOTTOM  = 6
PIN_LDR_LEFT_TOP     = 26
PIN_LDR_RIGHT_TOP    = 17
PIN_LDR_RIGHT_BOTTOM = 5
PIN_RAIN             = 15

ALL_LDR_PINS = [
    PIN_LDR_LEFT_BOTTOM,
    PIN_LDR_LEFT_TOP,
    PIN_LDR_RIGHT_TOP,
    PIN_LDR_RIGHT_BOTTOM,
]
ALL_SENSOR_PINS = ALL_LDR_PINS + [PIN_RAIN]


class SensorManager:
    def __init__(self, config=None):
        """Initialize GPIO pins for all sensors."""
        self.config = config or {}

        if HAS_GPIO:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            for pin in ALL_SENSOR_PINS:
                GPIO.setup(pin, GPIO.IN)
            print(f"  [SENSOR] GPIO initialized: LDR {ALL_LDR_PINS}, Rain [{PIN_RAIN}]")
        else:
            print("  [SENSOR] RPi.GPIO not available — running in simulation mode")

    # ── Raw reads ──

    def _read_pin(self, pin):
        """Read a single GPIO pin. Returns 0 or 1."""
        if HAS_GPIO:
            return GPIO.input(pin)
        return 0

    def read_ldr_raw(self):
        """Read all 4 LDR sensors as individual values."""
        return {
            'left_bottom':  self._read_pin(PIN_LDR_LEFT_BOTTOM),
            'left_top':     self._read_pin(PIN_LDR_LEFT_TOP),
            'right_top':    self._read_pin(PIN_LDR_RIGHT_TOP),
            'right_bottom': self._read_pin(PIN_LDR_RIGHT_BOTTOM),
        }

    def read_rain(self):
        """Read rain sensor. Returns True if rain detected."""
        return bool(self._read_pin(PIN_RAIN))

    # ── Directional light (pairs) ──

    def get_directional_light(self):
        """Combine LDR pairs into directional light readings."""
        raw = self.read_ldr_raw()
        return {
            'left':   raw['left_top']   + raw['left_bottom'],
            'right':  raw['right_top']  + raw['right_bottom'],
            'top':    raw['left_top']   + raw['right_top'],
            'bottom': raw['left_bottom'] + raw['right_bottom'],
        }

    # ── Telemetry ──

    def get_telemetry(self):
        """Get all sensor data formatted for telemetry transmission."""
        raw = self.read_ldr_raw()
        return {
            'ldr_left':   raw['left_top']   + raw['left_bottom'],
            'ldr_right':  raw['right_top']  + raw['right_bottom'],
            'ldr_top':    raw['left_top']   + raw['right_top'],
            'ldr_bottom': raw['left_bottom'] + raw['right_bottom'],
            'rain':       int(self.read_rain()),
        }

    # ── Backward-compatible methods ──

    def read_all_ldr(self):
        """Return a list of all 4 raw LDR values (backward compat)."""
        raw = self.read_ldr_raw()
        return [raw['left_bottom'], raw['left_top'], raw['right_top'], raw['right_bottom']]

    def cleanup(self):
        """Release GPIO resources."""
        if HAS_GPIO:
            GPIO.cleanup()
            print("  [SENSOR] GPIO cleaned up")


# ── Standalone test ──
if __name__ == '__main__':
    print("HelioCore OS — Sensor Manager Test")
    print("=" * 50)
    sensor = SensorManager()

    try:
        while True:
            raw = sensor.read_ldr_raw()
            data = sensor.get_telemetry()
            light = sensor.get_directional_light()

            print(f"\nRaw LDR: LB={raw['left_bottom']} LT={raw['left_top']} "
                  f"RT={raw['right_top']} RB={raw['right_bottom']}")
            print(f"Directional: L={light['left']} R={light['right']} "
                  f"T={light['top']} B={light['bottom']}")
            print(f"Telemetry: L={data['ldr_left']} R={data['ldr_right']} "
                  f"T={data['ldr_top']} B={data['ldr_bottom']} | Rain={data['rain']}")
            time.sleep(1)

    except KeyboardInterrupt:
        sensor.cleanup()
        print("\nSensor test complete")
