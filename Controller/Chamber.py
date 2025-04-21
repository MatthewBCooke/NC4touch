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
import time
import serial
import serial.tools.list_ports
from helpers import wait_for_dmesg

class Chamber:
  def __init__(self,
               reward_LED_pin = 21,
               reward_pump_pin = 27,
               beambreak_pin = 4,
               punishment_LED_pin = 17,
               buzzer_pin = 16,
               reset_pins = [6, 5, 25]):
    self.reward_LED_pin = reward_LED_pin
    self.reward_pump_pin = reward_pump_pin
    self.beambreak_pin = beambreak_pin
    self.punishment_LED_pin = punishment_LED_pin
    self.buzzer_pin = buzzer_pin
    self.reset_pins = reset_pins

    self.pi = pigpio.pi()

    # Initialize M0s
    self.left_m0 = M0Device(pi = self.pi, id = "M0_0", reset_pin = self.reset_pins[0])
    self.middle_m0 = M0Device(pi = self.pi, id = "M0_1", reset_pin = self.reset_pins[1])
    self.right_m0 = M0Device(pi = self.pi, id = "M0_2", reset_pin = self.reset_pins[2])

    self.m0s = [self.left_m0, self.middle_m0, self.right_m0]

    self.reward_LED = LED(pi=self.pi, pin=self.reward_LED_pin, brightness = 140)
    self.punishment_LED = LED(pi=self.pi, pin=self.punishment_LED_pin, brightness = 255)
    self.beambreak = BeamBreak(pi=self.pi, pin=self.beambreak_pin)
    self.buzzer = Buzzer(pi=self.pi, pin=self.buzzer_pin)
    self.reward = Reward(pi=self.pi, pin=self.reward_pump_pin, serial_port=None)
  
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
                        print(f"Discovered {board_id} on {p.device}")
            except Exception as e:
                print(f"Could not open {p.device}: {e}")

    return board_map


  def initialize(self):
    # Initialize all the devices
    [m0.initialize() for m0 in self.m0s]

    self.reward.setup_reward()

if __name__ == "__main__":
  chamber = Chamber()
  # [m0.initialize() for m0 in chamber.m0s]
  # [m0.sync_image_folder() for m0 in chamber.m0s]

  # chamber.reward_LED.turn_on()
  # chamber.punishment_LED.turn_on()
  # chamber.buzzer.turn_on()

  # time.sleep(2)

  # chamber.reward_LED.turn_off()
  # chamber.punishment_LED.turn_off()
  # chamber.buzzer.turn_off()

  print("Chamber initialized.")
  input("Press Enter to exit.")
  print("Chamber stopped.")