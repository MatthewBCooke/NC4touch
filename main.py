#!/home/nc4/TouchscreenApparatus/venv/bin/python

# sudo python3 /home/nc4/TouchscreenApparatus/main.py

from src.peripherals.lcd import LCD
from src.peripherals.buzzer import Buzzer
from src.peripherals.reward import Reward
from src.peripherals.beam_break import BeamBreak
from src.peripherals.led import LED
import time

if __name__ == "__main__":
    # Initialize the LCD class
    lcd = LCD(framebuffer_device="/dev/fb0", image_dir="data/images")

    # Load first image
    lcd.load_image("C01.png")
    time.sleep(2)

    # Load second image
    lcd.load_image("B01.bmp")
    time.sleep(2)

    # Clear the screen at the end
    lcd.clear_screen()
    print("Image display test complete.")
