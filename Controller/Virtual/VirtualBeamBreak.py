"""
Virtual BeamBreak sensor for reward hopper simulation.
"""

import time
import threading

import logging
logger = logging.getLogger(f"session_logger.{__name__}")


class VirtualBeamBreak:
    """
    Virtual implementation of BeamBreak sensor.
    Maintains the same API as the real BeamBreak class.
    """

    def __init__(self, pi=None, pin=4, beam_break_memory=0.2):
        self.pin = pin
        self.last_break_time = time.time()
        self.beam_break_memory = beam_break_memory
        self.read_interval = 0.05
        self.read_timer = None
        self.state = 1  # 1 = beam not broken, 0 = beam broken
        self._is_active = False

        logger.info(f"Virtual BeamBreak initialized on pin {self.pin}")

    def _read_loop(self):
        """Internal method to update beam break state."""
        if not self._is_active:
            return

        current_time = time.time()

        # Check if memory time has expired
        if current_time - self.last_break_time > self.beam_break_memory:
            if self.state == 0:
                self.state = 1
                logger.debug("Virtual beam restored (memory expired)")

        # Schedule next read
        self.read_timer = threading.Timer(self.read_interval, self._read_loop)
        self.read_timer.start()

    def activate(self):
        """Activate the virtual beam break sensor."""
        self._is_active = True
        if self.read_timer:
            self.read_timer.cancel()
        self.read_timer = threading.Timer(self.read_interval, self._read_loop)
        self.read_timer.start()
        logger.debug("Virtual BeamBreak activated")

    def deactivate(self):
        """Deactivate the virtual beam break sensor."""
        self._is_active = False
        if self.read_timer:
            self.read_timer.cancel()
        logger.debug("Virtual BeamBreak deactivated")

    # ===== Virtual-specific methods for simulation =====

    def simulate_break(self, duration=None):
        """
        Simulate the beam being broken.
        
        Args:
            duration: If provided, automatically restore beam after this many seconds.
                     If None, beam stays broken until manually restored.
        """
        self.last_break_time = time.time()
        self.state = 0
        logger.info("Virtual beam broken")

        if duration is not None:
            def restore_beam():
                time.sleep(duration)
                # Only restore if memory has expired
                if time.time() - self.last_break_time > self.beam_break_memory:
                    self.state = 1
                    logger.info("Virtual beam automatically restored")

            threading.Thread(target=restore_beam, daemon=True).start()

    def simulate_restore(self):
        """Manually restore the beam (simulate animal leaving)."""
        # Set last_break_time far enough in the past that memory expires
        self.last_break_time = time.time() - (self.beam_break_memory + 0.1)
        self.state = 1
        logger.info("Virtual beam manually restored")

    def get_state(self):
        """Get current beam state (1=not broken, 0=broken)."""
        return self.state
