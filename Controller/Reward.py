import pigpio
import time

import logging
session_logger = logging.getLogger('session_logger')
logger = session_logger.getChild(__name__)
logger.setLevel(logging.DEBUG)

class Reward:
    def __init__(self, pi=pigpio.pi(), pin=27):
        if not isinstance(pi, pigpio.pi):
            logger.error("pi must be an instance of pigpio.pi")
            raise ValueError("pi must be an instance of pigpio.pi")

        self.pi = pi
        self.pin = pin
        self.is_priming = False
        self.reward_duration_ms = 1500  
        self.setup_reward()

    def setup_reward(self):
        """PWM set up"""
        self.pi.set_mode(self.pin, pigpio.OUTPUT)
        self.pi.set_PWM_dutycycle(self.pin, 0)
        self.pi.set_PWM_range(self.pin, 255)
        self.pi.set_PWM_frequency(self.pin, 5000)

    def dispense(self, duration_s=None):
        """
        Turn on the pump (max duty cycle).
        If duration_s is given, the main code is responsible for timing and stopping the pump.
        """
        logger.debug(f"Dispensing reward for {duration_s} seconds" if duration_s else "Dispensing reward indefinitely")
        self.pi.set_PWM_dutycycle(self.pin, 255)

    def stop(self):
        self.pi.set_PWM_dutycycle(self.pin, 0)
        logger.debug("Stopping reward dispensing")

    def prime_feeding_tube(self):
        self.is_priming = True
        start_time = time.time()
        logger.debug("Priming started")
        try:
            while self.is_priming and (time.time() - start_time) < 20:  # ~20 seconds max
                self.pi.set_PWM_dutycycle(self.pin, 255)
                time.sleep(0.1)
            self.pi.set_PWM_dutycycle(self.pin, 0)
            if self.is_priming:
                logger.debug("Priming finished")
        except Exception as e:
            self.stop_priming()
            logger.error(f"Error during priming: {e}")

    def stop_priming(self):
        self.pi.set_PWM_dutycycle(self.pin, 0)
        self.is_priming = False
        logger.debug("Priming stopped")

    def cleanup(self):
        self.stop()  
        self.pi.set_PWM_dutycycle(self.pin, 0)
