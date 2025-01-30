import pigpio
import time

class BeamBreak:
    def __init__(self, pi, sensor_pin, debounce_delay=0.2):
        
        self.pi = pi
        self.sensor_pin = sensor_pin
        self.debounce_delay = debounce_delay
        self.sensor_state = 0
        self.last_state = 0
        self.last_debounce_time = 0

        self.pi.set_mode(self.sensor_pin, pigpio.INPUT)
        self.pi.set_pull_up_down(self.sensor_pin, pigpio.PUD_UP)

    def activate_beam_break(self):
        reading = self.pi.read(self.sensor_pin)

        if reading != self.last_state:
            self.last_debounce_time = time.time()

        if (time.time() - self.last_debounce_time) > self.debounce_delay:
            if reading != self.sensor_state:
                self.sensor_state = reading
                print(f"BeamBreak state changed to: {self.sensor_state}")

        self.last_state = reading

    def deactivate_beam_break(self):
        self.sensor_state = -1
        self.last_state = -1
        self.last_debounce_time = 0
        print("BeamBreak deactivated.")