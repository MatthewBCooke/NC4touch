import os

class LCD:
    """
    Class to manage image display on an LCD framebuffer device using 'fbi'.
    """
    def __init__(self, framebuffer_device="/dev/fb0", image_dir="assets/images"):
        """
        Initialize the LCD class with framebuffer device and image directory.
        :param framebuffer_device: Path to the framebuffer device.
        :param image_dir: Directory where image assets are stored.
        """
        self.framebuffer_device = framebuffer_device
        self.image_dir = image_dir

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
        command = f"sudo fbi -d {self.framebuffer_device} -T 1 --noverbose {image_path}"
        os.system(command)

    def clear_screen(self):
        """
        Clears the framebuffer display.
        """
        print("Clearing framebuffer display...")
        os.system(f"sudo fbi -d {self.framebuffer_device} -T 1 --noverbose --blank 0")
