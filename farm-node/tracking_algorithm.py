import time

class TrackingAlgorithm:
    def __init__(self, sensor_manager, motor_controller, config):
        self.sensor = sensor_manager
        self.motor = motor_controller
        self.threshold = 1
        self.step_size = 2
        self.update_interval = 2.0
        self.active = False
    
    def calculate_tracking_adjustment(self):
        light = self.sensor.get_directional_light()
        
        base_adjustment = 0
        tilt_adjustment = 0
        
        # Horizontal tracking
        h_diff = light['left'] - light['right']
        if abs(h_diff) >= self.threshold:
            if h_diff > 0:
                base_adjustment = -self.step_size  # Move left
            else:
                base_adjustment = self.step_size   # Move right
        
        # Vertical tracking
        v_diff = light['top'] - light['bottom']
        if abs(v_diff) >= self.threshold:
            if v_diff > 0:
                tilt_adjustment = self.step_size   # Tilt up
            else:
                tilt_adjustment = -self.step_size  # Tilt down
        
        return base_adjustment, tilt_adjustment
    
    def update(self):
        if not self.active:
            return False
        
        base_adj, tilt_adj = self.calculate_tracking_adjustment()
        
        if base_adj != 0:
            self.motor.move_base_relative(base_adj)
        
        if tilt_adj != 0:
            self.motor.move_tilt_relative(tilt_adj)
        
        return base_adj != 0 or tilt_adj != 0
    
    def start(self):
        self.active = True
        self.motor.open_petals()
    
    def stop(self):
        self.active = False
    
    def is_active(self):
        return self.active

if __name__ == '__main__':
    import json
    from sensor_manager import SensorManager
    from motor_controller import MotorController
    
    with open('config.json') as f:
        config = json.load(f)
    
    sensor = SensorManager(config)
    motor = MotorController(config)
    tracker = TrackingAlgorithm(sensor, motor, config)
    
    try:
        print("Starting sun tracking test...")
        tracker.start()
        
        for i in range(10):
            print(f"\nIteration {i+1}")
            light = sensor.get_directional_light()
            print(f"Light: L={light['left']} R={light['right']} T={light['top']} B={light['bottom']}")
            
            moved = tracker.update()
            state = motor.get_state()
            print(f"Position: Base={state['base_angle']}\u00b0 Tilt={state['tilt_angle']}\u00b0")
            print(f"Movement: {'YES' if moved else 'NO'}")
            
            time.sleep(2)
        
        tracker.stop()
        motor.safe_position()
        
    except KeyboardInterrupt:
        tracker.stop()
        motor.safe_position()
        sensor.cleanup()
        motor.cleanup()
        print("\nTracking test complete")
