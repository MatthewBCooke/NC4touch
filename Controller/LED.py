try:
    import pigpio
except ImportError:
    pigpio = None
import logging
logger = logging.getLogger(f"session_logger.{__name__}")

class LED:
    """Class to control an LED using PWM on a Raspberry Pi."""
    def __init__(self, pi=None, pin=21, rgb_pins = None, frequency=5000, range=255, brightness=140, color=(255, 255, 255)):
        if pi is None and pigpio is not None:
            pi = pigpio.pi()
        if pigpio is not None and not isinstance(pi, pigpio.pi):
            logger.error("pi must be an instance of pigpio.pi")
            raise ValueError("pi must be an instance of pigpio.pi")

        self.pi = pi
        self.pin = pin
        self.frequency = frequency
        self.range = range
        self.brightness = brightness
        self.color = color  # Default to white
        self.active = False # Default to inactive

        # Check if RGB pins are provided
        if rgb_pins is not None and len(rgb_pins) == 3:
            self.r_pin, self.g_pin, self.b_pin = rgb_pins
            self.show_color = True
        else:
            self.r_pin = None
            self.g_pin = None
            self.b_pin = None
            self.show_color = False
        
        if self.show_color:
            self.setup_pin(self.r_pin)
            self.setup_pin(self.g_pin)
            self.setup_pin(self.b_pin)
        else:
            self.setup_pin(self.pin)

    def setup_pin(self, pin):
        """Set up the pin for PWM output."""
        # If pigpio isn't available or wasn't initialized, skip hardware calls
        if self.pi is None:
            logger.warning(f"pigpio not available; skipping setup for pin {pin}")
            return

        self.pi.set_mode(pin, pigpio.OUTPUT)
        self.pi.set_PWM_frequency(pin, self.frequency)
        self.pi.set_PWM_range(pin, self.range)
        self.pi.set_PWM_dutycycle(pin, 0)
    
    def __del__(self):
        """Clean up the LED by stopping the PWM."""
        self.deactivate()
    
    def set_color(self, color):
        """Set the color of the LED."""
        self.color = color
        logger.debug(f"LED color set to {self.color}")

        if self.active:
            self.activate()

    def set_brightness(self, brightness):
        """Set the brightness of the LED."""
        self.brightness = brightness
        logger.debug(f"LED brightness set to {self.brightness}")

        if self.active:
            self.activate()

    def activate(self):
        """Activate the LED with the current brightness and/or color."""
        # If pigpio isn't available, simulate activation and log
        if self.pi is None:
            self.active = True
            logger.warning("pigpio not available; LED.activate() simulated")
            return

        if self.show_color:
            r, g, b = self.color
            self.pi.set_PWM_dutycycle(self.r_pin, r * self.brightness // 255)
            self.pi.set_PWM_dutycycle(self.g_pin, g * self.brightness // 255)
            self.pi.set_PWM_dutycycle(self.b_pin, b * self.brightness // 255)
        else:
            self.pi.set_PWM_dutycycle(self.pin, self.brightness)

        self.active = True
        logger.debug("LED activated")
    
    def deactivate(self):
        """Deactivate the LED."""
        # If pigpio isn't available, simulate deactivation and log
        if self.pi is None:
            self.active = False
            logger.warning("pigpio not available; LED.deactivate() simulated")
            return

        if self.show_color:
            self.pi.set_PWM_dutycycle(self.r_pin, 0)
            self.pi.set_PWM_dutycycle(self.g_pin, 0)
            self.pi.set_PWM_dutycycle(self.b_pin, 0)
        else:
            self.pi.set_PWM_dutycycle(self.pin, 0)

        self.active = False
        logger.debug(f"LED deactivated")
