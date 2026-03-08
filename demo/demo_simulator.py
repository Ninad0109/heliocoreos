#!/usr/bin/env python3
"""
HelioCore OS — Farm-Pi Data Simulator
Generates realistic solar tracking data without hardware.
Simulates: sun movement, LDR readings, motor tracking, rain events.
"""
import time
import math
import random
import json
import requests
import signal
import sys
from datetime import datetime

class FarmSimulator:
    def __init__(self, master_url='http://localhost:5000'):
        self.master_url = master_url
        self.running = False

        # Simulated state
        self.base_angle = 0.0
        self.tilt_angle = 45.0
        self.petal_state = 1          # 1=open, 0=closed
        self.rain = 0
        self.rain_event_timer = 0

        # Sun position (simulated arc)
        self.sim_time = 0.0           # 0..1 = sunrise..sunset
        self.sim_speed = 0.002        # how fast time advances per tick

        # Tracking params
        self.step_size = 2.0
        self.threshold = 1

    def get_sun_position(self):
        """Simulate sun arc: rises east (-160), peaks overhead (0), sets west (+160)."""
        sun_azimuth = -160 + (self.sim_time * 320)          # -160 to +160
        sun_elevation = math.sin(self.sim_time * math.pi) * 90  # 0 to 90 to 0
        return sun_azimuth, max(0, sun_elevation)

    def get_ldr_readings(self, sun_az, sun_el):
        """Generate LDR readings based on sun position vs panel orientation."""
        az_diff = sun_az - self.base_angle
        el_diff = sun_el - self.tilt_angle

        # LEFT vs RIGHT (based on azimuth difference)
        if az_diff < -self.threshold:
            ldr_left = random.randint(1, 2)
            ldr_right = 0
        elif az_diff > self.threshold:
            ldr_left = 0
            ldr_right = random.randint(1, 2)
        else:
            ldr_left = random.randint(0, 1)
            ldr_right = random.randint(0, 1)

        # TOP vs BOTTOM (based on elevation difference)
        if el_diff > self.threshold:
            ldr_top = random.randint(1, 2)
            ldr_bottom = 0
        elif el_diff < -self.threshold:
            ldr_top = 0
            ldr_bottom = random.randint(1, 2)
        else:
            ldr_top = random.randint(0, 1)
            ldr_bottom = random.randint(0, 1)

        return ldr_left, ldr_right, ldr_top, ldr_bottom

    def update_tracking(self, ldr_left, ldr_right, ldr_top, ldr_bottom):
        """Simulate tracking algorithm adjusting motors."""
        if self.rain or self.petal_state == 0:
            return

        # Horizontal tracking
        if abs(ldr_left - ldr_right) >= self.threshold:
            if ldr_left > ldr_right:
                self.base_angle = max(-160, self.base_angle - self.step_size)
            else:
                self.base_angle = min(160, self.base_angle + self.step_size)

        # Vertical tracking
        if abs(ldr_top - ldr_bottom) >= self.threshold:
            if ldr_top > ldr_bottom:
                self.tilt_angle = min(90, self.tilt_angle + self.step_size)
            else:
                self.tilt_angle = max(0, self.tilt_angle - self.step_size)

    def update_rain(self):
        """Randomly trigger rain events for demo purposes."""
        if self.rain_event_timer > 0:
            self.rain_event_timer -= 1
            self.rain = 1
            self.petal_state = 0
            self.tilt_angle = 0
            self.base_angle = 0
        else:
            if self.rain:
                # Recovery
                self.rain = 0
                self.petal_state = 1
            # 2% chance of rain per tick
            if random.random() < 0.02:
                self.rain_event_timer = random.randint(5, 15)
                print(f"  [SIM] Rain event! Duration: {self.rain_event_timer} ticks")

    def send_telemetry(self, ldr_left, ldr_right, ldr_top, ldr_bottom):
        """POST telemetry data to master-pi."""
        # Compute derived metrics
        tracking_active = 1 if (not self.rain and self.petal_state == 1) else 0
        alignment_error = abs(ldr_left - ldr_right) + abs(ldr_top - ldr_bottom)
        light_intensity_avg = round((ldr_left + ldr_right + ldr_top + ldr_bottom) / 4.0, 2)

        # Tracking direction: 0=idle, 1=east, 2=west, 3=north, 4=south, 5=zenith
        if not tracking_active:
            tracking_direction = 0
        elif ldr_right > ldr_left:
            tracking_direction = 1   # east
        elif ldr_left > ldr_right:
            tracking_direction = 2   # west
        elif ldr_top > ldr_bottom:
            tracking_direction = 3   # north/up
        elif ldr_bottom > ldr_top:
            tracking_direction = 4   # south/down
        else:
            tracking_direction = 5   # zenith (aligned)

        # Motor states: 0=idle, 1=running, 2=stalled, 3=fault
        motor_base_state = 1 if tracking_active and abs(ldr_left - ldr_right) >= self.threshold else 0
        motor_tilt_state = 1 if tracking_active and abs(ldr_top - ldr_bottom) >= self.threshold else 0

        # Simulated motor temperature (rises when motors are active)
        motor_temp = 25.0 + random.uniform(0, 5)
        if motor_base_state == 1 or motor_tilt_state == 1:
            motor_temp += random.uniform(5, 15)
        if self.rain:
            motor_temp = 22.0 + random.uniform(0, 3)

        data = {
            # Original metrics
            'ldr_left': ldr_left,
            'ldr_right': ldr_right,
            'ldr_top': ldr_top,
            'ldr_bottom': ldr_bottom,
            'rain': self.rain,
            'petal_state': self.petal_state,
            'tilt_angle': round(self.tilt_angle, 1),
            'base_angle': round(self.base_angle, 1),
            'motor_state': 1 if not self.rain else 0,
            # New dashboard metrics
            'tracking_active': tracking_active,
            'tracking_direction': tracking_direction,
            'alignment_error': alignment_error,
            'motor_base_state': motor_base_state,
            'motor_tilt_state': motor_tilt_state,
            'motor_temperature': round(motor_temp, 1),
            'heliocore_service_health': 1,
            'light_intensity_avg': light_intensity_avg
        }

        try:
            r = requests.post(f'{self.master_url}/telemetry', json=data, timeout=2)
            return r.status_code == 200
        except:
            return False

    def print_status(self, sun_az, sun_el, ldr_l, ldr_r, ldr_t, ldr_b, sent):
        """Print live status to terminal."""
        time_pct = int(self.sim_time * 100)
        status = "RAIN" if self.rain else "TRACKING"
        tx = "OK" if sent else "FAIL"

        # Build progress bar for sun position
        bar_len = 30
        pos = int(self.sim_time * bar_len)
        bar = "=" * pos + "O" + "-" * (bar_len - pos - 1)

        sys.stdout.write(f"\r  Sun [{bar}] {time_pct:3d}%  "
                         f"Az:{sun_az:+7.1f} El:{sun_el:5.1f}  "
                         f"Panel B:{self.base_angle:+7.1f} T:{self.tilt_angle:5.1f}  "
                         f"LDR L:{ldr_l} R:{ldr_r} T:{ldr_t} B:{ldr_b}  "
                         f"[{status:8s}] TX:{tx}   ")
        sys.stdout.flush()

    def run(self, interval=1.0):
        """Main simulation loop."""
        print("\n" + "=" * 70)
        print("  HelioCore OS — Farm-Pi Simulator")
        print("  Sending telemetry to:", self.master_url)
        print("  Press Ctrl+C to stop")
        print("=" * 70 + "\n")

        self.running = True

        # SIGTERM only on Linux (for daemon mode)
        if hasattr(signal, 'SIGTERM') and sys.platform != 'win32':
            signal.signal(signal.SIGTERM, lambda s, f: setattr(self, 'running', False))

        cycle = 0
        try:
            while self.running:
                # Advance simulated time (loops sunrise→sunset→sunrise)
                self.sim_time += self.sim_speed
                if self.sim_time >= 1.0:
                    self.sim_time = 0.0
                    self.base_angle = -150.0
                    self.tilt_angle = 10.0
                    cycle += 1
                    print(f"\n  [SIM] === New day cycle #{cycle + 1} ===")

                # Get sun position
                sun_az, sun_el = self.get_sun_position()

                # Generate LDR readings
                ldr_l, ldr_r, ldr_t, ldr_b = self.get_ldr_readings(sun_az, sun_el)

                # Update rain simulation
                self.update_rain()

                # Update tracking
                self.update_tracking(ldr_l, ldr_r, ldr_t, ldr_b)

                # Send telemetry
                sent = self.send_telemetry(ldr_l, ldr_r, ldr_t, ldr_b)

                # Display
                self.print_status(sun_az, sun_el, ldr_l, ldr_r, ldr_t, ldr_b, sent)

                time.sleep(interval)
        except KeyboardInterrupt:
            pass

        print("\n\n  [SIM] Simulator stopped.\n")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='HelioCore Farm-Pi Simulator')
    parser.add_argument('--master', default='http://localhost:5000',
                        help='Master-Pi telemetry URL')
    parser.add_argument('--interval', type=float, default=1.0,
                        help='Seconds between telemetry updates')
    parser.add_argument('--speed', type=float, default=0.002,
                        help='Sun simulation speed (0.001=slow, 0.01=fast)')
    args = parser.parse_args()

    sim = FarmSimulator(master_url=args.master)
    sim.sim_speed = args.speed
    sim.run(interval=args.interval)
