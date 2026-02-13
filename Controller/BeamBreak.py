try:
    import pigpio
except ImportError:
    pigpio = None
import time
import threading

import logging
logger = logging.getLogger(f"session_logger.{__name__}")

class BeamBreak:
    def __init__(self, pi=None, pin=4, beam_break_memory=0.2):
        if pi is None and pigpio is not None:
            pi = pigpio.pi()
        if pigpio is not None and not isinstance(pi, pigpio.pi):
            logger.error("pi must be an instance of pigpio.pi")
            raise ValueError("pi must be an instance of pigpio.pi")

        self.pi = pi
        self.pin = pin

        self.last_break_time = time.time()
        self.beam_break_memory = beam_break_memory  # 200 ms
        self.read_interval = 0.05  # 50 ms
        self.read_timer = threading.Timer(self.read_interval, self._read_loop)
        self.state = 1  # 1 = beam not broken, 0 = beam broken

        self.pi.set_mode(self.pin, pigpio.INPUT)
        self.pi.set_pull_up_down(self.pin, pigpio.PUD_UP)
    
    def _read_loop(self):
        """Internal method to read the beam break state."""
        self.read_timer.cancel()
        current_time = time.time()

        reading = self.pi.read(self.pin)
        if reading == 0: # Beam is broken
            self.last_break_time = current_time
            self.state = 0
        elif current_time - self.last_break_time > self.beam_break_memory:
            self.state = 1

        self.read_timer = threading.Timer(self.read_interval, self._read_loop)
        self.read_timer.start()

    def __del__(self):
        """Clean up timer thread."""
        try:
            self.deactivate()
        except Exception:
            pass

    def activate(self):
        self.read_timer.cancel()
        self.read_timer = threading.Timer(self.read_interval, self._read_loop)
        self.read_timer.start()
        logger.debug("BeamBreak activated.")

    def deactivate(self):
        self.read_timer.cancel()
        logger.debug("BeamBreak deactivated.")