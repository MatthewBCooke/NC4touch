"""
Virtual Reward pump for food delivery simulation.
"""

import time
import threading

import logging
logger = logging.getLogger(f"session_logger.{__name__}")


class VirtualReward:
    """
    Virtual implementation of Reward pump.
    Maintains the same API as the real Reward class.
    """

    def __init__(self, pi=None, pin=27):
        self.pin = pin

        # Virtual state
        self._is_dispensing = False
        self._total_dispensed = 0  # Track total rewards dispensed
        self._dispense_start_time = None

        logger.info(f"Virtual Reward pump initialized on pin {self.pin}")

    def __del__(self):
        self.stop()

    def dispense(self):
        """Turn on the pump (start dispensing)."""
        self._is_dispensing = True
        self._dispense_start_time = time.time()
        logger.info("Virtual Reward pump DISPENSING")

    def stop(self):
        """Stop the pump."""
        if self._is_dispensing:
            duration = time.time() - self._dispense_start_time if self._dispense_start_time else 0
            self._total_dispensed += 1
            logger.info(f"Virtual Reward pump STOPPED (dispensed for {duration:.2f}s)")
        self._is_dispensing = False
        self._dispense_start_time = None

    # ===== Virtual-specific methods =====

    def get_state(self):
        """Get current pump state."""
        current_duration = 0
        if self._is_dispensing and self._dispense_start_time:
            current_duration = time.time() - self._dispense_start_time

        return {
            'is_dispensing': self._is_dispensing,
            'total_dispensed': self._total_dispensed,
            'current_duration': current_duration,
            'pin': self.pin
        }

    def reset_counter(self):
        """Reset the total dispensed counter."""
        self._total_dispensed = 0
        logger.debug("Virtual Reward counter reset")
