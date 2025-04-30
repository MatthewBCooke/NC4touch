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
    
if __name__ == "__main__":
    tui = TUI()

    # Create ncurses window
    import curses
    stdscr = curses.initscr()
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)
    stdscr.clear()
    stdscr.refresh()

    try:
        while True:
            lineIdx = 0
            
            # Option dictionary
            options = {
                "Discover M0s": tui.session_controller.discover_m0s,
                "Start Recording": tui.start_recording,
                "Stop Recording": tui.stop_recording,
                "Start Training": tui.start_training,
                "Stop Training": tui.stop_training,
                "Start Priming": tui.start_priming,
                "Stop Priming": tui.stop_priming,
                "Set Rodent ID": lambda: tui.rodent_name,
                "Set Phase Name": lambda: tui.phase_name,
                "Set ITI Duration": lambda: tui.iti_duration,
                "Set CSV File": lambda: tui.csv_file,
                "Exit": exit
            }

            stdscr.clear()
            stdscr.addstr(lineIdx, 0, "TUI Menu")
            lineIdx += 1
            stdscr.addstr(lineIdx, 0, "----------------")

            for i, option in enumerate(options.keys()):
                stdscr.addstr(lineIdx + i, 0, f"{i + 1}. {option}")

            key = stdscr.getch()

            success = False
            for i, option in enumerate(options.keys()):
                if key == ord(str(i + 1)):
                    stdscr.addstr(8, 0, f"Selected: {option}")
                    stdscr.refresh()
                    options[option]()
                    success = True
                    time.sleep(1)
            
            if not success:
                stdscr.addstr(8, 0, "Invalid option. Please try again.")
                stdscr.refresh()
                time.sleep(1)
    finally:
        curses.nocbreak()
        stdscr.keypad(False)
        curses.echo()
        curses.endwin()
        print("Exiting TUI.")