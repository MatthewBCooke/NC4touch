import pigpio

class LED:
    def __init__(self, pi, pin, frequency=5000, range=255, brightness=255):
        self.pi = pi
        self.pin = pin
        self.frequency = frequency
        self.range = range
        self.brightness = brightness

        self.pi.set_mode(self.pin, pigpio.OUTPUT)
        self.pi.set_PWM_frequency(self.pin, self.frequency)
        self.pi.set_PWM_range(self.pin, self.range)
        self.pi.set_PWM_dutycycle(self.pin, 0)  

    def activate(self):
        self.pi.set_PWM_dutycycle(self.pin, self.brightness)

    def deactivate(self):
        self.pi.set_PWM_dutycycle(self.pin, 0)
