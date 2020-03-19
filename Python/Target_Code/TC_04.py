import RPi.GPIO as GPIO
import time

DEBUG = False

GREEN_LED_PIN = 11
RED_LED_PIN = 12

# Used for pin setups
# Array of tuples (pin_number, GPIO.OUT or IN)
# There is a third parameter, but the meaning depends on the pinmode (Input or Output)
output_pins = [
    (RED_LED_PIN, GPIO.OUT),
    (GREEN_LED_PIN, GPIO.OUT)
]

def init():
    if DEBUG is True:
        # The hello world for GPIOs
        print(GPIO.RPI_INFO)

    # Sets the pin numbering mode
    # https://raspberrypi.stackexchange.com/questions/12966/what-is-the-difference-between-board-and-bcm-for-gpio-pin-numbering
    # BOARD is more consistent physically

    GPIO.setmode(GPIO.BOARD) # for physical pin numbering 
    # GPIO.setmode(GPIO.BCM) # for Broadcom pin numbering 

    # Sets pin mode based on the array
    for pin_setup in output_pins:
        GPIO.setup(pin_setup[0], pin_setup[1])


try:
    init()
    print('Blink Green LED with a period of 2s')
    GPIO.output(RED_LED_PIN, GPIO.HIGH)
    while True:
        # Change values here
        GPIO.output(GREEN_LED_PIN, GPIO.HIGH)
        time.sleep(1)
        GPIO.output(GREEN_LED_PIN, GPIO.LOW)
        time.sleep(1)

finally:
    # Cleans up settings after finished running
    GPIO.cleanup()
