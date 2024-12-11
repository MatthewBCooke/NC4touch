import RPi.GPIO as GPIO
import time

class BeamBreak:
    def __init__(self, pin):
        self.pin = pin
        self.sensor_state = 0
        self.last_state = 0
        self.last_debounce_time = 0
        self.debounce_delay = 0.25  
        self.reading = 0

        # Set up GPIO mode and pin with pull-up
        GPIO.setmode(GPIO.BCM)  
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def activate_beam_break(self):

        self.reading = GPIO.input(self.pin)

        if self.reading != self.last_state:
        
            self.last_debounce_time = time.time()

        # Update sensor state if debounce time has passed
        if (time.time() - self.last_debounce_time) > self.debounce_delay:
            if self.reading != self.sensor_state:
                self.sensor_state = self.reading

        # Save the last reading for comparison in the next cycle
        self.last_state = self.reading
        time.sleep(0.01)  

    def deactivate_beam_break(self):
        self.sensor_state = -1
        self.last_state = -1
        self.last_debounce_time = 0
        self.reading = -1

        print("Beam break sensor deactivated")

