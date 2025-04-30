import time
from Controller.Session import Session
import curses
import os

class TUI:
    def __init__(self):
        # Counters for tracking progress
        self.correct_count = 0
        self.incorrect_count = 0
        self.notouch_count = 0
        self.trial_count = 0

        self.session = Session()
        self.camera = None
        self.trainer = None
        self.is_recording = False
        self.rodent_names = []

        # Setup camera
        self.session.setup_camera(camera_device="/dev/video0", mode="video_capture")
        self.session.camera.initialize_network_stream()
        self.is_recording = False

        self.phase_name = self.session.load_from_config("phase_name")
        self.rodent_name = self.session.load_from_config("rodent_name")
        self.iti_duration = self.session.load_from_config("iti_duration")
        self.seq_csv_dir = self.session.load_from_config("seq_csv_dir")
        self.seq_csv_file = self.session.load_from_config("seq_csv_file")
        self.data_csv_dir = self.session.load_from_config("data_csv_dir")

        self.stdscr = None
        self.run_loop = True
        self.lineIdx = 0

    def start_recording(self):
        if not self.is_recording:
            self.session.start_recording()
            self.is_recording = True
            print("Recording started.")
        else:
            print("Recording is already in progress.")

    def stop_recording(self):
        if self.is_recording:
            self.session.stop_recording()
            self.is_recording = False
            print("Recording stopped.")
        else:
            print("No recording in progress to stop.")

    def start_training(self):
        self.trainer = self.session.trainer
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
        csv_file = os.path.join(self.seq_csv_dir, self.seq_csv_file)

        print(f"Starting phase: {self.phase_name}, rodent={self.rodent_name}")
        if self.phase_name == "Habituation":
            self.trainer.Habituation()
        elif self.phase_name == "Initial Touch":
            self.trainer.initial_touch_phase(csv_file)
        elif self.phase_name == "Must Touch":
            self.trainer.must_touch_phase(csv_file)
        elif self.phase_name == "Must Initiate":
            self.trainer.must_initiate_phase(csv_file)
        elif self.phase_name == "Punish Incorrect":
            self.trainer.punish_incorrect_phase(csv_file)
        elif self.phase_name == "Simple Discrimination":
            self.trainer.simple_discrimination_phase(csv_file)
        elif self.phase_name == "Complex Discrimination":
            self.trainer.complex_discrimination_phase(csv_file)
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
    
    def export_data(self):
        if not self.trainer:
            print("No trainer to export data from.")
            return
        if not self.trainer.trial_data:
            print("No trial data to export.")
            return
        
        datetime_str = time.strftime("%Y%m%d_%H%M%S")
        csv_file = os.path.join(self.data_csv_dir, f"{datetime_str}_{self.rodent_name}_data.csv")
        self.trainer.export_results_csv(csv_file)
        print(f"Data exported to {csv_file}.")
    
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
            self.session.save_to_config("rodent_name", rodent_name)
        else:
            print("No Rodent name entered.")
    
    def tui_set_phase_name(self):
        phases = [
            "Habituation",
            "Initial Touch",
            "Must Touch",
            "Must Initiate",
            "Punish Incorrect",
            "Simple Discrimination",
            "Complex Discrimination"
        ]

        self.stdscr.clear()
        self.lineIdx = 0
        self.stdscr.addstr(self.lineIdx, 0, "Select Phase:")
        self.lineIdx += 1
        for i, phase in enumerate(phases):
            self.stdscr.addstr(self.lineIdx, 0, f"{i + 1}. {phase}")
            self.lineIdx += 1
        self.stdscr.addstr(self.lineIdx, 0, "Enter your choice: ")
        self.stdscr.refresh()
        key = self.stdscr.getstr(self.lineIdx + 1, 0).decode("utf-8")
        if key.isdigit() and 1 <= int(key) <= len(phases):
            self.phase_name = phases[int(key) - 1]
            print(f"Phase name set to: {self.phase_name}")
            self.session.save_to_config("phase_name", self.phase_name)
        else:
            print("Invalid option entered.")
    
    def tui_set_iti_duration(self):
        self.stdscr.clear()
        self.stdscr.addstr(0, 0, "Enter ITI Duration (seconds): ")
        self.stdscr.refresh()
        iti_duration = self.stdscr.getstr(1, 0).decode("utf-8")
        if iti_duration.isdigit():
            self.iti_duration = int(iti_duration)
            print(f"ITI Duration set to: {self.iti_duration} seconds")
            self.session.save_to_config("iti_duration", self.iti_duration)
        else:
            print("Invalid ITI Duration entered.")
    
    def tui_set_seq_csv_dir(self):
        self.stdscr.clear()
        self.stdscr.addstr(0, 0, "Enter Sequence CSV directory: ")
        self.stdscr.refresh()
        csv_dir = self.stdscr.getstr(1, 0).decode("utf-8")
        if os.path.isdir(csv_dir):
            self.seq_csv_dir = csv_dir
            print(f"Seq CSV directory set to: {self.seq_csv_dir}")
            self.session.save_to_config("seq_csv_dir", self.seq_csv_dir)
        else:
            print("Invalid Sequence directory entered.")
    
    def tui_set_seq_csv_file(self):
        self.stdscr.clear()
        self.stdscr.addstr(0, 0, "Enter Sequence CSV file: ")
        self.stdscr.refresh()
        csv_file = self.stdscr.getstr(1, 0).decode("utf-8")
        if os.path.isfile(os.path.join(self.seq_csv_dir, csv_file)):
            self.seq_csv_file = csv_file
            print(f"Seq CSV file set to: {self.seq_csv_file}")
            self.session.save_to_config("seq_csv_file", self.seq_csv_file)
        else:
            print("Invalid Sequence CSV file entered.")
    
    def tui_set_data_csv_dir(self):
        self.stdscr.clear()
        self.stdscr.addstr(0, 0, "Enter Data CSV directory: ")
        self.stdscr.refresh()
        csv_dir = self.stdscr.getstr(1, 0).decode("utf-8")
        if os.path.isdir(csv_dir):
            self.data_csv_dir = csv_dir
            print(f"Data CSV directory set to: {self.data_csv_dir}")
            self.session.save_to_config("data_csv_dir", self.data_csv_dir)
        else:
            print("Invalid Data directory entered.")
    
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
            "Discover M0s": self.session.discover_m0s,
            "Start Recording": self.start_recording,
            "Stop Recording": self.stop_recording,
            "Start Training": self.start_training,
            "Stop Training": self.stop_training,
            "Start Priming": self.start_priming,
            "Stop Priming": self.stop_priming,
            f"Set Rodent Name ({self.rodent_name})": self.tui_set_rodent_name,
            f"Set Phase Name ({self.phase_name})": self.tui_set_phase_name,
            f"Set ITI Duration ({self.iti_duration})": self.tui_set_iti_duration,
            f"Set Sequence CSV Directory ({self.seq_csv_dir})": self.tui_set_seq_csv_dir,
            f"Set Sequence CSV File ({self.seq_csv_file})": self.tui_set_seq_csv_file,
            f"Set Data CSV Directory ({self.data_csv_dir})": self.tui_set_data_csv_dir,
            "Export Data": self.export_data,
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

