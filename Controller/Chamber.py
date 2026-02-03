# Chamber class for the Touchscreen chamber
#
# Manu Madhav
# 2025

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

from LED import LED
from Reward import Reward
from BeamBreak import BeamBreak
from Buzzer import Buzzer
from M0Device import M0Device
from M0DeviceI2C import M0DeviceI2C, discover_i2c_devices
from Camera import Camera
from Config import Config

import logging
logger = logging.getLogger(f"session_logger.{__name__}")

#TODO: Add pigpiod to startup script

class Chamber:
  def __init__(self, chamber_config = {}, chamber_config_file = '~/chamber_config.yaml'):
    """
    Chamber class for the Touchscreen chamber.
    """
    logger.info("Initializing Chamber...")
    self.config = Config(config = chamber_config, config_file = chamber_config_file)
    self.config.ensure_param("chamber_name", "Chamber0")
    self.config.ensure_param("reward_LED_pin", 21)
    self.config.ensure_param("reward_pump_pin", 27)
    self.config.ensure_param("beambreak_pin", 4)
    self.config.ensure_param("punishment_LED_pin", 17)
    self.config.ensure_param("house_LED_pin", 20)
    self.config.ensure_param("buzzer_pin", 16)
    self.config.ensure_param("reset_pins", [25, 5, 6])
    self.config.ensure_param("camera_device", "/dev/video0")
    self.config.ensure_param("use_i2c", False)  # Use I2C instead of serial
    self.config.ensure_param("i2c_addresses", [0x00, 0x01, 0x02])  # I2C addresses for M0s

    self.code_dir = os.path.dirname(os.path.abspath(__file__))

    self.pi = pigpio.pi() if pigpio is not None else None

    # Initialize M0s based on communication mode
    if self.config["use_i2c"]:
        logger.info("Using I2C communication mode")
        self.i2c_discover()
    else:
        logger.info("Using serial communication mode")
        # Initialize M0s with serial
        self.left_m0 = M0Device(pi = self.pi, id = "M0_0", reset_pin = self.config["reset_pins"][0])
        self.middle_m0 = M0Device(pi = self.pi, id = "M0_1", reset_pin = self.config["reset_pins"][1])
        self.right_m0 = M0Device(pi = self.pi, id = "M0_2", reset_pin = self.config["reset_pins"][2])

        self.m0s = [self.left_m0, self.middle_m0, self.right_m0]
        self.arduino_cli_discover()

        if len(self.discovered_boards) >= len(self.m0s):
            for i, m0 in enumerate(self.m0s):
                m0.port = self.discovered_boards[i]
                logger.info(f"Set {m0.id} serial port to {m0.port}")
        else:
            logger.error("Not enough M0 boards discovered. Please check the connections.")

    self.reward_led = LED(pi=self.pi, pin=self.config["reward_LED_pin"], brightness = 140)
    self.punishment_led = LED(pi=self.pi, pin=self.config["punishment_LED_pin"], brightness = 255)
    self.house_led = LED(pi=self.pi, pin=self.config["house_LED_pin"], brightness = 100) 
    self.beambreak = BeamBreak(pi=self.pi, pin=self.config["beambreak_pin"])
    self.buzzer = Buzzer(pi=self.pi, pin=self.config["buzzer_pin"])
    self.reward = Reward(pi=self.pi, pin=self.config["reward_pump_pin"])
    self.camera = Camera(device=self.config["camera_device"])

  def __del__(self):
    """Clean up the chamber by stopping pigpio and M0s."""
    logger.info("Cleaning up chamber...")
    self.pi.stop()
    [m0.stop() for m0 in self.m0s]

  def compile_sketch(self, sketch_path=None):
      """
      Compiles the M0Touch sketch using arduino-cli.
      """
      if sketch_path is None:
          sketch_path = os.path.join(self.code_dir, "../M0Touch/M0Touch.ino")

      logger.info(f"Compiling sketch.")

      try:
          # Run arduino-cli compile
          compile = subprocess.check_output(f"~/bin/arduino-cli compile -b DFRobot:samd:mzero_bl {sketch_path}", shell=True).decode("utf-8")
          logger.info(f"Compile output: {compile}")
          
          if "error" in compile.lower():
              logger.error(f"Error compiling sketch: {compile}")
          else:
              logger.info(f"Sketch compiled successfully.")

      except Exception as e:
          logger.error(f"Error compiling sketch: {e}")

    
  def arduino_cli_discover(self):
    """
    Uses arduino-cli to discover connected boards.
    Looks for boards with VID: 0x2341 and PID: 0x0244 (DFRobot M0)
    """
    # Reset all the M0 boards in order before discovery
    self.m0_reset()
    time.sleep(3)

    logger.info("Discovering M0 boards using arduino-cli...")
    self.discovered_boards = []

    try:
        result = subprocess.run([f"~/bin/arduino-cli board list --format json"], capture_output=True, shell=True)
        boards = json.loads(result.stdout)

        for board in boards['detected_ports']:
            props = board['port']['properties']
            if 'pid' in props and 'vid' in props and props['pid'] == '0x0244' and props['vid'] == '0x2341':
                self.discovered_boards.append(board['port']['address'])
                logger.debug(f"Discovered M0 board on {board['port']['address']}")

    except Exception as e:
        logger.error(f"Error discovering boards with arduino-cli: {e}")

  
  
  def i2c_discover(self):
    """
    Discover M0 boards via I2C and create M0DeviceI2C instances.
    Queries each I2C address (0x00-0x07) for device identity and maps to M0Device objects.
    """
    logger.info("Discovering M0 boards via I2C...")
    
    try:
        # Scan I2C bus for devices
        devices = discover_i2c_devices(bus_num=1, address_range=range(0x00, 0x08))
        
        if len(devices) < 3:
            logger.error(f"Only found {len(devices)} I2C devices, need 3 M0s")
            return
        
        # Create device map: device_id -> (address, device_id)
        device_map = {device_id: addr for addr, device_id in devices}
        
        # Initialize M0 devices based on their IDs
        self.m0s = []
        expected_ids = ["M0_0", "M0_1", "M0_2"]
        
        for i, expected_id in enumerate(expected_ids):
            if expected_id in device_map:
                addr = device_map[expected_id]
                m0 = M0DeviceI2C(
                    pi=self.pi,
                    id=expected_id,
                    address=addr,
                    reset_pin=self.config["reset_pins"][i],
                    location=["left", "middle", "right"][i]
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

  def m0_discover(self):
    """
    Searches /dev/ttyACM*, /dev/ttyUSB* for boards that respond with "ID:M0_x"
    when we send "WHOAREYOU?".
    Returns a dict like {"M0_0": "/dev/ttyACM0", "M0_1": "/dev/ttyACM1"}.
    """
    logger.info("Discovering M0 boards...")

    board_map = {}
    ports = serial.tools.list_ports.comports()

    for p in ports:
        # Check if it's an ACM or USB device
        if "ACM" in p.device or "USB" in p.device:
            try:
                with serial.Serial(p.device, 115200, timeout=1) as ser:
                    time.sleep(0.3)
                    ser.write(b"WHOAREYOU?\n")
                    line = ser.readline().decode("utf-8", errors="ignore").strip()
                    if line.startswith("ID:"):
                        board_id = line.split(":", 1)[1]
                        board_map[board_id] = p.device
                        logger.debug(f"Discovered {board_id} on {p.device}")
            except Exception as e:
                logger.error(f"Could not open {p.device}: {e}")
      
    # if len(board_map) == 0:
    #     logger.error("No M0 boards found. Please check the connections.")
    # else:
    #     logger.info(f"Discovered M0 boards: {board_map}")
    #     for m0 in self.m0s:
    #         if m0.id in board_map:
    #             m0.port = board_map[m0.id]
    #             logger.info(f"Set {m0.id} serial port to {board_map[m0.id]}")
    #         else:
    #             logger.error(f"{m0.id} not found in discovered boards. Please check the connections.")

  def m0_send_command(self, command):
    """
    Sends a command to all M0 boards
    """
    [m0.send_command(command) for m0 in self.m0s]

  def m0_reset(self):
    # Reset all the M0 boards
    logger.info("Resetting M0 boards...")
    [m0.reset() for m0 in self.m0s]
  
  def m0_initialize(self):
    # Initialize all the devices
    [m0.initialize() for m0 in self.m0s]
  
  def m0_sync_images(self):
    # Sync the image folders for all M0s
    [m0.sync_image_folder() for m0 in self.m0s]

  def m0_upload_sketches(self):
    # Upload sketches to all M0s
    self.compile_sketch()
    [m0.upload_sketch() for m0 in self.m0s]
  
  def m0_clear(self):
    # Send the blank command to all M0s
    [m0.send_command("BLACK") for m0 in self.m0s]
  
  def m0_show_image(self):
    # Send the show image command to all M0s
    [m0.send_command("SHOW") for m0 in self.m0s]

  def default_state(self):
    self.m0_send_command("BLACK")
    self.reward_led.deactivate()
    self.punishment_led.deactivate()
    self.buzzer.deactivate()
    self.reward.stop()

if __name__ == "__main__":
  # chamber = Chamber()
  # [m0.initialize() for m0 in chamber.m0s]

  # [m0.sync_image_folder() for m0 in chamber.m0s]

  logger.info("Chamber initialized.")