import pigpio

class Buzzer:
    def __init__(self, pi, pin):
        self.pin = pin
        self.volume = 75
        self.pi = pi

        pi.set_mode(pin, pigpio.OUTPUT)
        pi.set_PWM_dutycycle(pin, 0)
        pi.set_PWM_range(pin, 100)
        pi.set_PWM_frequency(pin, 10000)
    
    def activate_buzzer(self):
        self.pi.set_PWM_dutycycle(self.pin, self.volume)
        
    def deactivate_buzzer(self):
        self.pi.set_PWM_dutycycle(self.pin, 0)