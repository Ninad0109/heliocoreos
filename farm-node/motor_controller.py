import RPi.GPIO as GPIO
import time

class MotorController:
    def __init__(self, config):
        self.config = config
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Motor 1: Petal actuator
        self.m1_step = config['motor1_step']
        self.m1_dir = config['motor1_dir']
        self.petal_state = 0  # 0=CLOSED, 1=OPEN
        
        # Motor 2: Tilt axis
        self.m2_step = config['motor2_step']
        self.m2_dir = config['motor2_dir']
        self.tilt_angle = 0
        
        # Motor 3: Base rotation
        self.m3_step = config['motor3_step']
        self.m3_dir = config['motor3_dir']
        self.base_angle = 0
        
        # Setup GPIO
        for pin in [self.m1_step, self.m1_dir, self.m2_step, self.m2_dir, self.m3_step, self.m3_dir]:
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.LOW)
        
        self.steps_per_rev = 200
        self.microsteps = 16
        self.step_delay = 0.001
    
    def step_motor(self, step_pin, dir_pin, steps, direction):
        GPIO.output(dir_pin, GPIO.HIGH if direction > 0 else GPIO.LOW)
        time.sleep(0.001)
        
        for _ in range(abs(steps)):
            GPIO.output(step_pin, GPIO.HIGH)
            time.sleep(self.step_delay)
            GPIO.output(step_pin, GPIO.LOW)
            time.sleep(self.step_delay)
    
    def set_petal_state(self, state):
        if state != self.petal_state:
            steps = 400 if state else -400
            self.step_motor(self.m1_step, self.m1_dir, abs(steps), 1 if state else -1)
            self.petal_state = state
    
    def set_tilt_angle(self, angle):
        angle = max(self.config['tilt_min_angle'], min(angle, self.config['tilt_max_angle']))
        delta = angle - self.tilt_angle
        steps = int((delta / 360.0) * self.steps_per_rev * self.microsteps)
        
        if steps != 0:
            self.step_motor(self.m2_step, self.m2_dir, abs(steps), 1 if steps > 0 else -1)
            self.tilt_angle = angle
    
    def set_base_angle(self, angle):
        angle = max(self.config['base_min_angle'], min(angle, self.config['base_max_angle']))
        delta = angle - self.base_angle
        steps = int((delta / 360.0) * self.steps_per_rev * self.microsteps)
        
        if steps != 0:
            self.step_motor(self.m3_step, self.m3_dir, abs(steps), 1 if steps > 0 else -1)
            self.base_angle = angle
    
    def move_base_relative(self, delta_angle):
        new_angle = self.base_angle + delta_angle
        self.set_base_angle(new_angle)
    
    def move_tilt_relative(self, delta_angle):
        new_angle = self.tilt_angle + delta_angle
        self.set_tilt_angle(new_angle)
    
    def open_petals(self):
        self.set_petal_state(1)
    
    def close_petals(self):
        self.set_petal_state(0)
    
    def get_state(self):
        return {
            'petal_state': self.petal_state,
            'tilt_angle': self.tilt_angle,
            'base_angle': self.base_angle
        }
    
    def safe_position(self):
        self.close_petals()
        self.set_tilt_angle(0)
        self.set_base_angle(0)
    
    def cleanup(self):
        GPIO.cleanup()

if __name__ == '__main__':
    import json
    with open('config.json') as f:
        config = json.load(f)
    
    motor = MotorController(config)
    
    try:
        print("Testing motors...")
        print("Opening petals...")
        motor.open_petals()
        time.sleep(1)
        
        print("Setting tilt to 45°...")
        motor.set_tilt_angle(45)
        time.sleep(1)
        
        print("Rotating base to 30°...")
        motor.set_base_angle(30)
        time.sleep(1)
        
        print("Returning to safe position...")
        motor.safe_position()
        
        print(f"Final state: {motor.get_state()}")
    except KeyboardInterrupt:
        motor.safe_position()
        motor.cleanup()
        print("\nMotor test complete")
