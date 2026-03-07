import time
from enum import Enum

class ProtectionState(Enum):
    NORMAL = 1
    RAIN_DETECTED = 2
    PROTECTED = 3
    RECOVERY = 4

class RainProtection:
    def __init__(self, sensor_manager, motor_controller, tracking_algorithm):
        self.sensor = sensor_manager
        self.motor = motor_controller
        self.tracker = tracking_algorithm
        self.state = ProtectionState.NORMAL
        self.recovery_delay = 30  # seconds
        self.recovery_start = None
    
    def check_rain(self):
        return self.sensor.read_rain()
    
    def execute_protection_sequence(self):
        print("RAIN DETECTED - Executing protection sequence")
        
        # Stop tracking
        self.tracker.stop()
        
        # Close petals
        self.motor.close_petals()
        
        # Move to safe position
        self.motor.safe_position()
        
        self.state = ProtectionState.PROTECTED
        print("Protection sequence complete - System in safe mode")
    
    def update(self):
        rain_detected = self.check_rain()
        
        if self.state == ProtectionState.NORMAL:
            if rain_detected:
                self.state = ProtectionState.RAIN_DETECTED
                self.execute_protection_sequence()
        
        elif self.state == ProtectionState.PROTECTED:
            if not rain_detected:
                self.state = ProtectionState.RECOVERY
                self.recovery_start = time.time()
                print(f"Rain cleared - Starting {self.recovery_delay}s recovery delay")
        
        elif self.state == ProtectionState.RECOVERY:
            if rain_detected:
                # Rain detected again during recovery
                self.state = ProtectionState.PROTECTED
                self.recovery_start = None
                print("Rain detected again - Remaining in protected mode")
            elif time.time() - self.recovery_start >= self.recovery_delay:
                # Recovery complete
                self.state = ProtectionState.NORMAL
                self.tracker.start()
                print("Recovery complete - Resuming normal operation")
        
        return self.state
    
    def is_protected(self):
        return self.state in [ProtectionState.RAIN_DETECTED, ProtectionState.PROTECTED, ProtectionState.RECOVERY]
    
    def get_state_name(self):
        return self.state.name

if __name__ == '__main__':
    import json
    from sensor_manager import SensorManager
    from motor_controller import MotorController
    from tracking_algorithm import TrackingAlgorithm
    
    with open('config.json') as f:
        config = json.load(f)
    
    sensor = SensorManager(config)
    motor = MotorController(config)
    tracker = TrackingAlgorithm(sensor, motor, config)
    protection = RainProtection(sensor, motor, tracker)
    
    try:
        print("Starting rain protection test...")
        tracker.start()
        
        for i in range(60):
            state = protection.update()
            rain = sensor.read_rain()
            motor_state = motor.get_state()
            
            print(f"[{i}s] State: {state.name} | Rain: {rain} | Tracking: {tracker.is_active()} | Petals: {motor_state['petal_state']}")
            
            time.sleep(1)
    
    except KeyboardInterrupt:
        motor.safe_position()
        sensor.cleanup()
        motor.cleanup()
        print("\nRain protection test complete")
