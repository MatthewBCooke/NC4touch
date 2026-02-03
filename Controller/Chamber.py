# Chamber class for the Touchscreen chamber
#
# Refactored to use centralized hardware configuration
#
# Manu Madhav
# OpenClaw Subagent
# 2025-2026

try:
    import pigpio
except ImportError:
    pigpio = None
try:
    import serial
    import serial.tools.list_ports
except ImportError:
    serial = None

import time
import subprocess
import json
import os
from typing import List, Optional

from LED import LED
from Reward import Reward
from BeamBreak import BeamBreak
from Buzzer import Buzzer
from M0Device import M0Device
from M0DeviceI2C import M0DeviceI2C, discover_i2c_devices
from Camera import Camera
from Config import Config

# Import new hardware config system
from config import HardwareConfig, get_default_config

import logging
logger = logging.getLogger(f"session_logger.{__name__}")


class Chamber:
    """
    Chamber class for the Touchscreen chamber.
    
    Manages all hardware components including M0 touchscreens, LEDs, reward system,
    sensors, and camera. Supports both serial and I2C communication with M0 devices.
    
    Args:
        chamber_config: Legacy dict-based config (deprecated, use hw_config instead)
        chamber_config_file: Legacy YAML config file path
        hw_config: New HardwareConfig instance (recommended)
    
    Example:
        # Using new config system (recommended)
        from config import get_default_config
        hw_config = get_default_config()
        chamber = Chamber(hw_config=hw_config)
        
        # Using legacy config (backward compatible)
        chamber = Chamber(chamber_config={'use_i2c': True})
    """
    
    def __init__(
        self,
        chamber_config: Optional[dict] = None,
        chamber_config_file: str = '~/chamber_config.yaml',
        hw_config: Optional[HardwareConfig] = None
    ):
        logger.info("Initializing Chamber...")
        
        # Initialize hardware configuration
        if hw_config is not None:
            # Use new config system
            self.hw_config = hw_config
            # Also maintain legacy config for backward compatibility
            self.config = Config(config={}, config_file=chamber_config_file)
            # Merge any legacy overrides
            if chamber_config:
                self.hw_config.merge_with_legacy_config(chamber_config)
        else:
            # Use legacy config system
            if chamber_config is None:
                chamber_config = {}
            self.config = Config(config=chamber_config, config_file=chamber_config_file)
            
            # Set legacy defaults
            self._set_legacy_config_defaults()
            
            # Create new config from legacy
            self.hw_config = get_default_config()
            self.hw_config.merge_with_legacy_config(self.config.config)
        
        # Store code directory
        self.code_dir = os.path.dirname(os.path.abspath(__file__))
        self.hw_config.directories.code_dir = self.code_dir
        
        # Initialize pigpio connection
        self.pi = pigpio.pi() if pigpio is not None else None
        
        # Initialize M0 devices based on communication mode
        if self.hw_config.use_i2c:
            logger.info("Using I2C communication mode")
            self._initialize_i2c_m0s()
        else:
            logger.info("Using serial communication mode")
            self._initialize_serial_m0s()
        
        # Initialize peripherals
        self._initialize_peripherals()
    
    def _set_legacy_config_defaults(self) -> None:
        """Set default values for legacy config system."""
        self.config.ensure_param("chamber_name", "Chamber0")
        self.config.ensure_param("reward_LED_pin", 21)
        self.config.ensure_param("reward_pump_pin", 27)
        self.config.ensure_param("beambreak_pin", 4)
        self.config.ensure_param("punishment_LED_pin", 17)
        self.config.ensure_param("house_LED_pin", 20)
        self.config.ensure_param("buzzer_pin", 16)
        self.config.ensure_param("reset_pins", [25, 5, 6])
        self.config.ensure_param("camera_device", "/dev/video0")
        self.config.ensure_param("use_i2c", False)
        self.config.ensure_param("i2c_addresses", [0x00, 0x01, 0x02])
    
    def _initialize_serial_m0s(self) -> None:
        """Initialize M0 devices using serial communication."""
        cfg = self.hw_config.m0_serial
        pins = self.hw_config.gpio_pins
        
        # Create M0Device instances
        self.left_m0 = M0Device(
            pi=self.pi,
            id="M0_0",
            reset_pin=pins.m0_reset_pins[0],
            baudrate=cfg.baudrate,
            location="left"
        )
        self.middle_m0 = M0Device(
            pi=self.pi,
            id="M0_1",
            reset_pin=pins.m0_reset_pins[1],
            baudrate=cfg.baudrate,
            location="middle"
        )
        self.right_m0 = M0Device(
            pi=self.pi,
            id="M0_2",
            reset_pin=pins.m0_reset_pins[2],
            baudrate=cfg.baudrate,
            location="right"
        )
        
        self.m0s = [self.left_m0, self.middle_m0, self.right_m0]
        
        # Discover and assign serial ports
        self.arduino_cli_discover()
        
        if len(self.discovered_boards) >= len(self.m0s):
            for i, m0 in enumerate(self.m0s):
                m0.port = self.discovered_boards[i]
                logger.info(f"Set {m0.id} serial port to {m0.port}")
        else:
            logger.error(f"Not enough M0 boards discovered. "
                        f"Found {len(self.discovered_boards)}, need {len(self.m0s)}")
    
    def _initialize_i2c_m0s(self) -> None:
        """Initialize M0 devices using I2C communication."""
        cfg = self.hw_config.m0_i2c
        pins = self.hw_config.gpio_pins
        
        try:
            # Scan I2C bus for devices
            devices = discover_i2c_devices(
                bus_num=cfg.bus_number,
                address_range=range(0x00, 0x08)
            )
            
            if len(devices) < 3:
                logger.error(f"Only found {len(devices)} I2C devices, need 3 M0s")
                return
            
            # Create device map: device_id -> address
            device_map = {device_id: addr for addr, device_id in devices}
            
            # Initialize M0 devices based on their IDs
            self.m0s = []
            expected_ids = ["M0_0", "M0_1", "M0_2"]
            locations = ["left", "middle", "right"]
            
            for i, (expected_id, location) in enumerate(zip(expected_ids, locations)):
                if expected_id in device_map:
                    addr = device_map[expected_id]
                    m0 = M0DeviceI2C(
                        pi=self.pi,
                        id=expected_id,
                        address=addr,
                        reset_pin=pins.m0_reset_pins[i],
                        bus_num=cfg.bus_number,
                        location=location
                    )
                    self.m0s.append(m0)
                    logger.info(f"Mapped {expected_id} to I2C address {addr:#04x}")
                else:
                    logger.error(f"{expected_id} not found on I2C bus")
            
            # Assign to named attributes for backward compatibility
            if len(self.m0s) >= 3:
                self.left_m0 = self.m0s[0]
                self.middle_m0 = self.m0s[1]
                self.right_m0 = self.m0s[2]
            
            logger.info(f"I2C discovery complete: {len(self.m0s)} devices found")
            
        except Exception as e:
            logger.error(f"I2C discovery failed: {e}")
            raise
    
    def _initialize_peripherals(self) -> None:
        """Initialize all peripheral hardware components."""
        pins = self.hw_config.gpio_pins
        pwm = self.hw_config.pwm
        cam = self.hw_config.camera
        bb = self.hw_config.beambreak
        
        # LEDs
        self.reward_led = LED(
            pi=self.pi,
            pin=pins.reward_led_pin,
            brightness=pwm.reward_led_brightness,
            frequency=pwm.frequency,
            range=pwm.range
        )
        self.punishment_led = LED(
            pi=self.pi,
            pin=pins.punishment_led_pin,
            brightness=pwm.punishment_led_brightness,
            frequency=pwm.frequency,
            range=pwm.range
        )
        self.house_led = LED(
            pi=self.pi,
            pin=pins.house_led_pin,
            brightness=pwm.house_led_brightness,
            frequency=pwm.frequency,
            range=pwm.range
        )
        
        # Sensors and actuators
        self.beambreak = BeamBreak(
            pi=self.pi,
            pin=pins.beambreak_pin,
            beam_break_memory=bb.memory_duration
        )
        self.buzzer = Buzzer(pi=self.pi, pin=pins.buzzer_pin)
        self.reward = Reward(pi=self.pi, pin=pins.reward_pump_pin)
        
        # Camera
        self.camera = Camera(device=cam.device_path)
    
    def __del__(self):
        """Clean up the chamber by stopping pigpio and M0s."""
        logger.info("Cleaning up chamber...")
        if hasattr(self, 'pi') and self.pi is not None:
            try:
                self.pi.stop()
            except:
                pass
        
        if hasattr(self, 'm0s'):
            for m0 in self.m0s:
                try:
                    m0.stop()
                except:
                    pass
    
    def compile_sketch(self, sketch_path: Optional[str] = None) -> bool:
        """
        Compile the M0Touch sketch using arduino-cli.
        
        Args:
            sketch_path: Path to .ino sketch file. If None, uses default from config.
            
        Returns:
            bool: True if compilation successful
        """
        if sketch_path is None:
            sketch_path = self.hw_config.directories.get_m0_sketch_path(
                use_i2c=self.hw_config.use_i2c
            )
        
        logger.info(f"Compiling sketch: {sketch_path}")
        
        try:
            # Run arduino-cli compile
            compile_output = subprocess.check_output(
                f"~/bin/arduino-cli compile -b DFRobot:samd:mzero_bl {sketch_path}",
                shell=True,
                stderr=subprocess.STDOUT
            ).decode("utf-8")
            
            logger.info(f"Compile output: {compile_output}")
            
            if "error" in compile_output.lower():
                logger.error(f"Compilation errors detected")
                return False
            else:
                logger.info(f"Sketch compiled successfully")
                return True
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Compilation failed: {e.output.decode('utf-8')}")
            return False
        except Exception as e:
            logger.error(f"Error compiling sketch: {e}")
            return False
    
    def arduino_cli_discover(self) -> List[str]:
        """
        Use arduino-cli to discover connected M0 boards.
        
        Looks for boards with VID: 0x2341 and PID: 0x0244 (DFRobot M0).
        
        Returns:
            List of discovered port addresses
        """
        cfg = self.hw_config.m0_serial
        
        # Reset all M0 boards before discovery
        self.m0_reset()
        time.sleep(cfg.discovery_wait_time)
        
        logger.info("Discovering M0 boards using arduino-cli...")
        self.discovered_boards = []
        
        try:
            result = subprocess.run(
                ["~/bin/arduino-cli", "board", "list", "--format", "json"],
                capture_output=True,
                shell=True,
                text=True
            )
            boards = json.loads(result.stdout)
            
            for board in boards.get('detected_ports', []):
                props = board.get('port', {}).get('properties', {})
                if (props.get('pid') == cfg.product_id and
                    props.get('vid') == cfg.vendor_id):
                    port_addr = board['port']['address']
                    self.discovered_boards.append(port_addr)
                    logger.debug(f"Discovered M0 board on {port_addr}")
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse arduino-cli output: {e}")
        except Exception as e:
            logger.error(f"Error discovering boards with arduino-cli: {e}")
        
        return self.discovered_boards
    
    def i2c_discover(self) -> int:
        """
        Discover M0 boards via I2C (wrapper for backward compatibility).
        
        Returns:
            Number of devices discovered
        """
        self._initialize_i2c_m0s()
        return len(self.m0s) if hasattr(self, 'm0s') else 0
    
    def m0_discover(self) -> dict:
        """
        Search /dev/ttyACM*, /dev/ttyUSB* for boards that respond with "ID:M0_x"
        when sent "WHOAREYOU?" command.
        
        Returns:
            Dictionary mapping device IDs to port paths (e.g., {"M0_0": "/dev/ttyACM0"})
        """
        if serial is None:
            logger.error("pyserial not available")
            return {}
        
        logger.info("Discovering M0 boards via serial...")
        
        board_map = {}
        ports = serial.tools.list_ports.comports()
        
        for p in ports:
            # Check if it's an ACM or USB device
            if "ACM" in p.device or "USB" in p.device:
                try:
                    with serial.Serial(p.device, self.hw_config.m0_serial.baudrate, timeout=1) as ser:
                        time.sleep(0.3)
                        ser.write(b"WHOAREYOU?\n")
                        line = ser.readline().decode("utf-8", errors="ignore").strip()
                        if line.startswith("ID:"):
                            board_id = line.split(":", 1)[1]
                            board_map[board_id] = p.device
                            logger.debug(f"Discovered {board_id} on {p.device}")
                except Exception as e:
                    logger.error(f"Could not query {p.device}: {e}")
        
        return board_map
    
    # M0 control methods
    
    def m0_send_command(self, command: str) -> None:
        """Send a command to all M0 boards."""
        for m0 in self.m0s:
            m0.send_command(command)
    
    def m0_reset(self) -> None:
        """Reset all M0 boards via hardware reset pins."""
        logger.info("Resetting M0 boards...")
        for m0 in self.m0s:
            m0.reset()
    
    def m0_initialize(self) -> None:
        """Initialize all M0 devices."""
        for m0 in self.m0s:
            m0.initialize()
    
    def m0_sync_images(self) -> None:
        """Sync image folders to all M0s."""
        for m0 in self.m0s:
            m0.sync_image_folder()
    
    def m0_upload_sketches(self) -> None:
        """Compile and upload sketches to all M0s."""
        if self.compile_sketch():
            for m0 in self.m0s:
                m0.upload_sketch()
    
    def m0_clear(self) -> None:
        """Clear all M0 screens (show black)."""
        self.m0_send_command("BLACK")
    
    def m0_show_image(self) -> None:
        """Show loaded images on all M0 screens."""
        self.m0_send_command("SHOW")
    
    def default_state(self) -> None:
        """Reset chamber to default state (all outputs off)."""
        self.m0_send_command("BLACK")
        self.reward_led.deactivate()
        self.punishment_led.deactivate()
        self.buzzer.deactivate()
        self.reward.stop()


if __name__ == "__main__":
    logger.info("Chamber module test")
    
    # Test new config system
    from config import get_default_config
    hw_config = get_default_config()
    logger.info(f"Hardware config created: {hw_config.chamber_name}")
    logger.info("Chamber initialized.")
