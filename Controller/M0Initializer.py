#! /usr/bin/env python3

import pigpio
import time
import subprocess
import os
import argparse

class M0Initializer:
    reset_pins = [6, 5, 25] # GPIO pins for reset

    def __init__(self):
        self.pi = pigpio.pi()
        for pin in self.reset_pins:
            self.pi.set_mode(pin, pigpio.OUTPUT)
        
        self.board_ports = []

    def reset_m0(self, reset_pin):
        print(f"Resetting M0 board on pin {reset_pin}.")
        try:
            self.pi.write(reset_pin, 0)
            time.sleep(0.1)
            self.pi.write(reset_pin, 1)
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
    
    def detect_all_m0s(self):
        """
        Detects the M0 boards connected to the system.
        """
        # Reset all M0 boards
        self.reset_all_m0s()
        time.sleep(0.1)
        print("Detecting M0 boards.")
        try:
            # Run arduino-cli board list
            boards = subprocess.check_output("arduino-cli board list", shell=True).decode("utf-8")
            print(boards)

            """
            Output format:
            Port         Protocol Type              Board Name FQBN Core
            /dev/ttyACM0 serial   Serial Port (USB) Unknown
            /dev/ttyACM1 serial   Serial Port (USB) Unknown
            /dev/ttyACM2 serial   Serial Port (USB) Unknown
            """

            # Parse the output
            self.board_ports = []
            for line in boards.split("\n"):
                if "serial" in line:
                    self.board_ports.append(line.split()[0])
            
        except Exception as e:
            print(f"Error detecting M0 boards: {e}")
            return []
    
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
        for port in m0_init.board_ports:
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
                for port in m0_init.board_ports:
                    m0_init.upload_to_port(port, sketch_path)
            elif choice == "4":
                m0_init.sync_all_image_folders()
            elif choice == "5":
                break
            else:
                print("Invalid choice.")
            print()