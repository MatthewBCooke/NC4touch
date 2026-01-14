"""
Virtual M0 Device for touchscreen simulation.

Simulates the M0 board touchscreen interface without requiring physical hardware.
"""

import time
import threading
import queue
from enum import Enum
import os

import logging
logger = logging.getLogger(f"session_logger.{__name__}")


class M0Mode(Enum):
    UNINITIALIZED = 0
    PORT_OPEN = 1
    SERIAL_COMM = 2
    PORT_CLOSED = 3
    UD = 4


class VirtualM0Device:
    """
    Virtual implementation of M0Device for testing without physical hardware.
    Maintains the same API as the real M0Device.
    """

    def __init__(self, pi=None, id=None, reset_pin=None,
                 port=None, baudrate=115200, location=None, image_dir=None):
        self.id = id
        self.reset_pin = reset_pin
        self.port = port or f"VIRTUAL_{id}"
        self.baudrate = baudrate
        self.location = location
        self.image_dir = image_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data', 'images')

        self.ser = None
        self.ud_mount_loc = None

        self.stop_flag = threading.Event()
        self.message_queue = queue.Queue()
        self.write_lock = threading.Lock()
        self.read_loop_interval = 0.1

        # Virtual touchscreen state
        self._is_touched = False  # Internal attribute
        self._touch_coordinates = (0, 0)
        self._current_image = None  # Stores image name (e.g., "A01")
        self._current_image_path = None  # Stores full path to BMP file
        self._display_enabled = True
        self._loaded_image = None  # Image loaded but not yet shown

        self.code_dir = os.path.dirname(os.path.abspath(__file__))
        self.mode = M0Mode.UNINITIALIZED

        # Virtual read thread
        self._virtual_read_thread = None

        logger.info(f"[{self.id}] Virtual M0 Device initialized")

    def __del__(self):
        self.stop()

    def stop(self):
        """Stops the virtual device."""
        self.stop_flag.set()
        if self._virtual_read_thread and self._virtual_read_thread.is_alive():
            self._virtual_read_thread.join(timeout=1.0)
        logger.info(f"[{self.id}] Virtual device stopped.")
        self.mode = M0Mode.UNINITIALIZED

    def initialize(self):
        """Initialize the virtual device."""
        logger.info(f"[{self.id}] Initializing virtual M0 device...")
        self.mode = M0Mode.PORT_OPEN
        time.sleep(0.1)
        self.mode = M0Mode.SERIAL_COMM
        self.start_read_thread()
        time.sleep(0.1)
        self.message_queue.put((self.id, f"ID:{self.id}"))
        logger.info(f"[{self.id}] Virtual device initialized")

    def start_read_thread(self):
        """Start the virtual read thread."""
        self.stop_flag.clear()
        self._virtual_read_thread = threading.Thread(
            target=self._virtual_read_loop,
            daemon=True
        )
        self._virtual_read_thread.start()
        logger.debug(f"[{self.id}] Virtual read thread started")

    def _virtual_read_loop(self):
        """Virtual read loop that simulates serial communication."""
        while not self.stop_flag.is_set():
            time.sleep(self.read_loop_interval)
            # Touch events are injected via simulate_touch()

    def send_command(self, command):
        """
        Send a command to the virtual device.
        Simulates the serial write operation.
        """
        with self.write_lock:
            logger.debug(f"[{self.id}] Virtual command sent: {command}")
            
            # Simulate responses for known commands
            if command == "WHOAREYOU?":
                self.message_queue.put((self.id, f"ID:{self.id}"))
            elif command.startswith("IMG:"):
                # Load image (like real M0: IMG:A01 loads A01.bmp)
                image_name = command.split(":", 1)[1]
                image_path = self._resolve_image_path(image_name)
                if image_path:
                    self._loaded_image = image_name
                    logger.debug(f"[{self.id}] Loaded image: {image_name} from {image_path}")
                else:
                    logger.warning(f"[{self.id}] Image not found: {image_name}")
            elif command == "SHOW":
                # Display the loaded image
                if self._loaded_image:
                    self._current_image = self._loaded_image
                    self._current_image_path = self._resolve_image_path(self._loaded_image)
                    logger.debug(f"[{self.id}] Showing image: {self._current_image}")
                else:
                    logger.warning(f"[{self.id}] SHOW called but no image loaded")
            elif command == "BLACK":
                # Clear display to black
                self._current_image = None
                self._current_image_path = None
                self._loaded_image = None
                logger.debug(f"[{self.id}] Display cleared (BLACK)")
            elif command.startswith("DISPLAY:"):
                # Legacy support: DISPLAY:path displays directly
                image_path = command.split(":", 1)[1]
                self._current_image = image_path
                self._current_image_path = image_path
                logger.debug(f"[{self.id}] Displaying image: {image_path}")
            elif command == "CLEAR":
                # Legacy support
                self._current_image = None
                self._current_image_path = None
                logger.debug(f"[{self.id}] Display cleared")
            elif command == "SCREENSHARE":
                logger.debug(f"[{self.id}] Screenshare mode activated")

    def get_messages(self):
        """
        Retrieve all messages from the message queue.
        Returns a list of (id, message) tuples.
        """
        messages = []
        while not self.message_queue.empty():
            try:
                messages.append(self.message_queue.get_nowait())
            except queue.Empty:
                break
        return messages

    def clear_messages(self):
        """Clear all messages from the queue."""
        while not self.message_queue.empty():
            try:
                self.message_queue.get_nowait()
            except queue.Empty:
                break

    def is_touched(self):
        """
        Check if the touchscreen is currently being touched.
        Method version for compatibility with trainer code that calls m0.is_touched().
        """
        return self._is_touched

    # ===== Virtual-specific methods for simulation =====

    def simulate_touch(self, x=None, y=None, duration=0.1):
        """
        Simulate a touch event on the virtual touchscreen.
        
        Args:
            x: X coordinate (0-320)
            y: Y coordinate (0-480)
            duration: How long the touch lasts in seconds
        """
        if x is None:
            x = 160  # Center
        if y is None:
            y = 240  # Center
            
        self._touch_coordinates = (x, y)
        self._is_touched = True
        self.message_queue.put((self.id, f"TOUCH:{x},{y}"))
        logger.info(f"[{self.id}] Virtual touch at ({x}, {y})")

        # Auto-release after duration
        def release_touch():
            time.sleep(duration)
            self._is_touched = False
            self.message_queue.put((self.id, "RELEASE"))
            logger.debug(f"[{self.id}] Touch released")

        threading.Thread(target=release_touch, daemon=True).start()

    def _resolve_image_path(self, image_name):
        """Resolve image name to full file path."""
        # If already a full path, return as-is
        if os.path.isabs(image_name) or '/' in image_name:
            return image_name
        
        # Try with .bmp extension
        bmp_path = os.path.join(self.image_dir, f"{image_name}.bmp")
        if os.path.exists(bmp_path):
            return bmp_path
        
        # Try without extension (in case it's included)
        direct_path = os.path.join(self.image_dir, image_name)
        if os.path.exists(direct_path):
            return direct_path
        
        logger.warning(f"[{self.id}] Image file not found: {image_name} in {self.image_dir}")
        return None

    def get_current_image(self):
        """Get the currently displayed image name."""
        return self._current_image
    
    def get_current_image_path(self):
        """Get the full path to the currently displayed image file."""
        return self._current_image_path

    def get_touch_coordinates(self):
        """Get the last touch coordinates."""
        return self._touch_coordinates

    def set_display_enabled(self, enabled):
        """Enable or disable the virtual display."""
        self._display_enabled = enabled
        logger.debug(f"[{self.id}] Display {'enabled' if enabled else 'disabled'}")
