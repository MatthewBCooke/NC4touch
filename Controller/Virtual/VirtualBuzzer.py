"""
Virtual Buzzer for audio feedback simulation.
"""

import logging
logger = logging.getLogger(f"session_logger.{__name__}")


class VirtualBuzzer:
    """
    Virtual implementation of Buzzer.
    Maintains the same API as the real Buzzer class.
    """

    def __init__(self, pi=None, pin=16, volume=60, frequency=6000):
        self.pin = pin
        self.volume = volume
        self.frequency = frequency

        # Virtual state
        self._is_active = False

        logger.info(f"Virtual Buzzer initialized on pin {self.pin} "
                   f"(frequency={self.frequency}Hz, volume={self.volume})")

    def activate(self):
        """Activate the buzzer."""
        self._is_active = True
        logger.info(f"Virtual Buzzer ACTIVATED (frequency={self.frequency}Hz, volume={self.volume})")

    def deactivate(self):
        """Deactivate the buzzer."""
        self._is_active = False
        logger.info(f"Virtual Buzzer DEACTIVATED")

    def set_frequency(self, frequency):
        """Set buzzer frequency."""
        self.frequency = frequency
        logger.debug(f"Virtual Buzzer frequency set to {frequency}Hz")

    def set_volume(self, volume):
        """Set buzzer volume (0-100)."""
        self.volume = volume
        logger.debug(f"Virtual Buzzer volume set to {volume}")

    # ===== Virtual-specific methods =====

    def get_state(self):
        """Get current buzzer state."""
        return {
            'is_active': self._is_active,
            'frequency': self.frequency,
            'volume': self.volume,
            'pin': self.pin
        }
