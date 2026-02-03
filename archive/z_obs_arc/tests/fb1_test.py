import numpy as np
import time

# Open the framebuffer for /dev/fb1
buf = np.memmap('/dev/fb1', dtype='uint16', mode='w+', shape=(480, 320))  # Adjusted for driver-configured resolution
buf[:] = 0xFFFF  # Fill with white
time.sleep(1)
buf[:] = 0x0000  # Clear to black
