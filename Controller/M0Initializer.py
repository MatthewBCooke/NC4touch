#! /usr/bin/env python3

import pigpio
import time
import subprocess
import os
import argparse
import serial

class M0Initializer:
    reset_pins = [6] # GPIO pins for reset

    def __init__(self, pi=None):
        if pi is not None:
            self.pi = pi
        else:
            self.pi = pigpio.pi()

        for pin in self.reset_pins:
            self.pi.set_mode(pin, pigpio.INPUT)
        
        self.ports = [] # List of tty ports where M0 boards are connected
        self.device_map = {} # Map of device IDs to ports

    def reset_m0(self, reset_pin):
        print(f"Resetting M0 board on pin {reset_pin}.")
        try:
            # Need to only use GPIO reset pin as ouput during hardware reset
            # to avoid interference with the serial communication reset
            self.pi.set_mode(reset_pin, pigpio.OUTPUT)
            time.sleep(0.01)
            self.pi.write(reset_pin, 0)
            time.sleep(0.01)
            self.pi.write(reset_pin, 1)
            time.sleep(0.01)
            self.pi.set_mode(reset_pin, pigpio.INPUT)
        except Exception as e:
            print(f"Error resetting M0 board: {e}")
      
    def reset_all_m0s(self):
        print("Resetting all M0 boards.")
        for pin in self.reset_pins:
            self.reset_m0(pin)
            time.sleep(0.1)
    
    def mount_ud(self, reset_pin):
        """
        Mounts the UD drive connected to the M0 board by double clicking the reset pin.
        """
        print(f"Mounting UD drive on pin {reset_pin}.")
        try:
            self.reset_m0(reset_pin)
            time.sleep(0.1)
            self.reset_m0(reset_pin)
        except Exception as e:
            print(f"Error mounting UD drive: {e}")
    
    def mount_all_ud(self):
        print("Mounting all UD drives.")
        for pin in self.reset_pins:
            self.mount_ud(pin)
            time.sleep(6)
    
    def find_m0_device(self, reset_pin):
        """
        Finds the port and device ID of the M0 board connected to the given reset pin.
        """
        print(f"Finding M0 board on pin {reset_pin}.")
        try:
            # Mount the UD drive
            self.reset_m0(reset_pin)
            time.sleep(1)

            # Record current time
            start_time = time.localtime()

            # Wait for the device to be detected
            # Check the dmesg log for messages after the start time
            waiting = True
            while waiting:
                dmesg = subprocess.check_output("dmesg -T | tail", shell=True).decode("utf-8")
                dmesg = dmesg.split("\n")[-2] # Get the latest message
                # Starts with timestamp, e.g. [Wed Mar 12 15:29:35 2025]
                timestamp = dmesg.split("]")[0][1:]
                print(f"{timestamp}: Waiting for device...")
                # Convert to time struct
                timestamp = time.strptime(timestamp, "%a %b %d %H:%M:%S %Y")
                if timestamp > start_time:
                    waiting = False
                time.sleep(0.5)

            # Check dmesg for the device ID
            dmesg = subprocess.check_output("dmesg | tail", shell=True).decode("utf-8")
            dmesg = dmesg.split("\n")[::-1] # Reverse the list to get the latest messages first

            device_line = [line for line in dmesg if "SerialNumber:" in line][0]
            port_line = [line for line in dmesg if "ttyACM" in line][0]

            if "SerialNumber:" in device_line and "ttyACM" in port_line:
                device_id = device_line.split("SerialNumber: ")[1]
                port = port_line.split("ttyACM")[1].split(":")[0]

                print(f"Found device ID: {device_id} on port /dev/ttyACM{port}")
                return device_id, f"/dev/ttyACM{port}"
            else:
                print("Error finding device ID.")
                return None, None
        except Exception as e:
            print(f"Error finding device ID: {e}")
            return None, None
    
    def find_all_m0_devices(self):
        """
        Finds the ports and device IDs of all M0 boards connected to the system.
        """
        print("Finding all M0 boards.")
        self.device_map = {}
        for pin in self.reset_pins:
            device_id, port = self.find_m0_device(pin)
            if device_id is not None and port is not None:
                self.device_map[device_id] = port

    def upload_to_port(self, port, sketch_path):
        """
        Uploads the sketch to the M0 board connected to the given port.
        """
        print(f"Uploading sketch to {port}.")
        try:
            # Run arduino-cli board list
            upload = subprocess.check_output(f"arduino-cli upload --port {port} --fqbn DFRobot:samd:mzero_bl {sketch_path}", shell=True).decode("utf-8")
            print(upload)

        except Exception as e:
            print(f"Error uploading sketch to {port}: {e}")
    
    def sync_image_folder(self, reset_pin):
        """
        Syncs the image folder (../data/images) to the UD drive connected to the M0 board.
        """
        print(f"Syncing image folder to UD drive on pin {reset_pin}.")

        # Mount the UD drive
        self.mount_ud(reset_pin)
        time.sleep(6)
        # Find the mount location from lsblk
        try:
            lsblk = subprocess.check_output("lsblk", shell=True).decode("utf-8")
            mount_loc = "/media/" + lsblk.split("/media/")[1].split("\n")[0]
            print(f"Found mount location: {mount_loc}")
        except Exception as e:
            print(f"Error finding mount location: {e}")
            return

        # Sync the image folder
        try:
            subprocess.run(["rsync", "-av", "../data/images/", mount_loc])
            print("Synced image folder.")
        except Exception as e:
            print(f"Error syncing image folder: {e}")
            return

        # Unmount the UD drive
        self.reset_m0(reset_pin)
    
    def sync_all_image_folders(self):
        # Reset all M0 boards
        self.reset_all_m0s()
        time.sleep(0.1)
        print("Syncing image folders to all UD drives.")
        for pin in self.reset_pins:
            self.sync_image_folder(pin)
            time.sleep(6)
    
    def query_m0(self, port):
        """
        Queries the M0 board connected to the given port.
        """
        try:
            with serial.Serial(port, 115200, timeout=1) as ser:
                ser.reset_input_buffer()
                ser.reset_output_buffer()
                time.sleep(0.3)
                ser.write(b"WHOAREYOU?\n")
                line = ser.readline().decode("utf-8", errors="ignore").strip()
                print(f"Query response from {port}: {line}")
        except Exception as e:
            print(f"Error querying {port}: {e}")
    
    # def query_all_m0s(self):
    #     """
    #     Searches /dev/ttyACM*, /dev/ttyUSB* for boards that respond with "ID:M0_x"
    #     when we send "WHOAREYOU?".
    #     Returns a dict like {"M0_0": "/dev/ttyACM0", "M0_1": "/dev/ttyACM1"}.
    #     """
    #     for port in self.ports:
    #         time.sleep(0.3)
    #         self.query_m0(port)

        # board_map = {}
        # ports = serial.tools.list_ports.comports()

        # for p in ports:
        #     # Check if it's an ACM or USB device
        #     if "ACM" in p.device or "USB" in p.device:
        #         try:
        #             with serial.Serial(p.device, 115200, timeout=1) as ser:
        #                 time.sleep(0.3)
        #                 ser.write(b"WHOAREYOU?\n")
        #                 line = ser.readline().decode("utf-8", errors="ignore").strip()
        #                 if line.startswith("ID:"):
        #                     board_id = line.split(":", 1)[1]
        #                     board_map[board_id] = p.device
        #                     print(f"Discovered {board_id} on {p.device}")
        #         except Exception as e:
        #             print(f"Could not open {p.device}: {e}")

        # return board_map

if __name__ == "__main__":
    m0_init = M0Initializer()

    # parse arguments
    parser = argparse.ArgumentParser(description="M0 Initializer")
    parser.add_argument("-r", "--reset", action="store_true", help="Reset all M0 boards.")
    parser.add_argument("-d", "--detect", action="store_true", help="Detect all M0 boards.")
    parser.add_argument("-u", "--upload", action="store_true", help="Upload sketch to all M0 boards.")
    parser.add_argument("-s", "--sync", action="store_true", help="Sync image folders to all UD drives.")
    args = parser.parse_args()

    if args.reset:
        m0_init.reset_all_m0s()
    elif args.detect:
        m0_init.detect_all_m0s()
    elif args.upload:
        sketch_path = os.path.abspath("../M0Touch/M0Touch.ino")
        for port in m0_init.ports:
            m0_init.upload_to_port(port, sketch_path)
    elif args.sync:
        m0_init.sync_all_image_folders()
    else:
        # Show menu
        while True:
            print("********** M0 Initializer **********")
            print("1. Reset all M0 boards.")
            print("2. Detect all M0 boards.")
            print("3. Upload sketch to all M0 boards.")
            print("4. Sync image folders to all UD drives.")
            print("5. Exit.")
            choice = input("Enter choice: ")

            if choice == "1":
                m0_init.reset_all_m0s()
            elif choice == "2":
                m0_init.detect_all_m0s()
            elif choice == "3":
                sketch_path = os.path.abspath("../M0Touch/M0Touch.ino")
                for port in m0_init.ports:
                    m0_init.upload_to_port(port, sketch_path)
            elif choice == "4":
                m0_init.sync_all_image_folders()
            elif choice == "5":
                break
            else:
                print("Invalid choice.")
            print()