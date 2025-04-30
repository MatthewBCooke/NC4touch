import os
import time
import pigpio
import yaml
import csv

# Local modules
import m0_devices       # discover_m0_boards()
import Main             # The MultiPhaseTraining code
from LED import LED
from Reward import Reward
from BeamBreak import BeamBreak
from Buzzer import Buzzer
from Camera import Camera

class Session:
    def __init__(self):
        # pigpio/peripherals/trainer
        self.pi = None
        self.peripherals = None
        self.trainer = None

        # Video Recording
        self.video_capture = None
        self.video_timer = None
        self.is_recording = False
        self.video_file_path = ""

        # Session Timer
        self.session_start_time = None

        # A list to store rodent names (history)
        self.rodent_names = []

        # Initialize pigpio and trainer
        self.init_hardware()

        # Initialize config file
        self.init_config_file()
    
    def start_recording(self, video_file_path):
        """
        Starts video recording and sets the file path for the recorded video.
        """
        self.video_file_path = video_file_path
        self.is_recording = True
        print(f"Recording started. Video will be saved to {self.video_file_path}.")
        return self.camera.video_recorder.start_recording(self.video_file_path)
    
    def stop_recording(self):
        """
        Stops video recording.
        """
        if self.is_recording:
            self.is_recording = False
            print("Recording stopped.")
            return self.camera.video_recorder.stop_recording()
        else:
            print("No recording in progress.")
            return False

    def init_config_file(self):
        code_dir = os.path.dirname(os.path.realpath(__file__))
        self.config_file = os.path.join(code_dir, 'config.yaml')
        if os.path.isfile(self.config_file):
            with open(self.config_file, 'r') as file:
                self.config = yaml.safe_load(file)
        else:
            self.config = {}
    
    def load_from_config(self, key):
        if key in self.config:
            return self.config[key]
        else:
            print(f"Key '{key}' not found in config.")
            return ""
            return None
    
    def save_to_config(self, key, value):
        self.config[key] = value
        self.write_config_file()

    def write_config_file(self):
        with open(self.config_file, 'w') as f:
            yaml.dump(self.config, f)

    # ---------------- Hardware/Trainer Init ----------------
    def init_hardware(self):
        self.pi = pigpio.pi()
        if not self.pi.connected:
            print("Failed to connect to pigpio!")
            return

        Reward_LED_PIN = 21
        Reward_PIN = 27
        BeamBreak_PIN = 4
        Punishment_LED_PIN = 17
        Buzzer_PIN = 16

        self.peripherals = {
            'reward_led': LED(self.pi, Reward_LED_PIN, brightness=140),
            'reward':     Reward(self.pi, Reward_PIN),
            'beam_break': BeamBreak(self.pi, BeamBreak_PIN),
            'punishment_led': LED(self.pi, Punishment_LED_PIN, brightness=255),
            'buzzer': Buzzer(self.pi, Buzzer_PIN)
        }
        # self.trainer = None
        #default_board_map = {"M0_0": "/dev/ttyACM0", "M0_1": "/dev/ttyACM1"}
        #self.trainer = Main.MultiPhaseTraining(self.pi, self.peripherals, default_board_map)
        #self.trainer.open_realtime_csv("FullSession")


    # ---------------- SESSION CONTROL ----------------
    def discover_m0s(self):
        boards = m0_devices.discover_m0_boards()
        if boards:
            print("Discovered boards:")
            for bid, dev in boards.items():
                print(f" - {bid} => {dev}")
            self.trainer = Main.MultiPhaseTraining(self.pi, self.peripherals, boards)
            print("Trainer updated with discovered boards.")
            self.trainer.open_realtime_csv("FullSession_ReDiscovered")
        else:
            print("No M0 boards found.")
    
    def setup_camera(self, camera_device="/dev/video0", mode="video_capture"):
        """
        Initializes the camera for video capture.
        """
        self.camera = Camera(camera_device=camera_device)

        if mode == "video_capture":
            self.camera.initialize_video_capture()
        elif mode == "network_stream":
            self.camera.initialize_network_stream()
        else:
            print("Invalid camera mode. Use 'video_capture' or 'network_stream'.")
            return
        print("Camera initialized successfully.")

        


