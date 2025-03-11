# Chamber class for the Touchscreen chamber
#
# Manu Madhav
# 2025

import pigpio
from Controller.LED import LED
from Controller.Reward import Reward
from Controller.BeamBreak import BeamBreak
from Controller.Buzzer import Buzzer

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

    self.reward_LED = LED(self.pi, self.reward_LED_pin, brightness = 140)
    self.reward = Reward(self.pi, self.reward_pump_pin)
    self.beambreak = BeamBreak(self.pi, self.beambreak_pin)
    self.punishment_LED = LED(self.pi, self.punishment_LED_pin, brightness = 255)
    self.buzzer = Buzzer(self.pi, self.buzzer_pin)

    # Initialize M0s and find the ports