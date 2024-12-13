import numpy as np
import os
import time

print("Initializing framebuffer test...")

# Map the framebuffer device
try:
    buf = np.memmap('/dev/fb0', dtype='uint16', mode='w+', shape=(480, 320))
    print("Framebuffer mapped successfully.")
except Exception as e:
    print(f"Error mapping framebuffer: {e}")
    exit(1)

# Fill the screen with white
print("Filling screen with white (0xFFFF)...")
buf[:] = 0xFFFF
time.sleep(1)

# Fill the screen with yellow (0xFFC0)
print("Filling screen with yellow (0xFFC0)...")
buf[:] = 0xFFC0

print("Test complete. Screen should have transitioned from white to yellow.")
