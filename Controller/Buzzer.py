import pigpio
import logging
session_logger = logging.getLogger('session_logger')
logger = session_logger.getChild(__name__)
logger.setLevel(logging.DEBUG)

class Buzzer:
    def __init__(self, pi=pigpio.pi(), pin=16, volume=60, frequency=6000):
        if not isinstance(pi, pigpio.pi):
            logger.error("pi must be an instance of pigpio.pi")
            raise ValueError("pi must be an instance of pigpio.pi")

        self.pi = pi
        self.pin = pin
        self.volume = volume
        self.frequency = frequency

        self.pi.set_mode(self.pin, pigpio.OUTPUT)
        self.pi.set_PWM_dutycycle(self.pin, 0)  
        self.pi.set_PWM_range(self.pin, 100) 
        self.pi.set_PWM_frequency(self.pin, self.frequency)

    def activate(self):
        self.pi.set_PWM_dutycycle(self.pin, self.volume)
        logger.debug(f"Buzzer activated")

    def deactivate(self):
        self.pi.set_PWM_dutycycle(self.pin, 0)
        logger.debug(f"Buzzer deactivated")