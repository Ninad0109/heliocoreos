#!/usr/bin/env python3
"""
HelioCore OS — Farm Node Main Loop

Continuous control loop (1 Hz):
  1. Read sensors (LDR + rain)
  2. Run rain protection logic
  3. Run sun tracking algorithm
  4. Control motors
  5. Collect telemetry (21 metrics)
  6. Send telemetry to Master-Pi

Run:  python3 farm-node/farm_node.py
"""
import json
import time
import signal
import sys
import os

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

import requests

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sensor_manager import SensorManager
from motor_controller import MotorController
from tracking_algorithm import TrackingAlgorithm
from rain_protection import RainProtection


class FarmNode:
    def __init__(self, config_path=None):
        # Find config.json relative to this script
        if config_path is None:
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')

        with open(config_path) as f:
            self.config = json.load(f)

        self.master_url = f"http://{self.config['master_ip']}:{self.config['master_port']}/telemetry"
        self.telemetry_interval = self.config.get('telemetry_interval', 1.0)

        # ── Initialize hardware ──
        print("=" * 60)
        print("  HelioCore OS — Farm Node")
        print("=" * 60)
        print(f"  Master-Pi: {self.master_url}")
        print(f"  Interval:  {self.telemetry_interval}s")
        print("")

        print("Initializing hardware...")
        self.sensor = SensorManager(self.config)
        self.motor = MotorController(self.config)
        self.tracker = TrackingAlgorithm(self.sensor, self.motor, self.config)
        self.protection = RainProtection(self.sensor, self.motor, self.tracker)

        self.running = False
        self._tx_count = 0
        self._tx_fail = 0

        # Graceful shutdown
        signal.signal(signal.SIGINT, self._shutdown_handler)
        signal.signal(signal.SIGTERM, self._shutdown_handler)

        print("  ✓ Hardware initialized")
        print("")

    # ── Startup sequence (runs once) ──

    def initialize_flower(self):
        """
        Boot sequence for the solar flower mechanism.
        Runs ONCE during system startup before the main loop.

        Order:
          1. Tilt motor raises panel to default angle (45°)
          2. Petal motor opens the flower panels
          3. Sun tracking enabled
        """
        print("")
        print("  HelioCore Boot Sequence Starting")
        print("  ─────────────────────────────────")

        # Step 1 — Tilt panel up
        print("  [1/3] Raising panel to default tilt...")
        TILT_UP_STEPS = 1200
        self.motor.step_motor(
            self.motor.PIN_TILT_STEP if hasattr(self.motor, 'PIN_TILT_STEP') else 13,
            self.motor.PIN_TILT_DIR if hasattr(self.motor, 'PIN_TILT_DIR') else 19,
            direction=1,
            steps=TILT_UP_STEPS
        )
        self.motor.tilt_angle = 45
        print("  ✓ Tilt position reached (45°)")

        # Step 2 — Open flower petals
        print("  [2/3] Opening flower petals...")
        PETAL_OPEN_STEPS = 1000
        self.motor.step_motor(
            self.motor.PIN_PETAL_STEP if hasattr(self.motor, 'PIN_PETAL_STEP') else 27,
            self.motor.PIN_PETAL_DIR if hasattr(self.motor, 'PIN_PETAL_DIR') else 18,
            direction=1,
            steps=PETAL_OPEN_STEPS
        )
        self.motor.petal_state = 1
        print("  ✓ Petals opened")

        # Step 3 — Enable sun tracking
        print("  [3/3] Enabling sun tracking...")
        self.tracker.active = True
        print("  ✓ Sun tracking enabled")

        print("  ─────────────────────────────────")
        print("  Boot sequence complete!")
        print("")

    # ── Telemetry collection ──

    def collect_telemetry(self):
        """Collect all 21 telemetry metrics from hardware."""
        sensor_data = self.sensor.get_telemetry()
        motor_state = self.motor.get_state()
        track_state = self.tracker.get_tracking_state()

        ldr_l = sensor_data['ldr_left']
        ldr_r = sensor_data['ldr_right']
        ldr_t = sensor_data['ldr_top']
        ldr_b = sensor_data['ldr_bottom']

        is_tracking = self.tracker.is_active() and not self.protection.is_protected()

        # Tracking direction for dashboard (0=idle, 1=east, 2=west, 3=up, 4=down, 5=zenith)
        raw_dir = track_state['tracking_direction']
        if not is_tracking:
            dashboard_direction = 0   # idle
        elif raw_dir > 0:
            dashboard_direction = 1   # east (right)
        elif raw_dir < 0:
            dashboard_direction = 2   # west (left)
        elif ldr_t > ldr_b:
            dashboard_direction = 3   # up
        elif ldr_b > ldr_t:
            dashboard_direction = 4   # down
        else:
            dashboard_direction = 5   # zenith (aligned)

        # Motor states: 0=idle, 1=running
        motor_base_state = 1 if is_tracking and abs(ldr_l - ldr_r) > 0 else 0
        motor_tilt_state = 1 if is_tracking and abs(ldr_t - ldr_b) > 0 else 0

        # System metrics
        cpu = psutil.cpu_percent(interval=0) if HAS_PSUTIL else 0.0
        mem = psutil.virtual_memory().percent if HAS_PSUTIL else 0.0

        telemetry = {
            # ── Original metrics ──
            'ldr_left':   ldr_l,
            'ldr_right':  ldr_r,
            'ldr_top':    ldr_t,
            'ldr_bottom': ldr_b,
            'rain':       sensor_data['rain'],
            'petal_state': motor_state['petal_state'],
            'tilt_angle': motor_state['tilt_angle'],
            'base_angle': motor_state['base_angle'],
            'motor_state': int(is_tracking),

            # ── Dashboard metrics ──
            'tracking_active':        int(is_tracking),
            'tracking_direction':     dashboard_direction,
            'alignment_error':        abs(ldr_l - ldr_r) + abs(ldr_t - ldr_b),
            'motor_base_state':       motor_base_state,
            'motor_tilt_state':       motor_tilt_state,
            'motor_temperature':      30,   # placeholder — no temp sensor yet
            'heliocore_service_health': 1,
            'light_intensity_avg':    round((ldr_l + ldr_r + ldr_t + ldr_b) / 4.0, 2),

            # ── System metrics ──
            'cpu_usage':    cpu,
            'memory_usage': mem,
        }

        return telemetry

    # ── Telemetry transmission ──

    def send_telemetry(self, data):
        """POST telemetry data to Master-Pi."""
        try:
            response = requests.post(self.master_url, json=data, timeout=2)
            if response.status_code == 200:
                self._tx_count += 1
                return True
            else:
                self._tx_fail += 1
                return False
        except Exception as e:
            self._tx_fail += 1
            return False

    # ── Main loop ──

    def run(self):
        """Main control loop (1 Hz)."""
        # Run startup sequence ONCE before main loop
        self.initialize_flower()
        self.running = True

        while self.running:
            try:
                # 1. Update rain protection (highest priority)
                prot_state = self.protection.update()

                # 2. Update sun tracking (if not protected)
                if not self.protection.is_protected():
                    self.tracker.update()

                # 3. Collect all telemetry
                telemetry = self.collect_telemetry()

                # 4. Send to Master-Pi
                tx_ok = self.send_telemetry(telemetry)

                # 5. Console status
                tx_status = "TX:OK" if tx_ok else "TX:FAIL"
                print(f"  [{prot_state.name:12s}] "
                      f"Base:{telemetry['base_angle']:6.0f}° "
                      f"Tilt:{telemetry['tilt_angle']:5.0f}° "
                      f"LDR L:{telemetry['ldr_left']} R:{telemetry['ldr_right']} "
                      f"T:{telemetry['ldr_top']} B:{telemetry['ldr_bottom']} "
                      f"Rain:{telemetry['rain']} "
                      f"Petal:{'OPEN' if telemetry['petal_state'] else 'SHUT'} "
                      f"{tx_status} ({self._tx_count}/{self._tx_count + self._tx_fail})")

                time.sleep(self.telemetry_interval)

            except Exception as e:
                print(f"  [ERROR] Control loop: {e}")
                time.sleep(1)

        self._cleanup()

    # ── Shutdown ──

    def _shutdown_handler(self, signum, frame):
        print("\n  Shutdown signal received...")
        self.running = False

    def _cleanup(self):
        print("  Moving to safe position...")
        self.tracker.stop()
        self.motor.safe_position()
        self.sensor.cleanup()
        self.motor.cleanup()
        print(f"  Transmitted {self._tx_count} telemetry packets "
              f"({self._tx_fail} failures)")
        print("  Farm Node shutdown complete")
        sys.exit(0)


# ── Entry point ──
if __name__ == '__main__':
    node = FarmNode()
    node.run()
