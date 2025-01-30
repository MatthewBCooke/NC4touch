"""
    1) discover_m0_boards() to find /dev/ttyACM* boards.
    2) M0ListenerThread: A thread that keeps one open serial connection
       to an M0 device & reads lines in real time.
"""
import time
import serial
import serial.tools.list_ports
import threading
import queue


def discover_m0_boards():
    board_map = {}
    ports = serial.tools.list_ports.comports()

    for p in ports:
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


class M0ListenerThread(threading.Thread):
    def __init__(self, m0_id, port, stop_flag, message_queue):
        super().__init__()
        self.m0_id = m0_id
        self.port = port
        self.stop_flag = stop_flag
        self.message_queue = message_queue

        self.ser = None
        self.lock = threading.Lock()  

    def run(self):
        print(f"Listener thread started on {self.m0_id} ({self.port})")
        try:
            self.ser = serial.Serial(self.port, 115200, timeout=1)
            while not self.stop_flag.is_set():
                line = self.ser.readline().decode("utf-8", errors="ignore").strip()
                if line:
                    self.message_queue.put((self.m0_id, line))
        except Exception as e:
            print(f"Listener error on {self.port}: {e}")
        finally:
            if self.ser and self.ser.is_open:
                self.ser.close()

        print(f"Listener thread stopped on {self.m0_id}")

    def send_command(self, cmd):
        if not self.ser or not self.ser.is_open:

            return
        with self.lock:
            msg = (cmd + "\n").encode("utf-8")
            self.ser.write(msg)
            self.ser.flush()
            print(f"[{self.port}] -> {cmd}")