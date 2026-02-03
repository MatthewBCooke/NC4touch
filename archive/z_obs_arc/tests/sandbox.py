# On a Raspberry Pi 4, create initial functions for the project

import smbus
# import RPi.GPIO as GPIO
import time
import pigpio
from src.peripherals.buzzer import *

I2C_CHANNEL = 1    


# Scan I2C bus for devices
def scan_i2c():
    i2c = smbus.SMBus(I2C_CHANNEL)
    devices = []
    for addr in range(0x03, 0x78):
        try:
            i2c.read_byte(addr)
            devices.append(addr)
        except:
            pass
    return devices

if __name__ == '__main__':

    pi = pigpio.pi()
    buzzer = Buzzer(pi, 12)
    buzzer.activate()
    reward_led = LED(pi, 10, brightness=60)  
    house_led = LED(pi, 11, brightness=100)  
    beam_break_sensor = BeamBreak(pin=18)


    buzzer.activate()
    time.sleep(1)  
    buzzer.deactivate()

    reward_led.activate()
    time.sleep(5)
    reward_led.deactivate()

    house_led.activate()
    time.sleep(10)
    house_led.deactivate()