# M0Device is a class that represents one M0 board with a persistent serial connection.
#
# Gelareh Modara
# Manu Madhav
# 2025

import pigpio
import time
import subprocess
import threading
import queue
import serial
from helpers import wait_for_dmesg
from enum import Enum
import os

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

    def __init__(self, pi=None, id=None, reset_pin=None,
                 port=None, baudrate=115200, location=None):
        
        if pi is None:
            self.pi = pigpio.pi()
        else:
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

        self.mode = M0Mode.UNINITIALIZED
    
    def __del__(self):
        self.stop()
    
    def stop(self):
        """
        Stops the read thread and closes the serial port.
        """
        self.stop_flag.set()
        if self.ser and self.ser.is_open:
            self.ser.close()
            print(f"[{self.id}] Closed port {self.port}.")
        print(f"[{self.id}] Stopped.")
        self.mode = M0Mode.UNINITIALIZED

    def initialize(self):
        self.find_device()
        time.sleep(1)
        self.open_serial()
        time.sleep(1)
        self.start_read_thread()
        time.sleep(1)
        self.send_command("WHOAREYOU?")
    
    def find_device(self):
        """
        Finds the port and device ID of the M0 board connected to the given reset pin.
        """
        print(f"Finding M0 board on pin {self.reset_pin}.")
        try:
            self.reset()
            time.sleep(1)

            # Wait for the device to be detected
            tty_line = wait_for_dmesg("ttyACM")

            if tty_line:
                self.port = "/dev/ttyACM" + tty_line.split("ttyACM")[1].split(":")[0]

                print(f"Found device on port /dev/ttyACM{self.port}")

                self.mode = M0Mode.PORT_CLOSED
            else:
                print(f"[{self.id}] Error: No ttyACM device found.")
        except Exception as e:
            print(f"[{self.id}] Error finding device: {e}")
    
    def open_serial(self):
        """
        Opens the serial port.
        """
        if self.port is None:
            print(f"[{self.id}] Port not found. Finding device...")
            self.find_device()
        
        if not self.mode == M0Mode.PORT_CLOSED:
            print(f"[{self.id}] Port not closed; cannot open serial port.")
            return

        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=5)
            print(f"[{self.id}] Opened port {self.port} at {self.baudrate}.")
            self.mode = M0Mode.PORT_OPEN
        except Exception as e:
            print(f"[{self.id}] Failed to open {self.port}: {e}")
    
    def start_read_thread(self):
        """
        Starts the read thread.
        """
        if not self.mode == M0Mode.PORT_OPEN:
            print(f"[{self.id}] Port not open; cannot start read thread.")
            return
        if self.ser is None:
            print(f"[{self.id}] Serial port not initialized; cannot start read thread.")
            return
        
        self.thread = threading.Thread(target=self.read_loop, daemon=True)
        self.thread.start()
        self.mode = M0Mode.SERIAL_COMM
    
    def read_loop(self):
        print(f"[{self.id}] read_loop started.")
        while not self.stop_flag.is_set():
            try:
                if self.ser and self.ser.is_open:
                    line = self.ser.readline().decode("utf-8", errors="ignore").strip()
                    if line:
                        print(f"[{self.id}] <- {line}")
                        self.message_queue.put((self.id, line))
                else:
                    time.sleep(0.5)
            except Exception as e:
                print(f"[{self.id}] read_loop error: {e}")
                # re-open self.ser here
                self._attempt_reopen()
        print(f"[{self.id}] read_loop ending.")
    
    def stop_read_thread(self):
        """
        Stops the read thread.
        """
        if not self.mode == M0Mode.SERIAL_COMM:
            print(f"[{self.id}] Port not in serial communication mode; cannot stop read thread.")
            return
        
        print(f"[{self.id}] Stopping read thread.")
        self.stop_flag.set()
        self.mode = M0Mode.PORT_OPEN
    
    def send_command(self, cmd):
        """
        Sends 'cmd' + newline to the M0 board. Thread-safe via self.write_lock.
        """
        
        if not self.mode == M0Mode.SERIAL_COMM:
            print(f"[{self.id}] Port not in serial communication mode; cannot send command.")
            return

        with self.write_lock:
            try:
                msg = (cmd + "\n").encode("utf-8")
                self.ser.reset_input_buffer()
                self.ser.reset_output_buffer()
                self.ser.write(msg)
                print(f"[{self.id}] -> {cmd}")
            except Exception as e:
                print(f"[{self.id}] Error writing '{cmd}': {e}")
    
    def reset(self):
        print(f"Resetting M0 board on pin {self.reset_pin}.")

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
            print(f"[{self.id}] Error resetting M0 board: {e}")
    
    def mount_ud(self):
        """
        Mounts the UD drive connected to the M0 board by double clicking the reset pin.
        Currently this assumes only one UD drive is mounted at a time.
        """
        print(f"[{self.id}] Mounting UD drive on pin {self.reset_pin}.")

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
                        print(f"Found mount location: {self.ud_mount_loc}")
                        waiting = False
            
            self.mode = M0Mode.UD
        
        except Exception as e:
            print(f"[{self.id}] Error mounting UD drive: {e}")
    
    def upload_sketch(self, sketch_path="../M0Touch/M0Touch.ino"):
        """
        Uploads the given sketch to the M0 board.
        """

        if self.mode == M0Mode.SERIAL_COMM:
            self.stop_read_thread()
        
        if self.mode == M0Mode.UD or self.port is None:
            self.find_device()

        print(f"[{self.id}] Uploading sketch to {self.port}.")
        try:
            # Run arduino-cli upload
            upload = subprocess.check_output(f"arduino-cli upload --port {self.port} --fqbn DFRobot:samd:mzero_bl {sketch_path}", shell=True).decode("utf-8")
            print(upload)

            print(f"[{self.id}] Sketch uploaded successfully.")
            self.mode = M0Mode.PORT_CLOSED
        except Exception as e:
            print(f"[{self.id}] Error uploading sketch: {e}")
    
    def sync_image_folder(self, image_folder="../data/images"):
        """
        Syncs the image folder to the UD drive connected to the M0 board.
        """
        print(f"Syncing image folder to UD drive.")

        # Mount the UD drive
        self.mount_ud()

        if not self.mode == M0Mode.UD:
            print(f"[{self.id}] Port not in UD mode; cannot sync image folder.")
            return
        if self.ud_mount_loc is None:
            print(f"[{self.id}] UD mount location not found; cannot sync image folder.")
            return
        # Check if the image folder exists
        if not os.path.exists(image_folder):
            print(f"[{self.id}] Image folder {image_folder} does not exist.")
            return
        # Check if the image folder is empty
        if not os.listdir(image_folder):
            print(f"[{self.id}] Image folder {image_folder} is empty.")
            return

        # Sync the image folder
        try:
            subprocess.run(["rsync", "-av", image_folder, self.ud_mount_loc])
            print("Synced image folder.")
        except Exception as e:
            print(f"Error syncing image folder: {e}")
            return

        # Unmount the UD drive
        time.sleep(0.1)
        self.reset()
    
    def _attempt_reopen(self):
        """
        Attempts to reopen the serial port.
        """
        print(f"[{self.id}] Attempting to reinitialize the port {self.port}...")

        try:
            if self.ser:
                # Flush input and output buffers
                self.ser.reset_input_buffer()
                self.ser.reset_output_buffer()
                self.ser.close()
            # Reopen the serial connection
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)

            print(f"[{self.id}] Reinitialized port {self.port} successfully.")
        except Exception as e:
            print(f"[{self.id}] Failed to reinitialize port: {e}")
            self.stop_read_thread()
            time.sleep(1)
    
    def stop(self):
        """
        Stops the read thread and closes the serial port.
        """
        self.stop_flag.set()
        if self.ser and self.ser.is_open:
            self.ser.close()
            print(f"[{self.id}] Closed port {self.port}.")
        print(f"[{self.id}] Stopped.")
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
    print("M0 device test complete.")
    input("Press Enter to exit.")
    print("M0 device stopped.")