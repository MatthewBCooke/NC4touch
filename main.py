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
    lcd_0 = LCD(framebuffer_device="/dev/fb0", image_dir="data/images")
    lcd_1 = LCD(framebuffer_device="/dev/fb1", image_dir="data/images")

    # Load image to fb0 and fb1
    lcd_0.load_image("C01.png")
    lcd_1.load_image("B01.bmp")
    time.sleep(2)

    # Switch images
    lcd_0.load_image("B01.bmp")
    lcd_1.load_image("C01.png")
    time.sleep(2)

    # Clear the screen at the end
    lcd_0.clear_screen()
    print("Image display test complete.")
