#!/usr/bin/env python3
"""
HelioCore OS — Sun Tracking Algorithm

Uses LDR sensor differences to determine sun direction
and drives base/tilt motors to align the solar panel.

Logic:
  alignment_error = ldr_left - ldr_right

  alignment_error > 0 → sun is left  → rotate base left  (direction = -1)
  alignment_error < 0 → sun is right → rotate base right (direction =  1)
  alignment_error == 0 → aligned     → stop              (direction =  0)

  vertical_error = ldr_top - ldr_bottom

  vertical_error > 0 → sun is high → tilt up
  vertical_error < 0 → sun is low  → tilt down
"""
import time


class TrackingAlgorithm:
    def __init__(self, sensor_manager, motor_controller, config=None):
        self.sensor = sensor_manager
        self.motor = motor_controller
        self.config = config or {}

        # Tracking thresholds
        self.threshold = 1           # Minimum LDR difference to trigger movement
        self.step_size = 2           # Degrees per tracking step
        self.update_interval = 2.0   # Seconds between tracking updates

        # State
        self.active = False
        self.tracking_direction = 0  # -1=left, 0=aligned, 1=right
        self.alignment_error = 0     # ldr_left - ldr_right

    def calculate_tracking_adjustment(self):
        """
        Read LDR sensors and calculate motor adjustments.
        Returns: (base_adjustment, tilt_adjustment)
        """
        light = self.sensor.get_directional_light()

        base_adjustment = 0
        tilt_adjustment = 0

        # ── Horizontal tracking (base motor) ──
        h_diff = light['left'] - light['right']
        self.alignment_error = h_diff

        if h_diff > 0:
            # Sun is to the left → rotate base left
            base_adjustment = -self.step_size
            self.tracking_direction = -1
        elif h_diff < 0:
            # Sun is to the right → rotate base right
            base_adjustment = self.step_size
            self.tracking_direction = 1
        else:
            # Aligned
            self.tracking_direction = 0

        # ── Vertical tracking (tilt motor) ──
        v_diff = light['top'] - light['bottom']
        if v_diff > 0:
            tilt_adjustment = self.step_size    # Sun is high → tilt up
        elif v_diff < 0:
            tilt_adjustment = -self.step_size   # Sun is low → tilt down

        return base_adjustment, tilt_adjustment

    def update(self):
        """Run one cycle of the tracking algorithm."""
        if not self.active:
            return False

        base_adj, tilt_adj = self.calculate_tracking_adjustment()

        if base_adj != 0:
            self.motor.move_base_relative(base_adj)

        if tilt_adj != 0:
            self.motor.move_tilt_relative(tilt_adj)

        return base_adj != 0 or tilt_adj != 0

    def start(self):
        """Enable sun tracking and open petals."""
        self.active = True
        self.motor.open_petals()

    def stop(self):
        """Disable sun tracking."""
        self.active = False
        self.tracking_direction = 0
        self.alignment_error = 0

    def is_active(self):
        """Return whether tracking is currently active."""
        return self.active

    def get_tracking_state(self):
        """Return current tracking metrics for telemetry."""
        return {
            'tracking_active': int(self.active),
            'tracking_direction': self.tracking_direction,
            'alignment_error': self.alignment_error,
        }


# ── Standalone test ──
if __name__ == '__main__':
    import json
    from sensor_manager import SensorManager
    from motor_controller import MotorController

    print("HelioCore OS — Tracking Algorithm Test")
    print("=" * 50)

    sensor = SensorManager()
    motor = MotorController()
    tracker = TrackingAlgorithm(sensor, motor)

    try:
        print("Starting sun tracking...")
        tracker.start()

        for i in range(20):
            light = sensor.get_directional_light()
            moved = tracker.update()
            state = motor.get_state()
            track = tracker.get_tracking_state()

            print(f"\n[{i+1}] Light: L={light['left']} R={light['right']} "
                  f"T={light['top']} B={light['bottom']}")
            print(f"     Position: Base={state['base_angle']}° Tilt={state['tilt_angle']}°")
            print(f"     Tracking: dir={track['tracking_direction']} "
                  f"error={track['alignment_error']} moved={moved}")

            time.sleep(2)

        tracker.stop()
        motor.safe_position()

    except KeyboardInterrupt:
        tracker.stop()
        motor.safe_position()
        sensor.cleanup()
        motor.cleanup()
        print("\nTracking test complete")
