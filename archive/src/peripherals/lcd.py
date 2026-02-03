import os

class LCD:
    """
    Class to manage image display on an LCD framebuffer device using 'fbi'
    and control the backlight via the Linux backlight interface.
    """
    BACKLIGHT_PATH = "/sys/class/backlight/soc:backlight/brightness"

    def __init__(self, framebuffer_device="/dev/fb0", image_dir="data/images"):
        """
        Initialize the LCD class with framebuffer device and image directory.
        """
        self.framebuffer_device = framebuffer_device
        self.image_dir = image_dir

    def set_backlight(self, state):
        """
        Turn the backlight ON or OFF using the backlight interface.
        :param state: True to turn on, False to turn off.
        """
        value = "1" if state else "0"
        if os.path.exists(self.BACKLIGHT_PATH):
            try:
                with open(self.BACKLIGHT_PATH, "w") as f:
                    f.write(value)
                print(f"Backlight {'ON' if state else 'OFF'}")
            except PermissionError:
                print("Error: Run the script with 'sudo' to control the backlight.")
        else:
            print("Error: Backlight control path not found.")

    def load_image(self, filename):
        """
        Load and display an image on the framebuffer.
        :param filename: Name of the image file (e.g., 'A01.bmp').
        """
        # Construct the full path to the image
        image_path = os.path.join(self.image_dir, filename)

        # Check if the image file exists
        if not os.path.exists(image_path):
            print(f"Error: Image file '{image_path}' not found.")
            return

        print(f"Displaying image: {image_path}")
        # Command to display the image using 'fbi'
        os.system(f"sudo fbi -d {self.framebuffer_device} -T 1 --noverbose {image_path}")

        # Turn the backlight on
        self.set_backlight(True)

    def clear_screen(self):
        """
        Clears the framebuffer display.
        """
        # Turn the backlight off
        self.set_backlight(False)

        print("Clearing framebuffer display...")
        os.system(f"sudo fbi -d {self.framebuffer_device} -T 1 --noverbose --blank 0")
