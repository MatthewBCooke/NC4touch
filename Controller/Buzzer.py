import pigpio

class Buzzer:
    def __init__(self, pi, pin, volume=75, frequency=10000):
        self.pi = pi
        self.pin = pin
        self.volume = volume
        self.frequency = frequency

        self.pi.set_mode(self.pin, pigpio.OUTPUT)
        self.pi.set_PWM_dutycycle(self.pin, 0)  
        self.pi.set_PWM_range(self.pin, 100) 
        self.pi.set_PWM_frequency(self.pin, self.frequency)
        print(f"Buzzer initialized on GPIO {self.pin} with volume {self.volume}% and frequency {self.frequency}Hz.")

    def activate_buzzer(self):
        self.pi.set_PWM_dutycycle(self.pin, self.volume)
        print("Buzzer activated.")

    def deactivate_buzzer(self):
        self.pi.set_PWM_dutycycle(self.pin, 0)
        print("Buzzer deactivated.")