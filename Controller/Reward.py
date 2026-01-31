try:
    import pigpio
except ImportError:
    pigpio = None
import time

import logging
logger = logging.getLogger(f"session_logger.{__name__}")

class Reward:
    def __init__(self, pi=None, pin=27):
        if pi is None and pigpio is not None:
            pi = pigpio.pi()
        if pigpio is not None and not isinstance(pi, pigpio.pi):
            logger.error("pi must be an instance of pigpio.pi")
            raise ValueError("pi must be an instance of pigpio.pi")

        self.pi = pi
        self.pin = pin

        """PWM set up"""
        self.pi.set_mode(self.pin, pigpio.OUTPUT)
        # Explicitly write LOW immediately to override boot-time pull-up
        self.pi.write(self.pin, 0)
        self.pi.set_PWM_range(self.pin, 255)
        self.pi.set_PWM_frequency(self.pin, 5000)
        self.pi.set_PWM_dutycycle(self.pin, 0)
    
    def __del__(self):
        self.stop()

    def dispense(self):
        # Turn on the pump
        logger.debug("Dispensing reward")
        self.pi.set_PWM_dutycycle(self.pin, 255)

    def stop(self):
        logger.debug("Stopping reward")
        self.pi.set_PWM_dutycycle(self.pin, 0)