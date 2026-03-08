#!/usr/bin/env python3
"""
HelioCore OS — Motor Controller (Real Hardware DRV8825)

GPIO Pin Mapping (BCM mode):
  Base rotation motor:  DIR → GPIO 4,  STEP → GPIO 12
  Tilt motor:           DIR → GPIO 19, STEP → GPIO 13
  Flower petal motor:   DIR → GPIO 18, STEP → GPIO 27

DRV8825 step timing: 1ms high + 1ms low per microstep.
Base rotation limited to ±160°.
Tilt limited to 0°–90°.
"""
import time

try:
    import RPi.GPIO as GPIO
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False

# ── Motor pin definitions ──
PIN_BASE_DIR   = 4
PIN_BASE_STEP  = 12

PIN_TILT_DIR   = 19
PIN_TILT_STEP  = 13

PIN_PETAL_DIR  = 18
PIN_PETAL_STEP = 27

ALL_MOTOR_PINS = [
    PIN_BASE_DIR, PIN_BASE_STEP,
    PIN_TILT_DIR, PIN_TILT_STEP,
    PIN_PETAL_DIR, PIN_PETAL_STEP,
]

# Motor constants
STEPS_PER_REV = 200     # NEMA stepper: 200 steps/rev (1.8° per step)
MICROSTEPS    = 16      # DRV8825 microstepping (1/16)
STEP_DELAY    = 0.001   # 1ms per half-step → 500 steps/sec max

# Angle limits
BASE_MIN = -160
BASE_MAX = 160
TILT_MIN = 0
TILT_MAX = 90

# Petal motor steps for full open/close
PETAL_STEPS = 400


class MotorController:
    def __init__(self, config=None):
        """Initialize GPIO outputs for all motor drivers."""
        self.config = config or {}

        # Current positions
        self.base_angle = 0
        self.tilt_angle = 0
        self.petal_state = 0  # 0=CLOSED, 1=OPEN

        # Motor running state
        self._base_running = False
        self._tilt_running = False

        if HAS_GPIO:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            for pin in ALL_MOTOR_PINS:
                GPIO.setup(pin, GPIO.OUT)
                GPIO.output(pin, GPIO.LOW)
            print(f"  [MOTOR] GPIO initialized: Base [{PIN_BASE_STEP}/{PIN_BASE_DIR}], "
                  f"Tilt [{PIN_TILT_STEP}/{PIN_TILT_DIR}], "
                  f"Petal [{PIN_PETAL_STEP}/{PIN_PETAL_DIR}]")
        else:
            print("  [MOTOR] RPi.GPIO not available — running in simulation mode")

        # Expose pin constants as instance attributes for external access
        self.PIN_BASE_DIR   = PIN_BASE_DIR
        self.PIN_BASE_STEP  = PIN_BASE_STEP
        self.PIN_TILT_DIR   = PIN_TILT_DIR
        self.PIN_TILT_STEP  = PIN_TILT_STEP
        self.PIN_PETAL_DIR  = PIN_PETAL_DIR
        self.PIN_PETAL_STEP = PIN_PETAL_STEP

    # ── Low-level step control ──

    def step_motor(self, step_pin, dir_pin, direction, steps):
        """
        Drive a DRV8825 stepper motor.

        Args:
            step_pin: GPIO pin connected to STEP input
            dir_pin:  GPIO pin connected to DIR input
            direction: 1 for CW (HIGH), -1 for CCW (LOW)
            steps:    number of microsteps to execute
        """
        if not HAS_GPIO:
            return

        GPIO.output(dir_pin, GPIO.HIGH if direction > 0 else GPIO.LOW)
        time.sleep(0.001)  # DIR settle time

        for _ in range(abs(steps)):
            GPIO.output(step_pin, GPIO.HIGH)
            time.sleep(STEP_DELAY)
            GPIO.output(step_pin, GPIO.LOW)
            time.sleep(STEP_DELAY)

    def _angle_to_steps(self, angle_delta):
        """Convert an angle delta to microsteps."""
        return int((angle_delta / 360.0) * STEPS_PER_REV * MICROSTEPS)

    # ── Base rotation (±160°) ──

    def set_base_angle(self, angle):
        """Move base motor to an absolute angle (clamped to ±160°)."""
        angle = max(BASE_MIN, min(angle, BASE_MAX))
        delta = angle - self.base_angle
        steps = self._angle_to_steps(abs(delta))

        if steps > 0:
            self._base_running = True
            self.step_motor(PIN_BASE_STEP, PIN_BASE_DIR,
                            1 if delta > 0 else -1, steps)
            self.base_angle = angle
            self._base_running = False

    def move_base_relative(self, delta_angle):
        """Move base motor by a relative angle."""
        self.set_base_angle(self.base_angle + delta_angle)

    # ── Tilt (0°–90°) ──

    def set_tilt_angle(self, angle):
        """Move tilt motor to an absolute angle (clamped to 0°–90°)."""
        angle = max(TILT_MIN, min(angle, TILT_MAX))
        delta = angle - self.tilt_angle
        steps = self._angle_to_steps(abs(delta))

        if steps > 0:
            self._tilt_running = True
            self.step_motor(PIN_TILT_STEP, PIN_TILT_DIR,
                            1 if delta > 0 else -1, steps)
            self.tilt_angle = angle
            self._tilt_running = False

    def move_tilt_relative(self, delta_angle):
        """Move tilt motor by a relative angle."""
        self.set_tilt_angle(self.tilt_angle + delta_angle)

    # ── Petal motor ──

    def set_petal_state(self, state):
        """Open (1) or close (0) the flower petals."""
        if state != self.petal_state:
            direction = 1 if state else -1
            self.step_motor(PIN_PETAL_STEP, PIN_PETAL_DIR,
                            direction, PETAL_STEPS)
            self.petal_state = state

    def open_petals(self):
        """Open flower petals."""
        self.set_petal_state(1)

    def close_petals(self):
        """Close flower petals."""
        self.set_petal_state(0)

    # ── Status ──

    def get_state(self):
        """Return current motor positions and states."""
        return {
            'petal_state': self.petal_state,
            'tilt_angle': self.tilt_angle,
            'base_angle': self.base_angle,
            'base_running': self._base_running,
            'tilt_running': self._tilt_running,
        }

    def safe_position(self):
        """Move all motors to safe/home position."""
        print("  [MOTOR] Moving to safe position...")
        self.close_petals()
        self.set_tilt_angle(0)
        self.set_base_angle(0)
        print("  [MOTOR] Safe position reached")

    def cleanup(self):
        """Release GPIO resources."""
        if HAS_GPIO:
            for pin in ALL_MOTOR_PINS:
                GPIO.output(pin, GPIO.LOW)
            GPIO.cleanup()
            print("  [MOTOR] GPIO cleaned up")


# ── Standalone test ──
if __name__ == '__main__':
    print("HelioCore OS — Motor Controller Test")
    print("=" * 50)
    motor = MotorController()

    try:
        print("\n1. Opening petals...")
        motor.open_petals()
        print(f"   State: {motor.get_state()}")
        time.sleep(1)

        print("\n2. Setting tilt to 45°...")
        motor.set_tilt_angle(45)
        print(f"   State: {motor.get_state()}")
        time.sleep(1)

        print("\n3. Rotating base to 30°...")
        motor.set_base_angle(30)
        print(f"   State: {motor.get_state()}")
        time.sleep(1)

        print("\n4. Rotating base to -30°...")
        motor.set_base_angle(-30)
        print(f"   State: {motor.get_state()}")
        time.sleep(1)

        print("\n5. Returning to safe position...")
        motor.safe_position()
        print(f"   State: {motor.get_state()}")

    except KeyboardInterrupt:
        motor.safe_position()
        motor.cleanup()
        print("\nMotor test complete")
