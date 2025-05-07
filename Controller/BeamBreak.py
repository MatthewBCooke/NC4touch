import pigpio
import time
import threading

import logging
logger = logging.getLogger(f"session_logger.{__name__}")

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
        self.is_active = False
        self.read_interval = 0.05  # 50 ms
        self.read_timer = threading.Timer(self.read_interval, self._read_loop)

        self.pi.set_mode(self.pin, pigpio.INPUT)
        self.pi.set_pull_up_down(self.pin, pigpio.PUD_UP)
    
    def read(self):
        reading = self.pi.read(self.pin)

        if reading != self.last_state:
            self.last_debounce_time = time.time()

        if (time.time() - self.last_debounce_time) > self.debounce_delay:
            if reading != self.state:
                self.state = reading
                logger.debug(f"BeamBreak state changed to: {self.state}")

        self.last_state = reading
    
    def _read_loop(self):
        self.read_timer.cancel()

        reading = self.pi.read(self.pin)
        if reading != self.last_state:
            self.last_debounce_time = time.time()

        self.read_timer = threading.Timer(self.read_interval, self._read_loop)
        self.read_timer.start()

    def activate(self):
        self.is_active = True
        self.read_timer.cancel()
        self.read_timer = threading.Timer(self.read_interval, self._read_loop)
        self.read_timer.start()

    def deactivate(self):
        self.state = -1
        self.last_state = -1
        self.last_debounce_time = 0
        logger.debug("BeamBreak deactivated.")