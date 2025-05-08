# Chamber class for the Touchscreen chamber
#
# Manu Madhav
# 2025

import pigpio
import time
import serial
import serial.tools.list_ports

from LED import LED
from Reward import Reward
from BeamBreak import BeamBreak
from Buzzer import Buzzer
from M0Device import M0Device
from Camera import Camera

from Config import Config

import logging
logger = logging.getLogger(f"session_logger.{__name__}")

class Chamber:
  def __init__(self, chamber_config = {}, chamber_config_file = '~/chamber_config.yaml'):
    """
    Chamber class for the Touchscreen chamber.
    """
    self.config = Config(config = chamber_config, config_file = chamber_config_file)
    self.config.ensure_param("chamber_name", "Chamber0")
    self.config.ensure_param("reward_LED_pin", 21)
    self.config.ensure_param("reward_pump_pin", 27)
    self.config.ensure_param("beambreak_pin", 4)
    self.config.ensure_param("punishment_LED_pin", 17)
    self.config.ensure_param("buzzer_pin", 16)
    self.config.ensure_param("reset_pins", [6, 5, 25])
    self.config.ensure_param("camera_device", "/dev/video0")

    self.pi = pigpio.pi()

    # Initialize M0s
    self.left_m0 = M0Device(pi = self.pi, id = "M0_0", reset_pin = self.config["reset_pins"][0])
    # self.middle_m0 = M0Device(pi = self.pi, id = "M0_1", reset_pin = self.config["reset_pins"][1])
    self.right_m0 = M0Device(pi = self.pi, id = "M0_1", reset_pin = self.config["reset_pins"][2])

    self.m0s = [self.left_m0, self.right_m0]

    self.reward_led = LED(pi=self.pi, pin=self.config["reward_LED_pin"], brightness = 140)
    self.punishment_led = LED(pi=self.pi, pin=self.config["punishment_LED_pin"], brightness = 255)
    self.beambreak = BeamBreak(pi=self.pi, pin=self.config["beambreak_pin"])
    self.buzzer = Buzzer(pi=self.pi, pin=self.config["buzzer_pin"])
    self.reward = Reward(pi=self.pi, pin=self.config["reward_pump_pin"])
    self.camera = Camera(device=self.config["camera_device"])

  def __del__(self):
    self.pi.stop()
    [m0.stop() for m0 in self.m0s]
  
  def m0_discover(self):
    """
    Searches /dev/ttyACM*, /dev/ttyUSB* for boards that respond with "ID:M0_x"
    when we send "WHOAREYOU?".
    Returns a dict like {"M0_0": "/dev/ttyACM0", "M0_1": "/dev/ttyACM1"}.
    """
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
      
    if len(board_map) == 0:
        logger.error("No M0 boards found. Please check the connections.")
    else:
        logger.info(f"Discovered M0 boards: {board_map}")
        for m0 in self.m0s:
            if m0.id in board_map:
                m0.port = board_map[m0.id])
                logger.info(f"Set {m0.id} serial port to {board_map[m0.id]}")
            else:
                logger.error(f"{m0.id} not found in discovered boards. Please check the connections.")

  def m0_send_command(self, command):
    """
    Sends a command to all M0 boards
    """
    [m0.send_command(command) for m0 in self.m0s]

  def m0_reset(self):
    # Reset all the M0 boards
    [m0.reset() for m0 in self.m0s]
  
  def m0_initialize(self):
    # Initialize all the devices
    [m0.initialize() for m0 in self.m0s]
  
  def m0_sync_images(self):
    # Sync the image folders for all M0s
    [m0.sync_image_folder() for m0 in self.m0s]

  def m0_upload_sketches(self):
    # Upload sketches to all M0s
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