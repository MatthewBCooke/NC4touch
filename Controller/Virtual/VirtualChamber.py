"""
Virtual Chamber - Complete virtualized touchscreen chamber for testing.
"""

import os
import time

from Virtual.VirtualM0Device import VirtualM0Device
from Virtual.VirtualBeamBreak import VirtualBeamBreak
from Virtual.VirtualBuzzer import VirtualBuzzer
from Virtual.VirtualLED import VirtualLED
from Virtual.VirtualReward import VirtualReward
from Config import Config

import logging
logger = logging.getLogger(f"session_logger.{__name__}")


class VirtualCamera:
    """Simple virtual camera placeholder."""
    def __init__(self, device="/dev/video0"):
        self.device = "VIRTUAL_CAMERA"
        logger.info(f"Virtual Camera initialized")

    def start_recording(self, filename):
        logger.info(f"Virtual Camera: recording to {filename}")

    def stop_recording(self):
        logger.info("Virtual Camera: recording stopped")


class VirtualChamber:
    """
    Virtual implementation of Chamber class for testing without physical hardware.
    Maintains the same API as the real Chamber class.
    """

    def __init__(self, chamber_config={}, chamber_config_file='~/chamber_config.yaml'):
        logger.info("="*60)
        logger.info("Initializing VIRTUAL Chamber")
        logger.info("="*60)

        self.config = Config(config=chamber_config, config_file=chamber_config_file)
        self.config.ensure_param("chamber_name", "VirtualChamber")
        self.config.ensure_param("name", "VirtualChamber")  # Alias for compatibility with Trainer
        self.config.ensure_param("reward_LED_pin", 21)
        self.config.ensure_param("reward_pump_pin", 27)
        self.config.ensure_param("beambreak_pin", 4)
        self.config.ensure_param("punishment_LED_pin", 17)
        self.config.ensure_param("house_LED_pin", 20)
        self.config.ensure_param("buzzer_pin", 16)
        self.config.ensure_param("reset_pins", [25, 5, 6])
        self.config.ensure_param("camera_device", "/dev/video0")
        
        self.code_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Image directory for stimulus BMPs (mimics M0 internal storage)
        # Default: <project_root>/data/images/
        default_image_dir = os.path.join(os.path.dirname(os.path.dirname(self.code_dir)), 'data', 'images')
        self.config.ensure_param("image_dir", default_image_dir)

        # No pigpio needed for virtual
        self.pi = None

        # Initialize virtual M0 devices
        self.left_m0 = VirtualM0Device(
            pi=self.pi,
            id="M0_0",
            reset_pin=self.config["reset_pins"][0],
            location="left",
            image_dir=self.config["image_dir"]
        )
        self.middle_m0 = VirtualM0Device(
            pi=self.pi,
            id="M0_1",
            reset_pin=self.config["reset_pins"][1],
            location="middle",
            image_dir=self.config["image_dir"]
        )
        self.right_m0 = VirtualM0Device(
            pi=self.pi,
            id="M0_2",
            reset_pin=self.config["reset_pins"][2],
            location="right",
            image_dir=self.config["image_dir"]
        )

        self.m0s = [self.left_m0, self.middle_m0, self.right_m0]

        # Initialize virtual peripherals
        self.reward_led = VirtualLED(
            pi=self.pi,
            pin=self.config["reward_LED_pin"],
            brightness=140
        )
        self.punishment_led = VirtualLED(
            pi=self.pi,
            pin=self.config["punishment_LED_pin"],
            brightness=255
        )
        self.house_led = VirtualLED(
            pi=self.pi,
            pin=self.config["house_LED_pin"],
            brightness=255
        )
        self.beambreak = VirtualBeamBreak(
            pi=self.pi,
            pin=self.config["beambreak_pin"]
        )
        self.buzzer = VirtualBuzzer(
            pi=self.pi,
            pin=self.config["buzzer_pin"]
        )
        self.reward = VirtualReward(
            pi=self.pi,
            pin=self.config["reward_pump_pin"]
        )
        self.camera = VirtualCamera(
            device=self.config["camera_device"]
        )

        # Virtual chamber state tracking
        self._state_history = []

        logger.info("Virtual Chamber initialized successfully")
        logger.info(f"  - 3 Virtual M0 Touchscreens (L/M/R)")
        logger.info(f"  - Virtual Reward Pump")
        logger.info(f"  - Virtual Beam Break Sensor")
        logger.info(f"  - 2 Virtual LEDs (reward/punishment)")
        logger.info(f"  - Virtual House LED")
        logger.info(f"  - Virtual Buzzer")
        logger.info("="*60)

    def __del__(self):
        """Cleanup virtual resources."""
        if hasattr(self, 'm0s'):
            for m0 in self.m0s:
                m0.stop()
        logger.info("Virtual Chamber cleaned up")

    def compile_sketch(self, sketch_path=None):
        """Virtual method - no compilation needed."""
        logger.info("Virtual Chamber: Sketch compilation skipped (virtual mode)")

    def arduino_cli_discover(self):
        """Virtual method - simulates board discovery."""
        logger.info("Virtual Chamber: Board discovery skipped (virtual mode)")
        self.discovered_boards = [f"VIRTUAL_PORT_{i}" for i in range(3)]

    def m0_discover(self):
        """Virtual method - simulates M0 discovery."""
        logger.info("Virtual Chamber: M0 discovery completed (virtual mode)")
        return {
            "M0_0": "VIRTUAL_PORT_0",
            "M0_1": "VIRTUAL_PORT_1",
            "M0_2": "VIRTUAL_PORT_2"
        }

    def m0_reset(self):
        """Virtual method - simulates M0 reset."""
        logger.info("Virtual Chamber: M0 boards reset (virtual mode)")

    def initialize_m0s(self):
        """Initialize all M0 devices."""
        for m0 in self.m0s:
            m0.initialize()
            time.sleep(0.1)
        logger.info("All virtual M0 devices initialized")

    def m0_send_command(self, command):
        """
        Sends a command to all M0 boards.
        """
        for m0 in self.m0s:
            m0.send_command(command)
        logger.debug(f"Virtual Chamber: sent command '{command}' to all M0s")

    def m0_show_image(self):
        """Virtual method - show images on all M0s."""
        self.m0_send_command("SHOW")

    def m0_clear(self):
        """Virtual method - clear images on all M0s."""
        self.m0_send_command("BLACK")

    def default_state(self):
        """
        Reset chamber to default state (all hardware off/clear).
        """
        self.m0_send_command("BLACK")
        self.reward_led.deactivate()
        self.punishment_led.deactivate()
        self.house_led.deactivate()
        self.buzzer.deactivate()
        self.reward.stop()
        logger.info("Virtual Chamber: reset to default state")

    # ===== Virtual-specific methods for simulation and testing =====

    def get_state(self):
        """Get complete virtual chamber state."""
        return {
            'timestamp': time.time(),
            'left_m0': {
                'is_touched': self.left_m0.is_touched(),
                'current_image': self.left_m0.get_current_image(),
                'touch_coords': self.left_m0.get_touch_coordinates()
            },
            'middle_m0': {
                'is_touched': self.middle_m0.is_touched(),
                'current_image': self.middle_m0.get_current_image(),
                'touch_coords': self.middle_m0.get_touch_coordinates()
            },
            'right_m0': {
                'is_touched': self.right_m0.is_touched(),
                'current_image': self.right_m0.get_current_image(),
                'touch_coords': self.right_m0.get_touch_coordinates()
            },
            'reward_led': self.reward_led.get_state(),
            'punishment_led': self.punishment_led.get_state(),
            'house_led': self.house_led.get_state(),
            'beambreak': {
                'state': self.beambreak.state,
                'last_break': self.beambreak.last_break_time
            },
            'buzzer': self.buzzer.get_state(),
            'reward': self.reward.get_state()
        }

    def log_state(self):
        """Log current state to history."""
        state = self.get_state()
        self._state_history.append(state)
        return state

    def get_state_history(self):
        """Get all logged states."""
        return self._state_history

    def clear_state_history(self):
        """Clear state history."""
        self._state_history = []
