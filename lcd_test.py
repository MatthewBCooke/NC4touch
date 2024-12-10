import gpiod
import time

# Constants
CHIP_NAME = "gpiochip0"  # Default GPIO chip on most Raspberry Pi boards
LINE_NUMBER = 17         # GPIO pin to test (BCM numbering)

def main():
    # Get the GPIO chip
    chip = gpiod.Chip(CHIP_NAME)

    # Get the specific GPIO line
    line = chip.get_line(LINE_NUMBER)

    # Request the GPIO line for output
    config = gpiod.LineRequest()
    config.consumer = "lcd_test"
    config.request_type = gpiod.LINE_REQ_DIR_OUT

    line.request(config)

    print(f"Testing GPIO line {LINE_NUMBER}...")
    try:
        # Toggle the GPIO line
        for i in range(10):  # Blink 10 times
            line.set_value(1)
            print(f"GPIO {LINE_NUMBER} set HIGH")
            time.sleep(0.5)

            line.set_value(0)
            print(f"GPIO {LINE_NUMBER} set LOW")
            time.sleep(0.5)

    finally:
        # Release the GPIO line
        line.release()
        print("GPIO test complete. Line released.")

if __name__ == "__main__":
    main()
