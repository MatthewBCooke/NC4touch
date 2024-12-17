import os
import time

# Paths to images
IMAGE_PATHS = [
    "/home/nc4/TouchscreenApparatus/tests/A01.bmp",
    "/home/nc4/TouchscreenApparatus/tests/B01.bmp"
]

# Framebuffer device
FRAMEBUFFER_DEVICE = "/dev/fb0"

def display_image(image_path):
    """Uses fbi to display the image."""
    print(f"Displaying image: {image_path}")
    command = f"sudo fbi -d {FRAMEBUFFER_DEVICE} -T 1 --noverbose {image_path}"
    os.system(command)

def clear_framebuffer():
    """Clears the framebuffer display."""
    os.system(f"sudo fbi -d {FRAMEBUFFER_DEVICE} -T 1 --noverbose --blank 0")

# Main script
if __name__ == "__main__":
    print("Starting image display test...")

    for image_path in IMAGE_PATHS:
        if not os.path.exists(image_path):
            print(f"Error: File '{image_path}' does not exist.")
            continue

        # Display image
        display_image(image_path)
        time.sleep(2)  # Delay between images

    # Clear framebuffer (optional)
    clear_framebuffer()
    print("Image display test complete.")
