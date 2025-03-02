#!/usr/bin/env python3

"""
m0_devices.py
1) discover_m0_boards() to find M0s by sending WHOAREYOU?
2) M0Device class to handle each M0's serial port in a thread,
   allowing send_command(...) and continuous read of lines.
"""

import time
import threading
import queue
import serial
import serial.tools.list_ports
import pigpio
import subprocess

def discover_m0_boards():
    """
    Searches /dev/ttyACM*, /dev/ttyUSB* for boards that respond with "ID:M0_x"
    when we send "WHOAREYOU?".
    Returns a dict like {"M0_0": "/dev/ttyACM0", "M0_1": "/dev/ttyACM1"}.
    """
    board_map = {}
    ports = serial.tools.list_ports.comports()

    for p in ports:
        # Check if it's an ACM or USB device
        if "ACM" in p.device or "USB" in p.device:
            try:
                with serial.Serial(p.device, 115200, timeout=1) as ser:
                    time.sleep(0.3)
                    ser.write(b"WHOAREYOU?\n")
                    line = ser.readline().decode("utf-8", errors="ignore").strip()
                    if line.startswith("ID:"):
                        board_id = line.split(":", 1)[1]
                        board_map[board_id] = p.device
                        print(f"Discovered {board_id} on {p.device}")
            except Exception as e:
                print(f"Could not open {p.device}: {e}")

    return board_map


class M0Device:
    """
    Represents one M0 board with a persistent serial connection.
    - Opens the serial port once (in __init__).
    - Spawns a background thread to continuously read lines, placing them
      into message_queue as (m0_id, line).
    - Provides send_command(cmd) for writing commands thread-safely.
    - Provides stop() to end the read thread and close the port.
    """

    def __init__(self, m0_id, port_path, reset_pin, baudrate=115200):
        """
        m0_id    : e.g. "M0_0"
        port_path: e.g. "/dev/ttyACM0"
        baudrate : default 115200
        """
        self.pi = pigpio.pi()
        self.m0_id = m0_id
        self.port_path = port_path
        self.reset_pin = reset_pin
        self.baudrate = baudrate

        self.pi.set_mode(self.reset_pin, pigpio.OUTPUT)
        self.reset()  # Reset the M0 board

        self.ser = None
        self.stop_flag = threading.Event()
        self.message_queue = queue.Queue()  # to store lines: (m0_id, text)

        self.write_lock = threading.Lock()

        # Attempt to open the port
        try:
            self.ser = serial.Serial(self.port_path, self.baudrate, timeout=1)
            print(f"[{self.m0_id}] Opened port {self.port_path} at {self.baudrate}.")
        except Exception as e:
            print(f"[{self.m0_id}] Failed to open {self.port_path}: {e}")

        # Start read thread
        self.thread = threading.Thread(target=self.read_loop, daemon=True)
        self.thread.start()
    
    def mountUD(self):
        """
        Mounts the UD drive connected to the M0 board by double clicking the reset pin.
        """
        print(f"[{self.m0_id}] Mounting UD drive.")
        try:
            self.reset()
            time.sleep(0.1)
            self.reset()
        except Exception as e:
            print(f"[{self.m0_id}] Error mounting UD drive: {e}")
    
    def reset(self):
        """
        Resets the M0 board by toggling the reset pin.
        """
        # print(f"[{self.m0_id}] Resetting M0 board.")
        try:
            self.pi.write(self.reset_pin, 0)
            time.sleep(0.1)
            self.pi.write(self.reset_pin, 1)
        except Exception as e:
            print(f"[{self.m0_id}] Error resetting M0 board: {e}")
    
    def sync_image_folder(self):
        """
        Syncs the image folder (../data/images) to the UD drive.
        """
        print(f"[{self.m0_id}] Syncing image folder.")

        # Mount the UD drive
        self.mountUD()
        time.sleep(6)
        # Find the mount location from lsblk
        try:
            lsblk = subprocess.check_output("lsblk", shell=True).decode("utf-8")
            mount_loc = "/media/" + lsblk.split("/media/")[1].split("\n")[0]
            print(f"[{self.m0_id}] Found mount location: {mount_loc}")
        except Exception as e:
            print(f"[{self.m0_id}] Error finding mount location: {e}")
            return

        # Sync the image folder
        try:
            subprocess.run(["rsync", "-av", "../data/images/", mount_loc])
            print(f"[{self.m0_id}] Synced image folder.")
        except Exception as e:
            print(f"[{self.m0_id}] Error syncing image folder: {e}")
            return

        # Unmount the UD drive
        self.reset()                

    def read_loop(self):
        print(f"[{self.m0_id}] read_loop started.")
        while not self.stop_flag.is_set():
            try:
                if self.ser and self.ser.is_open:
                    line = self.ser.readline().decode("utf-8", errors="ignore").strip()
                    if line:
                        self.message_queue.put((self.m0_id, line))
                else:
                    time.sleep(0.5)
            except Exception as e:
                print(f"[{self.m0_id}] read_loop error: {e}")
                # re-open self.ser here
                self._attempt_reopen()
        print(f"[{self.m0_id}] read_loop ending.")



    def send_command(self, cmd):
        """
        Sends 'cmd' + newline to the M0 board. Thread-safe via self.write_lock.
        """
        if not self.ser or not self.ser.is_open:
            print(f"[{self.m0_id}] Port not open; cannot send command.")
            return

        with self.write_lock:
            try:
                msg = (cmd + "\n").encode("utf-8")
                self.ser.write(msg)
                self.ser.flush()
                print(f"[{self.m0_id}] -> {cmd}")
            except Exception as e:
                print(f"[{self.m0_id}] Error writing '{cmd}': {e}")

    def stop(self):
        """
        Signals the thread to stop, closes the port, waits for thread to finish.
        """
        print(f"[{self.m0_id}] stop() called.")
        self.stop_flag.set()
        self.thread.join(timeout=2.0)

        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except Exception as e:
                print(f"[{self.m0_id}] Error closing port: {e}")

        print(f"[{self.m0_id}] Stopped.")