import pigpio

class LED:
    def __init__(self, pi, pin, brightness, freq=5000):
        self.pi = pi
        self.pin = pin
        self.brightness = brightness  

        self.pi.set_mode(pin, pigpio.OUTPUT)
        self.pi.set_PWM_frequency(pin, freq)
        self.pi.set_PWM_range(pin, 100)
        self.deactivate()

    def activate(self):
        self.pi.set_PWM_dutycycle(self.pin, self.brightness)

    def deactivate(self):
        self.pi.set_PWM_dutycycle(self.pin, 0)
