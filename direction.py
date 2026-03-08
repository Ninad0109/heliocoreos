import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)

PETAL_DIR = 18
PETAL_STEP = 27

GPIO.setup(PETAL_DIR, GPIO.OUT)
GPIO.setup(PETAL_STEP, GPIO.OUT)

# anticlockwise direction
GPIO.output(PETAL_DIR, 0)

STEPS_FOR_300_DEG = 170   # adjust if microstepping

print("Rotating petals 300 degrees anticlockwise...")

for i in range(STEPS_FOR_300_DEG):
    GPIO.output(PETAL_STEP, 1)
    time.sleep(0.001)
    GPIO.output(PETAL_STEP, 0)
    time.sleep(0.001)

GPIO.cleanup()

print("Rotation complete")
