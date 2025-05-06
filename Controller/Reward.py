import pigpio
import time

import logging
logger = logging.getLogger(f"session_logger.{__name__}")

class Reward:
    def __init__(self, pi=pigpio.pi(), pin=27):
        if not isinstance(pi, pigpio.pi):
            logger.error("pi must be an instance of pigpio.pi")
            raise ValueError("pi must be an instance of pigpio.pi")

        self.pi = pi
        self.pin = pin
        self.setup_reward()

        """PWM set up"""
        self.pi.set_mode(self.pin, pigpio.OUTPUT)
        self.pi.set_PWM_dutycycle(self.pin, 0)
        self.pi.set_PWM_range(self.pin, 255)
        self.pi.set_PWM_frequency(self.pin, 5000)
    
    def __del__(self):
        self.stop()

    def dispense(self):
        """
        Turn on the pump (max duty cycle).
        If duration_s is given, the main code is responsible for timing and stopping the pump.
        """
        logger.debug("Dispensing reward")
        self.pi.set_PWM_dutycycle(self.pin, 255)

    def stop(self):
        logger.debug("Stopping reward")
        self.pi.set_PWM_dutycycle(self.pin, 0)