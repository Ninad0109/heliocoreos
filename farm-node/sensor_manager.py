import RPi.GPIO as GPIO
import time

class SensorManager:
    def __init__(self, config):
        self.ldr_pins = config['ldr_pins']
        self.rain_pins = config['rain_pins']
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        for pin in self.ldr_pins + self.rain_pins:
            GPIO.setup(pin, GPIO.IN)
    
    def read_ldr(self, index):
        if 0 <= index < len(self.ldr_pins):
            return GPIO.input(self.ldr_pins[index])
        return 0
    
    def read_all_ldr(self):
        return [GPIO.input(pin) for pin in self.ldr_pins]
    
    def read_rain(self):
        return any(GPIO.input(pin) for pin in self.rain_pins)
    
    def get_directional_light(self):
        ldr = self.read_all_ldr()
        return {
            'left': ldr[0] + ldr[3],
            'right': ldr[2] + ldr[5],
            'top': ldr[1],
            'bottom': ldr[4]
        }
    
    def get_telemetry(self):
        ldr = self.read_all_ldr()
        return {
            'ldr_left': ldr[0] + ldr[3],
            'ldr_right': ldr[2] + ldr[5],
            'ldr_top': ldr[1],
            'ldr_bottom': ldr[4],
            'rain': int(self.read_rain())
        }
    
    def cleanup(self):
        GPIO.cleanup()

if __name__ == '__main__':
    import json
    with open('config.json') as f:
        config = json.load(f)
    
    sensor = SensorManager(config)
    
    try:
        while True:
            data = sensor.get_telemetry()
            print(f"LDR L:{data['ldr_left']} R:{data['ldr_right']} T:{data['ldr_top']} B:{data['ldr_bottom']} | Rain:{data['rain']}")
            time.sleep(1)
    except KeyboardInterrupt:
        sensor.cleanup()
        print("\nSensor test complete")
