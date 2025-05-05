import pigpio
import time

import logging
session_logger = logging.getLogger('session_logger')
logger = session_logger.getChild(__name__)
logger.setLevel(logging.DEBUG)

class BeamBreak:
    def __init__(self, pi=None, pin=4, debounce_delay=0.2):
        if pi is None:
            pi = pigpio.pi()
        if not isinstance(pi, pigpio.pi):
            logger.error("pi must be an instance of pigpio.pi")
            raise ValueError("pi must be an instance of pigpio.pi")

        self.pi = pi
        self.pin = pin
        self.debounce_delay = debounce_delay
        self.state = 0
        self.last_state = 0
        self.last_debounce_time = 0

        self.pi.set_mode(self.pin, pigpio.INPUT)
        self.pi.set_pull_up_down(self.pin, pigpio.PUD_UP)

    def activate(self):
        reading = self.pi.read(self.pin)

        if reading != self.last_state:
            self.last_debounce_time = time.time()

        if (time.time() - self.last_debounce_time) > self.debounce_delay:
            if reading != self.sensor_state:
                self.sensor_state = reading
                logger.debug(f"BeamBreak state changed to: {self.sensor_state}")

        self.last_state = reading

    def deactivate(self):
        self.sensor_state = -1
        self.last_state = -1
        self.last_debounce_time = 0
        logger.debug("BeamBreak deactivated.")