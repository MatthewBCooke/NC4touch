# M0Device is a class that represents one M0 board with a persistent serial connection.
#
# Gelareh Modara
# Manu Madhav
# 2025

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

import logging
logger = logging.getLogger(f"session_logger.{__name__}")

class M0Mode(Enum):
    UNINITIALIZED = 0
    PORT_OPEN = 1
    SERIAL_COMM = 2
    PORT_CLOSED = 3
    UD = 4

class M0Device:
    """
    Represents one M0 board with a persistent serial connection.
    """

    def __init__(self, pi, id=None, reset_pin=None,
                 port=None, baudrate=115200, location=None):
        if pigpio is not None and not isinstance(pi, pigpio.pi):
            logger.error("pi must be an instance of pigpio.pi")
            raise ValueError("pi must be an instance of pigpio.pi")
        
        self.pi = pi

        self.id = id
        self.reset_pin = reset_pin
        self.port= port
        self.baudrate = baudrate
        self.location = location

        self.ser = None
        self.ud_mount_loc = None

        self.stop_flag = threading.Event()
        self.message_queue = queue.Queue()  # to store lines: (id, text)
        self.write_lock = threading.Lock()
        self.read_loop_interval = 0.1  # seconds

        self.is_touched = False

        self.code_dir = os.path.dirname(os.path.abspath(__file__))

        self.mode = M0Mode.UNINITIALIZED
    
    def __del__(self):
        """Clean up the M0Device by stopping the read thread and closing the serial port."""
        logger.info(f"Cleaning up M0Device {self.id}...")
        self.stop()
    
    def stop(self):
        """
        Stops the read thread and closes the serial port.
        """
        self.stop_flag.set()
        if self.ser and self.ser.is_open:
            self.ser.close()
            logger.info(f"[{self.id}] Closed port {self.port}.")
        logger.info(f"[{self.id}] Stopped.")
        self.mode = M0Mode.UNINITIALIZED

    def initialize(self):
        """
        Initializes the M0 board by finding the device, opening the serial port,
        starting the read thread, and sending the WHOAREYOU? command.
        """
        logger.info(f"[{self.id}] Initializing M0Device...")
        self.find_device()
        time.sleep(1)
        self.open_serial()
        time.sleep(1)
        self.start_read_thread()
        time.sleep(1)
        self.send_command("WHOAREYOU?")
    
    def arduino_cli_find_device(self):
        """
        Lists the connected Arduino boards using arduino-cli.
        """
        try:
            output = subprocess.check_output("arduino-cli board list", shell=True).decode("utf-8")
            logger.info(f"Arduino CLI Boards:\n{output}")
            return output
        except Exception as e:
            logger.error(f"Error listing Arduino boards: {e}")
            return ""
    
    def find_device(self):
        """
        Finds the port and device ID of the M0 board connected to the given reset pin.
        """
        logger.info(f"[{self.id}] Finding M0 board on pin {self.reset_pin}.")
        try:
            self.reset()
            time.sleep(1)

            # Wait for the device to be detected
            tty_line = wait_for_dmesg("ttyACM")

            if tty_line:
                self.port = "/dev/ttyACM" + tty_line.split("ttyACM")[1].split(":")[0]

                logger.info(f"[{self.id}] Found device on port {self.port}.")

                self.mode = M0Mode.PORT_CLOSED
            else:
                logger.error(f"[{self.id}] Error: No ttyACM device found.")
        except Exception as e:
            logger.error(f"[{self.id}] Error finding device: {e}")
    
    def open_serial(self):
        """
        Opens the serial port.
        """
        if self.port is None:
            logger.error(f"[{self.id}] Port not found. Finding device...")
            self.find_device()
        
        if not self.mode == M0Mode.PORT_CLOSED:
            logger.error(f"[{self.id}] Port not closed; cannot open serial port.")
            return

        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=5)
            logger.info(f"[{self.id}] Opened port {self.port} at {self.baudrate}.")
            self.mode = M0Mode.PORT_OPEN
        except Exception as e:
            logger.error(f"[{self.id}] Failed to open {self.port}: {e}")
    
    def start_read_thread(self):
        """
        Starts the read thread.
        """
        if not self.mode == M0Mode.PORT_OPEN:
            logger.error(f"[{self.id}] Port not open; cannot start read thread.")
            return
        if self.ser is None:
            logger.error(f"[{self.id}] Serial port not initialized; cannot start read thread.")
            return
        
        self.thread = threading.Thread(target=self.read_loop, daemon=True)
        self.thread.start()
        self.mode = M0Mode.SERIAL_COMM
    
    def read_loop(self):
        logger.info(f"[{self.id}] Starting read loop.")
        while not self.stop_flag.is_set():
            try:
                if self.ser and self.ser.is_open:
                    # Read a line from the serial port
                    line = self.ser.readline().decode("utf-8", errors="ignore").strip()
                    if line:
                        logger.info(f"[{self.id}] {line}")
                        self.message_queue.put((self.id, line))
                        if line.startswith("TOUCH"):
                            self.is_touched = True
                            logger.debug(f"[{self.id}] Touch detected.")
                        else:
                            self.is_touched = False
                else:
                    time.sleep(self.read_loop_interval)
            except Exception as e:
                logger.error(f"[{self.id}] read_loop error: {e}")
                # re-open self.ser here
                self._attempt_reopen()
        logger.info(f"[{self.id}] Stopping read loop.")
    
    def stop_read_thread(self):
        """
        Stops the read thread.
        """
        if not self.mode == M0Mode.SERIAL_COMM:
            logger.error(f"[{self.id}] Port not in serial communication mode; cannot stop read thread.")
            return
        
        logger.info(f"[{self.id}] Stopping read thread.")
        self.stop_flag.set()
        self.mode = M0Mode.PORT_OPEN
    
    def send_command(self, cmd):
        """
        Sends 'cmd' + newline to the M0 board. Thread-safe via self.write_lock.
        """
        if not self.mode == M0Mode.SERIAL_COMM:
            logger.error(f"[{self.id}] Port not in serial communication mode; cannot send command.")
            return

        with self.write_lock:
            try:
                msg = (cmd + "\n").encode("utf-8")
                self.ser.reset_input_buffer()
                self.ser.reset_output_buffer()
                self.ser.write(msg)
                logger.info(f"[{self.id}] -> {cmd}")
            except Exception as e:
                logger.error(f"[{self.id}] Error writing to serial port: {e}")
    
    def reset(self):
        logger.info(f"[{self.id}] Resetting M0 board on pin {self.reset_pin}.")

        if self.mode == M0Mode.SERIAL_COMM:
            self.stop_read_thread()

        try:
            # Need to only use GPIO reset pin as ouput during hardware reset
            # to avoid interference with the serial communication reset
            self.pi.set_mode(self.reset_pin, pigpio.OUTPUT)
            time.sleep(0.01)
            self.pi.write(self.reset_pin, 0)
            time.sleep(0.01)
            self.pi.write(self.reset_pin, 1)
            time.sleep(0.01)
            self.pi.set_mode(self.reset_pin, pigpio.INPUT)

            self.mode = M0Mode.PORT_CLOSED
        except Exception as e:
            logger.error(f"[{self.id}] Error resetting M0 board: {e}")
    
    def mount_ud(self):
        """
        Mounts the UD drive connected to the M0 board by double clicking the reset pin.
        Currently this assumes only one UD drive is mounted at a time.
        """
        logger.info(f"[{self.id}] Mounting UD drive on pin {self.reset_pin}.")

        try:
            self.reset()
            time.sleep(0.1)
            self.reset()
            
            wait_for_dmesg("FireBeetle-UDisk")
            
            
            # Find the mount location from lsblk
            waiting = True
            while waiting:
                time.sleep(0.5)
                lsblk = subprocess.check_output("lsblk --output MOUNTPOINTS", shell=True).decode("utf-8")
                if lsblk:
                    lsblk = [line for line in lsblk.split("\n") if line.startswith("/media")]
                    if lsblk:
                        self.ud_mount_loc = lsblk[0]
                        logger.info(f"[{self.id}] Found mount location: {self.ud_mount_loc}")
                        waiting = False
            
            self.mode = M0Mode.UD
        
        except Exception as e:
            logger.error(f"[{self.id}] Error mounting UD drive: {e}")

    def upload_sketch(self, sketch_path=None):
        """
        Uploads the given sketch to the M0 board.
        """

        if sketch_path is None:
            sketch_path = os.path.join(self.code_dir, "../M0Touch/M0Touch.ino")

        if self.mode == M0Mode.SERIAL_COMM:
            self.stop_read_thread()
        
        if self.mode == M0Mode.UD or self.port is None:
            self.find_device()

        logger.info(f"[{self.id}] Uploading sketch to {self.port}.")
        try:
            # Run arduino-cli upload
            upload = subprocess.check_output(f"~/bin/arduino-cli upload --port {self.port} --fqbn DFRobot:samd:mzero_bl {sketch_path}", shell=True).decode("utf-8")
            logger.info(f"[{self.id}] Upload output: {upload}")
            
            if "error" in upload.lower():
                logger.error(f"[{self.id}] Error uploading sketch: {upload}")
            else:
                logger.info(f"[{self.id}] Sketch uploaded successfully.")

            self.mode = M0Mode.PORT_CLOSED
        except Exception as e:
            logger.error(f"[{self.id}] Error uploading sketch: {e}")
    
    def sync_image_folder(self, image_folder=None):
        """
        Syncs the image folder to the UD drive connected to the M0 board.
        """

        logger.info(f"[{self.id}] Syncing image folder to UD drive.")
        if image_folder is None:
            image_folder = os.path.join(self.code_dir, "../data/images")

        # Mount the UD drive
        self.mount_ud()

        if not self.mode == M0Mode.UD:
            logger.error(f"[{self.id}] Port not in UD mode; cannot sync image folder.")
            return
        if self.ud_mount_loc is None:
            logger.error(f"[{self.id}] UD mount location not found; cannot sync image folder.")
            return
        # Check if the image folder exists
        if not os.path.exists(image_folder):
            logger.error(f"[{self.id}] Image folder {image_folder} does not exist.")
            return
        # Check if the image folder is empty
        if not os.listdir(image_folder):
            logger.error(f"[{self.id}] Image folder {image_folder} is empty.")
            return

        # Sync the image folder
        try:
            subprocess.run(["rsync", "-av", image_folder, self.ud_mount_loc])
            logger.info(f"[{self.id}] Synced image folder to {self.ud_mount_loc}.")
        except Exception as e:
            logger.error(f"[{self.id}] Error syncing image folder: {e}")
            return

        # Unmount the UD drive
        time.sleep(0.1)
        self.reset()
    
    def flush_message_queue(self):
        """
        Flushes the message queue.
        """
        while not self.message_queue.empty():
            try:
                self.message_queue.get_nowait()
            except queue.Empty:
                break
    
    def _attempt_reopen(self):
        """
        Attempts to reopen the serial port.
        """
        logger.info(f"[{self.id}] Attempting to reinitialize the port {self.port}...")

        try:
            if self.ser:
                # Flush input and output buffers
                self.ser.reset_input_buffer()
                self.ser.reset_output_buffer()
                self.ser.close()
            # Reopen the serial connection
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)

            logger.info(f"[{self.id}] Reinitialized port {self.port} successfully.")
        except Exception as e:
            logger.error(f"[{self.id}] Failed to reinitialize port: {e}")
            self.stop_read_thread()
            time.sleep(1)
    
    def stop(self):
        """
        Stops the read thread and closes the serial port.
        """
        self.stop_flag.set()
        if self.ser and self.ser.is_open:
            self.ser.close()
            logger.info(f"[{self.id}] Closed port {self.port}.")
        logger.info(f"[{self.id}] Stopped.")
        self.mode = M0Mode.PORT_OPEN

# Test the M0Device class
if __name__ == "__main__":
    m0 = M0Device(id="M0_0", reset_pin=6)
    m0.find_device()
    # m0.mount_ud()
    # m0.sync_image_folder()
    # m0.upload_sketch()
    m0.open_serial()
    m0.start_read_thread()
    time.sleep(2)
    m0.send_command("WHOAREYOU?")
    time.sleep(5)
    logger.info("M0 device test complete.")