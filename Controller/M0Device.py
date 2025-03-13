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

class M0Device:
    """
    Represents one M0 board with a persistent serial connection.
    """

    def __init__(self, pi=None, id=None, reset_pin=None,
                 port=None, serial_number = None, 
                 baudrate=115200, location=None):
        
        if pi is None:
            self.pi = pigpio.pi()
        else:
            self.pi = pi

        self.id = id
        self.reset_pin = reset_pin
        self.port= port
        self.serial_number = serial_number
        self.baudrate = baudrate
        self.location = location

        self.ser = None
        self.ud_mount_loc = None

        self.stop_flag = threading.Event()
        self.message_queue = queue.Queue()  # to store lines: (id, text)

        self.write_lock = threading.Lock()
    
    def open_serial(self):
        """
        Opens the serial port.
        """
        if self.port is None:
            print("No port found. Finding device...")
            self.find_device()

        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            print(f"[{self.id}] Opened port {self.port} at {self.baudrate}.")
        except Exception as e:
            print(f"[{self.id}] Failed to open {self.port}: {e}")
    
    def start_read_thread(self):
        """
        Starts the read thread.
        """
        self.thread = threading.Thread(target=self.read_loop, daemon=True)
        self.thread.start()
    
    def read_loop(self):
        print(f"[{self.id}] read_loop started.")
        while not self.stop_flag.is_set():
            time.sleep(0.1)
            try:
                if self.ser and self.ser.is_open:
                    line = self.ser.readline().decode("utf-8", errors="ignore").strip()
                    if line:
                        self.message_queue.put((self.id, line))
                        print(f"[{self.id}] <- {line}")
                else:
                    print(f"[{self.id}] Serial port not open.")
            except Exception as e:
                print(f"[{self.id}] Error reading serial port: {e}")
        
        print(f"[{self.id}] read_loop stopped.")
    
    def send_command(self, cmd):
        """
        Sends 'cmd' + newline to the M0 board. Thread-safe via self.write_lock.
        """
        if not self.ser or not self.ser.is_open:
            print(f"[{self.id}] Port not open; cannot send command.")
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
        except Exception as e:
            print(f"Error resetting M0 board: {e}")
    
    def mount_ud(self):
        """
        Mounts the UD drive connected to the M0 board by double clicking the reset pin.
        Currently this assumes only one UD drive is mounted at a time.
        """
        print(f"Mounting UD drive on pin {self.reset_pin}.")
        try:
            self.reset()
            time.sleep(0.1)
            self.reset()
            
            start_time = time.localtime()
            waiting = True
            while waiting:
                time.sleep(0.5)
                print(f"Waiting for disk...")

                dmesg = subprocess.check_output("dmesg -T", shell=True).decode("utf-8")
                dmesg = dmesg.split("\n")[:-2]

                timestamps = [line.split("]")[0][1:] for line in dmesg]
                timestamps = [time.strptime(ts, "%a %b %d %H:%M:%S %Y") for ts in timestamps]

                # Filter for timestamps after start time
                dmesg = [line for line, ts in zip(dmesg, timestamps) if ts > start_time]

                if dmesg:
                    sd_line = [line for line in dmesg if "FireBeetle-UDisk" in line]
                    if sd_line:
                        waiting = False

            
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
        
        except Exception as e:
            print(f"Error mounting UD drive: {e}")
    
    def upload_sketch(self, sketch_path="../M0Touch/M0Touch.ino"):
        """
        Uploads the given sketch to the M0 board.
        """
        if self.port is None:
            print("No port found. Finding device...")
            self.find_device()

        print(f"Uploading sketch to {self.port}.")
        try:
            # Run arduino-cli upload
            upload = subprocess.check_output(f"arduino-cli upload --port {self.port} --fqbn DFRobot:samd:mzero_bl {sketch_path}", shell=True).decode("utf-8")
            print(upload)
        except Exception as e:
            print(f"Error uploading sketch to {self.port}: {e}")
    
    def sync_image_folder(self, image_folder="../data/images"):
        """
        Syncs the image folder to the UD drive connected to the M0 board.
        """
        print(f"Syncing image folder to UD drive.")

        # Mount the UD drive
        self.mount_ud()

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
    
    def find_device(self):
        """
        Finds the port and device ID of the M0 board connected to the given reset pin.
        """
        print(f"Finding M0 board on pin {self.reset_pin}.")
        try:
            self.reset()
            time.sleep(1)

            # Record current time
            start_time = time.localtime()

            # Wait for the device to be detected
            # Check the dmesg log for messages after the start time
            waiting = True
            while waiting:
                dmesg = subprocess.check_output("dmesg -T | tail", shell=True).decode("utf-8")
                dmesg = dmesg.split("\n") # Get the latest message

                # Starts with timestamp, e.g. [Wed Mar 12 15:29:35 2025]
                timestamp = dmesg[-2].split("]")[0][1:] # Last timestamp
                print(f"{timestamp}: Waiting for device...")
                # Convert to time struct
                timestamp = time.strptime(timestamp, "%a %b %d %H:%M:%S %Y")
                if timestamp > start_time:
                    waiting = False
                time.sleep(0.5)

            # Check dmesg for the device ID
            dmesg = subprocess.check_output("dmesg | tail", shell=True).decode("utf-8")
            dmesg = dmesg.split("\n")[::-1] # Reverse the list to get the latest messages first

            serial_number_line = [line for line in dmesg if "SerialNumber:" in line][0]
            port_line = [line for line in dmesg if "ttyACM" in line][0]

            if "SerialNumber:" in serial_number_line and "ttyACM" in port_line:
                self.serial_number = serial_number_line.split("SerialNumber: ")[1]
                self.port = "/dev/ttyACM" + port_line.split("ttyACM")[1].split(":")[0]

                print(f"Found device ID: {self.serial_number} on port /dev/ttyACM{self.port}")
            else:
                print("Error finding device ID.")
        except Exception as e:
            print(f"Error finding device ID: {e}")
    
    def stop(self):
        """
        Stops the read thread and closes the serial port.
        """
        self.stop_flag.set()
        if self.ser and self.ser.is_open:
            self.ser.close()
            print(f"[{self.id}] Closed port {self.port}.")
        print(f"[{self.id}] Stopped.")

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