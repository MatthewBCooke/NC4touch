import pigpio
import logging
logger = logging.getLogger(f"session_logger.{__name__}")

class LED:
    """Class to control an LED using PWM on a Raspberry Pi."""
    def __init__(self, pi=pigpio.pi(), pin=21, rgb_pins = None, frequency=5000, range=255, brightness=140):
        """
        Initialize the LED with the given parameters.
        :param pi: pigpio.pi() instance
        :param pin: GPIO pin number for the LED
        :param rgb_pins: Tuple of GPIO pin numbers for RGB pins (r_pin, g_pin, b_pin)
        :param frequency: PWM frequency (default: 5000 Hz)
        :param range: PWM range (default: 255)
        :param brightness: Initial brightness (default: 140)
        """
        if not isinstance(pi, pigpio.pi):
            logger.error("pi must be an instance of pigpio.pi")
            raise ValueError("pi must be an instance of pigpio.pi")

        self.pi = pi
        self.pin = pin
        self.frequency = frequency
        self.range = range
        self.brightness = brightness
        self.color = (brightness, brightness, brightness)  # Default to white

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
        self.pi.set_mode(pin, pigpio.OUTPUT)
        self.pi.set_PWM_frequency(pin, self.frequency)
        self.pi.set_PWM_range(pin, self.range)
        self.pi.set_PWM_dutycycle(pin, 0)
    
    def __del__(self):
        """Clean up the LED by stopping the PWM."""
        self.deactivate()
    
    def set_color(self, r, g, b):
        """Set the color of the LED."""
        self.color = (r, g, b)
        logger.debug(f"LED color set to {self.color}")

    def activate(self):
        """Activate the LED with the current brightness or color."""
        if self.show_color:
            r, g, b = self.color
            self.pi.set_PWM_dutycycle(self.r_pin, r)
            self.pi.set_PWM_dutycycle(self.g_pin, g)
            self.pi.set_PWM_dutycycle(self.b_pin, b)
        else:
            self.pi.set_PWM_dutycycle(self.pin, self.brightness)
        logger.debug(f"LED activated")

    def deactivate(self):
        """Deactivate the LED."""
        if self.show_color:
            self.pi.set_PWM_dutycycle(self.r_pin, 0)
            self.pi.set_PWM_dutycycle(self.g_pin, 0)
            self.pi.set_PWM_dutycycle(self.b_pin, 0)
        else:
            self.pi.set_PWM_dutycycle(self.pin, 0)
        logger.debug(f"LED deactivated")
