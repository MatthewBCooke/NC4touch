# M0Device is a class that represents one M0 board with a persistent serial connection.
#
# Refactored to use centralized hardware configuration
#
# Gelareh Modara
# Manu Madhav
# OpenClaw Subagent
# 2025-2026

try:
    import pigpio
except ImportError:
    pigpio = None
try:
    import serial
except ImportError:
    serial = None

import time
import subprocess
import threading
import queue
from helpers import wait_for_dmesg
from enum import Enum
import os
from typing import Optional

import logging
logger = logging.getLogger(f"session_logger.{__name__}")

# Import configuration (optional - will use defaults if not provided)
try:
    from config import M0SerialConfig
except ImportError:
    M0SerialConfig = None


class M0Mode(Enum):
    """M0 device operational modes."""
    UNINITIALIZED = 0
    PORT_OPEN = 1
    SERIAL_COMM = 2
    PORT_CLOSED = 3
    UD = 4


class M0Device:
    """
    Represents one M0 board with a persistent serial connection.
    
    Manages serial communication, touch event detection, and firmware updates
    for DFRobot M0 touchscreen controllers.
    
    Args:
        pi: pigpio.pi instance for GPIO control
        id: Device identifier (e.g., "M0_0")
        reset_pin: GPIO pin for hardware reset
        port: Serial port path (e.g., "/dev/ttyACM0")
        baudrate: Serial baud rate (default: 115200)
        location: Physical location identifier (e.g., "left", "middle", "right")
        config: M0SerialConfig instance (optional, uses defaults if None)
    """

    def __init__(
        self,
        pi,
        id: Optional[str] = None,
        reset_pin: Optional[int] = None,
        port: Optional[str] = None,
        baudrate: int = 115200,
        location: Optional[str] = None,
        config: Optional['M0SerialConfig'] = None
    ):
        if pigpio is not None and not isinstance(pi, pigpio.pi):
            logger.error("pi must be an instance of pigpio.pi")
            raise ValueError("pi must be an instance of pigpio.pi")
        
        self.pi = pi
        self.id = id
        self.reset_pin = reset_pin
        self.port = port
        self.location = location
        
        # Load configuration
        if config is not None:
            self.config = config
        elif M0SerialConfig is not None:
            self.config = M0SerialConfig()
        else:
            # Fallback to hardcoded defaults if config not available
            self.config = None
            logger.warning("M0SerialConfig not available, using hardcoded defaults")
        
        # Apply config or fallback values
        self.baudrate = baudrate if config is None else self.config.baudrate
        self.timeout = 5.0 if config is None else self.config.timeout
        self.read_loop_interval = 0.1 if config is None else self.config.read_loop_interval
        self.max_retries = 3 if config is None else self.config.max_retries
        self.retry_backoff_base = 0.1 if config is None else self.config.retry_backoff_base
        
        # Serial connection
        self.ser: Optional[serial.Serial] = None
        self.ud_mount_loc: Optional[str] = None
        
        # Threading
        self.stop_flag = threading.Event()
        self.message_queue = queue.Queue()  # Stores (id, text) tuples
        self.write_lock = threading.Lock()
        self.thread: Optional[threading.Thread] = None
        
        # State
        self.is_touched = False
        self.mode = M0Mode.UNINITIALIZED
        
        # Paths
        self.code_dir = os.path.dirname(os.path.abspath(__file__))
    
    def __del__(self):
        """Clean up the M0Device by stopping the read thread and closing the serial port."""
        try:
            if hasattr(self, 'id'):
                logger.info(f"Cleaning up M0Device {self.id}...")
            self.stop()
        except:
            pass
    
    def stop(self) -> None:
        """Stop the read thread and close the serial port."""
        self.stop_flag.set()
        
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
                logger.info(f"[{self.id}] Closed port {self.port}.")
            except Exception as e:
                logger.error(f"[{self.id}] Error closing serial port: {e}")
        
        logger.info(f"[{self.id}] Stopped.")
        self.mode = M0Mode.UNINITIALIZED

    def initialize(self) -> bool:
        """
        Initialize the M0 board: find device, open serial, start read thread.
        
        Returns:
            bool: True if initialization successful
        """
        logger.info(f"[{self.id}] Initializing M0Device...")
        
        try:
            self.find_device()
            time.sleep(1)
            
            self.open_serial()
            time.sleep(1)
            
            self.start_read_thread()
            time.sleep(1)
            
            self.send_command("WHOAREYOU?")
            return True
            
        except Exception as e:
            logger.error(f"[{self.id}] Initialization failed: {e}")
            return False
    
    def arduino_cli_find_device(self) -> str:
        """
        List connected Arduino boards using arduino-cli.
        
        Returns:
            str: arduino-cli output
        """
        try:
            output = subprocess.check_output(
                "~/bin/arduino-cli board list",
                shell=True,
                stderr=subprocess.STDOUT
            ).decode("utf-8")
            logger.info(f"Arduino CLI Boards:\n{output}")
            return output
        except subprocess.CalledProcessError as e:
            logger.error(f"arduino-cli error: {e.output.decode('utf-8')}")
            return ""
        except Exception as e:
            logger.error(f"Error listing Arduino boards: {e}")
            return ""
    
    def find_device(self) -> bool:
        """
        Find the port and device ID of the M0 board using hardware reset.
        
        Returns:
            bool: True if device found
        """
        logger.info(f"[{self.id}] Finding M0 board on reset pin {self.reset_pin}.")
        
        try:
            self.reset()
            time.sleep(1)
            
            # Wait for device to appear in dmesg
            tty_line = wait_for_dmesg("ttyACM")
            
            if tty_line:
                # Extract port from dmesg line
                port_suffix = tty_line.split("ttyACM")[1].split(":")[0]
                self.port = f"/dev/ttyACM{port_suffix}"
                
                logger.info(f"[{self.id}] Found device on port {self.port}.")
                self.mode = M0Mode.PORT_CLOSED
                return True
            else:
                logger.error(f"[{self.id}] No ttyACM device found in dmesg.")
                return False
                
        except Exception as e:
            logger.error(f"[{self.id}] Error finding device: {e}")
            return False
    
    def open_serial(self) -> bool:
        """
        Open the serial port for communication.
        
        Returns:
            bool: True if port opened successfully
        """
        if self.port is None:
            logger.error(f"[{self.id}] Port not found. Finding device...")
            self.find_device()
        
        if self.mode != M0Mode.PORT_CLOSED:
            logger.error(f"[{self.id}] Port not closed; cannot open serial port.")
            return False
        
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            logger.info(f"[{self.id}] Opened port {self.port} at {self.baudrate} baud.")
            self.mode = M0Mode.PORT_OPEN
            return True
            
        except Exception as e:
            logger.error(f"[{self.id}] Failed to open {self.port}: {e}")
            return False
    
    def start_read_thread(self) -> bool:
        """
        Start the background read thread for incoming serial data.
        
        Returns:
            bool: True if thread started successfully
        """
        if self.mode != M0Mode.PORT_OPEN:
            logger.error(f"[{self.id}] Port not open; cannot start read thread.")
            return False
        
        if self.ser is None:
            logger.error(f"[{self.id}] Serial port not initialized; cannot start read thread.")
            return False
        
        self.stop_flag.clear()
        self.thread = threading.Thread(target=self.read_loop, daemon=True)
        self.thread.start()
        self.mode = M0Mode.SERIAL_COMM
        
        logger.info(f"[{self.id}] Started read thread.")
        return True
    
    def read_loop(self) -> None:
        """Background thread loop for reading serial data."""
        logger.info(f"[{self.id}] Starting read loop.")
        
        while not self.stop_flag.is_set():
            try:
                if self.ser and self.ser.is_open:
                    # Read a line from serial port
                    line = self.ser.readline().decode("utf-8", errors="ignore").strip()
                    
                    if line:
                        logger.info(f"[{self.id}] {line}")
                        self.message_queue.put((self.id, line))
                        
                        # Update touch state
                        if line.startswith("TOUCH"):
                            self.is_touched = True
                            logger.debug(f"[{self.id}] Touch detected.")
                        else:
                            self.is_touched = False
                else:
                    time.sleep(self.read_loop_interval)
                    
            except Exception as e:
                logger.error(f"[{self.id}] read_loop error: {e}")
                self._attempt_reopen()
        
        logger.info(f"[{self.id}] Stopping read loop.")
    
    def stop_read_thread(self) -> bool:
        """
        Stop the background read thread.
        
        Returns:
            bool: True if thread stopped successfully
        """
        if self.mode != M0Mode.SERIAL_COMM:
            logger.error(f"[{self.id}] Port not in serial communication mode.")
            return False
        
        logger.info(f"[{self.id}] Stopping read thread.")
        self.stop_flag.set()
        
        if self.thread:
            self.thread.join(timeout=2.0)
        
        self.mode = M0Mode.PORT_OPEN
        return True
    
    def send_command(self, cmd: str) -> bool:
        """
        Send command string to M0 board (thread-safe).
        
        Args:
            cmd: Command string (e.g., "SHOW", "BLACK", "IMG:A01")
            
        Returns:
            bool: True if command sent successfully
        """
        if self.mode != M0Mode.SERIAL_COMM:
            logger.error(f"[{self.id}] Port not in serial communication mode; cannot send command.")
            return False
        
        with self.write_lock:
            try:
                msg = (cmd + "\n").encode("utf-8")
                
                # Flush buffers if configured
                if self.config and self.config.flush_on_send:
                    self.ser.reset_input_buffer()
                    self.ser.reset_output_buffer()
                
                self.ser.write(msg)
                logger.info(f"[{self.id}] -> {cmd}")
                return True
                
            except Exception as e:
                logger.error(f"[{self.id}] Error writing to serial port: {e}")
                return False
    
    def reset(self) -> None:
        """Perform hardware reset via GPIO pin."""
        logger.info(f"[{self.id}] Resetting M0 board on pin {self.reset_pin}.")
        
        # Get reset timing from config
        pulse_duration = 0.01 if self.config is None else self.config.reset_pulse_duration
        
        if self.mode == M0Mode.SERIAL_COMM:
            self.stop_read_thread()
        
        try:
            # Send reset pulse
            self.pi.set_mode(self.reset_pin, pigpio.OUTPUT)
            time.sleep(0.01)
            self.pi.write(self.reset_pin, 0)  # Pull low
            time.sleep(pulse_duration)
            self.pi.write(self.reset_pin, 1)  # Release
            time.sleep(0.01)
            self.pi.set_mode(self.reset_pin, pigpio.INPUT)  # High-Z
            
            self.mode = M0Mode.PORT_CLOSED
            
        except Exception as e:
            logger.error(f"[{self.id}] Error resetting M0 board: {e}")
    
    def mount_ud(self) -> bool:
        """
        Mount the UD drive (USB mass storage mode) via double-reset.
        
        Returns:
            bool: True if mount successful
        """
        logger.info(f"[{self.id}] Mounting UD drive on pin {self.reset_pin}.")
        
        try:
            # Double-reset to enter USB mass storage mode
            self.reset()
            time.sleep(0.1)
            self.reset()
            
            # Wait for FireBeetle-UDisk to appear
            wait_for_dmesg("FireBeetle-UDisk")
            
            # Find mount location from lsblk
            waiting = True
            timeout = 10  # 10 second timeout
            start_time = time.time()
            
            while waiting and (time.time() - start_time < timeout):
                time.sleep(0.5)
                
                lsblk = subprocess.check_output(
                    "lsblk --output MOUNTPOINTS",
                    shell=True
                ).decode("utf-8")
                
                mount_lines = [line for line in lsblk.split("\n") if line.startswith("/media")]
                
                if mount_lines:
                    self.ud_mount_loc = mount_lines[0]
                    logger.info(f"[{self.id}] Found mount location: {self.ud_mount_loc}")
                    waiting = False
            
            if not self.ud_mount_loc:
                logger.error(f"[{self.id}] Timeout waiting for UD mount")
                return False
            
            self.mode = M0Mode.UD
            return True
            
        except Exception as e:
            logger.error(f"[{self.id}] Error mounting UD drive: {e}")
            return False

    def upload_sketch(self, sketch_path: Optional[str] = None) -> bool:
        """
        Upload Arduino sketch to M0 board.
        
        Args:
            sketch_path: Path to .ino file (default: ../M0Touch/M0Touch.ino)
            
        Returns:
            bool: True if upload successful
        """
        if sketch_path is None:
            sketch_path = os.path.join(self.code_dir, "../M0Touch/M0Touch.ino")
        
        if self.mode == M0Mode.SERIAL_COMM:
            self.stop_read_thread()
        
        if self.mode == M0Mode.UD or self.port is None:
            self.find_device()
        
        logger.info(f"[{self.id}] Uploading sketch to {self.port}.")
        
        try:
            upload_output = subprocess.check_output(
                f"~/bin/arduino-cli upload --port {self.port} "
                f"--fqbn DFRobot:samd:mzero_bl {sketch_path}",
                shell=True,
                stderr=subprocess.STDOUT
            ).decode("utf-8")
            
            logger.info(f"[{self.id}] Upload output: {upload_output}")
            
            if "error" in upload_output.lower():
                logger.error(f"[{self.id}] Upload errors detected")
                return False
            else:
                logger.info(f"[{self.id}] Sketch uploaded successfully.")
                self.mode = M0Mode.PORT_CLOSED
                return True
                
        except subprocess.CalledProcessError as e:
            logger.error(f"[{self.id}] Upload failed: {e.output.decode('utf-8')}")
            return False
        except Exception as e:
            logger.error(f"[{self.id}] Error uploading sketch: {e}")
            return False
    
    def sync_image_folder(self, image_folder: Optional[str] = None) -> bool:
        """
        Sync image folder to UD drive.
        
        Args:
            image_folder: Path to image directory (default: ../data/images)
            
        Returns:
            bool: True if sync successful
        """
        logger.info(f"[{self.id}] Syncing image folder to UD drive.")
        
        if image_folder is None:
            image_folder = os.path.join(self.code_dir, "../data/images")
        
        # Mount UD drive
        if not self.mount_ud():
            return False
        
        if self.mode != M0Mode.UD:
            logger.error(f"[{self.id}] Port not in UD mode; cannot sync.")
            return False
        
        if self.ud_mount_loc is None:
            logger.error(f"[{self.id}] UD mount location not found.")
            return False
        
        # Check image folder
        if not os.path.exists(image_folder):
            logger.error(f"[{self.id}] Image folder does not exist: {image_folder}")
            return False
        
        if not os.listdir(image_folder):
            logger.error(f"[{self.id}] Image folder is empty: {image_folder}")
            return False
        
        # Sync images
        try:
            subprocess.run(
                ["rsync", "-av", image_folder, self.ud_mount_loc],
                check=True
            )
            logger.info(f"[{self.id}] Synced image folder to {self.ud_mount_loc}.")
            
            # Unmount by resetting
            time.sleep(0.1)
            self.reset()
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"[{self.id}] rsync failed: {e}")
            return False
        except Exception as e:
            logger.error(f"[{self.id}] Error syncing image folder: {e}")
            return False
    
    def flush_message_queue(self) -> None:
        """Clear all messages from the queue."""
        while not self.message_queue.empty():
            try:
                self.message_queue.get_nowait()
            except queue.Empty:
                break
    
    def _attempt_reopen(self) -> None:
        """Attempt to reinitialize the serial connection after error."""
        logger.info(f"[{self.id}] Attempting to reinitialize port {self.port}...")
        
        try:
            if self.ser:
                # Flush and close
                self.ser.reset_input_buffer()
                self.ser.reset_output_buffer()
                self.ser.close()
            
            # Reopen connection
            self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            logger.info(f"[{self.id}] Reinitialized port {self.port} successfully.")
            
        except Exception as e:
            logger.error(f"[{self.id}] Failed to reinitialize port: {e}")
            self.stop_read_thread()
            time.sleep(1)


# Test the M0Device class
if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        from config import M0SerialConfig
        config = M0SerialConfig()
        logger.info(f"Using M0SerialConfig: baudrate={config.baudrate}")
    except ImportError:
        config = None
        logger.warning("M0SerialConfig not available, using defaults")
    
    logger.info("M0Device test complete.")
