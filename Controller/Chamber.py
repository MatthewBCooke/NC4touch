# Chamber class for the Touchscreen chamber
#
# Manu Madhav
# 2025

import pigpio
from LED import LED
from Reward import Reward
from BeamBreak import BeamBreak
from Buzzer import Buzzer
from M0Device import M0Device
from Camera import Camera
import time
import serial
import serial.tools.list_ports
from helpers import wait_for_dmesg
import os
import yaml

import logging
session_logger = logging.getLogger('session_logger')
logger = session_logger.getChild(__name__)
logger.setLevel(logging.DEBUG)

class Chamber:
  def __init__(self, chamber_config = {}):
    if not isinstance(chamber_config, dict):
      logger.error("chamber_config must be a dictionary")
    
    print("Initializing Chamber...")
      chamber_config = {}

    self.chamber_config = chamber_config
    self.chamber_name = self.chamber_config.get("chamber_name", "Chamber0")
    self.reward_LED_pin = self.chamber_config.get("reward_LED_pin", 21)
    self.reward_pump_pin = self.chamber_config.get("reward_pump_pin", 27)
    self.beambreak_pin = self.chamber_config.get("beambreak_pin", 4)
    self.punishment_LED_pin = self.chamber_config.get("punishment_LED_pin", 17)
    self.buzzer_pin = self.chamber_config.get("buzzer_pin", 16)
    self.reset_pins = self.chamber_config.get("reset_pins", [6, 5, 25])

    self.pi = pigpio.pi()

    # Initialize M0s
    self.left_m0 = M0Device(pi = self.pi, id = "M0_0", reset_pin = self.reset_pins[0])
    # self.middle_m0 = M0Device(pi = self.pi, id = "M0_1", reset_pin = self.reset_pins[1])
    self.right_m0 = M0Device(pi = self.pi, id = "M0_1", reset_pin = self.reset_pins[2])

    self.m0s = [self.left_m0, self.right_m0]

    self.reward_led = LED(pi=self.pi, pin=self.reward_LED_pin, brightness = 140)
    self.punishment_led = LED(pi=self.pi, pin=self.punishment_LED_pin, brightness = 255)
    self.beambreak = BeamBreak(pi=self.pi, pin=self.beambreak_pin)
    self.buzzer = Buzzer(pi=self.pi, pin=self.buzzer_pin)
    self.reward = Reward(pi=self.pi, pin=self.reward_pump_pin)
    self.camera = Camera(camera_device="/dev/video0")

  def __del__(self):
    self.pi.stop()
    [m0.stop() for m0 in self.m0s]
  
  def reset_m0_boards(self):
    [m0.reset() for m0 in self.m0s]
  
  def discover_m0_boards(self):
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

    return board_map


  def initialize(self):
    # Initialize all the devices
    [m0.initialize() for m0 in self.m0s]

    self.reward.setup_reward()

if __name__ == "__main__":
  # chamber = Chamber()
  # [m0.initialize() for m0 in chamber.m0s]

  # [m0.sync_image_folder() for m0 in chamber.m0s]

  logger.info("Chamber initialized.")