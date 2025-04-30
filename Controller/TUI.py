import time
from SessionController import SessionController
import curses
import os

class TUI:
    def __init__(self):
        # Counters for tracking progress
        self.correct_count = 0
        self.incorrect_count = 0
        self.notouch_count = 0
        self.trial_count = 0

        self.session_controller = SessionController()
        self.config = self.session_controller.config
        self.camera = None
        self.trainer = None
        self.is_recording = False
        self.rodent_names = []

        # Setup camera
        self.session_controller.setup_camera(camera_device="/dev/video0", mode="video_capture")
        self.camera = self.session_controller.camera
        self.camera.initialize_network_stream()
        self.is_recording = False

        self.phase_name = None
        self.rodent_name = None
        self.iti_duration = None
        self.csv_file = None

        self.stdscr = None
        self.run_loop = True
        self.lineIdx = 0

    def start_recording(self):
        if not self.is_recording:
            self.session_controller.start_recording()
            self.is_recording = True
            print("Recording started.")
        else:
            print("Recording is already in progress.")

    def stop_recording(self):
        if self.is_recording:
            self.session_controller.stop_recording()
            self.is_recording = False
            print("Recording stopped.")
        else:
            print("No recording in progress to stop.")

    def start_training(self):
        self.trainer = self.session_controller.trainer
        if not self.trainer:
            print("Trainer not initialized.")
            return
        if not self.rodent_name:
            print("Rodent ID not set.")
            return
        
        self.trainer.current_phase = self.phase_name
        self.trainer.iti_duration = self.iti_duration
        self.trainer.rodent_id = self.rodent_name
        self.trainer.trial_data = []
        self.session_start_time = time.time()

        print(f"Starting phase: {self.phase_name}, rodent={self.rodent_name}")
        if self.phase_name == "Habituation":
            self.trainer.Habituation()
        elif self.phase_name == "Initial Touch":
            self.trainer.initial_touch_phase(self.csv_file)
        elif self.phase_name == "Must Touch":
            self.trainer.must_touch_phase(self.csv_file)
        elif self.phase_name == "Must Initiate":
            self.trainer.must_initiate_phase(self.csv_file)
        elif self.phase_name == "Punish Incorrect":
            self.trainer.punish_incorrect_phase(self.csv_file)
        elif self.phase_name == "Simple Discrimination":
            self.trainer.simple_discrimination_phase(self.csv_file)
        elif self.phase_name == "Complex Discrimination":
            self.trainer.complex_discrimination_phase(self.csv_file)
        print("Phase run finished.")

    def stop_training(self):
        if self.trainer:
            self.trainer.stop_session()
            print("Training stopped.")
        else:
            print("No training session to stop.")
    
    def start_priming(self):
        if not self.trainer or 'reward' not in self.trainer.peripherals:
            print("No trainer or reward object to prime.")
            return
        print("Starting to prime feeding tube.")
        self.trainer.peripherals['reward'].prime_feeding_tube()

    def stop_priming(self):
        if not self.trainer or 'reward' not in self.trainer.peripherals:
            print("No trainer or reward object to stop priming.")
            return
        print("Stopping priming.")
        self.trainer.peripherals['reward'].stop_priming()
    
    def tui_init(self):
        # Create ncurses window
        self.stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        self.stdscr.keypad(True)
        self.stdscr.clear()
        self.stdscr.refresh()
    
    def tui_set_rodent_name(self):
        self.stdscr.clear()
        self.stdscr.addstr(0, 0, "Enter Rodent name: ")
        self.stdscr.refresh()
        rodent_name = self.stdscr.getstr(1, 0).decode("utf-8")
        if rodent_name:
            self.rodent_name = rodent_name
            print(f"Rodent name set to: {self.rodent_name}")
        else:
            print("No Rodent name entered.")
    
    def tui_set_phase_name(self):
        self.stdscr.clear()
        self.stdscr.addstr(0, 0, "Enter Phase name: ")
        self.stdscr.refresh()
        phase_name = self.stdscr.getstr(1, 0).decode("utf-8")
        if phase_name:
            self.phase_name = phase_name
            print(f"Phase name set to: {self.phase_name}")
        else:
            print("No Phase name entered.")
    
    def tui_set_iti_duration(self):
        self.stdscr.clear()
        self.stdscr.addstr(0, 0, "Enter ITI Duration (seconds): ")
        self.stdscr.refresh()
        iti_duration = self.stdscr.getstr(1, 0).decode("utf-8")
        if iti_duration.isdigit():
            self.iti_duration = int(iti_duration)
            print(f"ITI Duration set to: {self.iti_duration} seconds")
        else:
            print("Invalid ITI Duration entered.")
    
    def tui_set_csv_file(self):
        self.stdscr.clear()
        self.stdscr.addstr(0, 0, "Enter CSV file path: ")
        self.stdscr.refresh()
        csv_file = self.stdscr.getstr(1, 0).decode("utf-8")
        if os.path.isfile(csv_file):
            self.csv_file = csv_file
            print(f"CSV file set to: {self.csv_file}")
        else:
            print("Invalid CSV file path entered.")
    
    def tui_exit(self):
        self.stdscr.addstr(0, 0, "Exiting TUI...")
        self.stdscr.refresh()
        time.sleep(1)
        curses.nocbreak()
        self.stdscr.keypad(False)
        curses.echo()
        curses.endwin()
        print("TUI exited.")
        self.run_loop = False
    
    def tui_show_menu(self):
        self.lineIdx = 0
        # Option dictionary
        options = {
            "Discover M0s": self.session_controller.discover_m0s,
            "Start Recording": self.start_recording,
            "Stop Recording": self.stop_recording,
            "Start Training": self.start_training,
            "Stop Training": self.stop_training,
            "Start Priming": self.start_priming,
            "Stop Priming": self.stop_priming,
            f"Set Rodent Name ({self.rodent_name})": self.tui_set_rodent_name,
            f"Set Phase Name ({self.phase_name})": self.tui_set_phase_name,
            f"Set ITI Duration ({self.iti_duration})": self.tui_set_iti_duration,
            f"Set CSV File ({self.csv_file})": self.tui_set_csv_file,
            "Exit": exit,
        }

        self.stdscr.clear()
        self.stdscr.addstr(self.lineIdx, 0, "TUI Menu")
        self.lineIdx += 1
        self.stdscr.addstr(self.lineIdx, 0, "----------------")
        self.lineIdx += 1

        for i, option in enumerate(options.keys()):
            self.stdscr.addstr(self.lineIdx + i, 0, f"{i + 1}. {option}")

        key = self.stdscr.getstr(0, 0).decode("utf-8")

        success = False
        for i, option in enumerate(options.keys()):
            if key == str(i + 1):
                self.stdscr.addstr(8, 0, f"Selected: {option}")
                self.stdscr.refresh()
                options[option]()
                success = True
                time.sleep(1)
        
        if not success:
            self.stdscr.addstr(self.lineIdx + len(options), 0, "Invalid option. Please try again.")
            self.stdscr.refresh()
            time.sleep(1)


    
if __name__ == "__main__":
    tui = TUI()
    tui.tui_init()
    try:
        while tui.run_loop:
            tui.tui_show_menu()
    except KeyboardInterrupt:
        tui.tui_exit()
    finally:
        tui.tui_exit()

