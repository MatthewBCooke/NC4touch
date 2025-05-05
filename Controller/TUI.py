import time
import curses

from Session import Session
from Trainer import get_trainers

import logging
session_logger = logging.getLogger('session_logger')
logger = session_logger.getChild(__name__)
logger.setLevel(logging.DEBUG)


class TUI:
    def __init__(self):
        # Counters for tracking progress
        self.session = Session()

        # Setup camera
        self.is_recording = False

        self.stdscr = None
        self.run_loop = True
        self.lineIdx = 0
    
    def __del__(self):
        self.tui_exit()
        self.run_loop = False
    
    def tui_start_video_recording(self):
        self.tui_exit()
        self.session.start_video_recording()
        self.tui_init()
    
    def tui_stop_video_recording(self):
        self.tui_exit()
        self.session.stop_video_recording()
        self.tui_init()

    def tui_start_training(self):
        self.tui_exit()
        self.session.start_training()
        self.tui_init()
    
    def tui_stop_training(self):
        self.tui_exit()
        self.session.stop_training()
        self.tui_init()
    
    def tui_start_priming(self):
        self.tui_exit()
        self.session.chamber.reward.prime_feeding_tube()
        self.tui_init()
    
    def tui_stop_priming(self):
        self.tui_exit()
        self.session.chamber.reward.stop_priming()
        self.tui_init()
    
    def tui_export_data(self):
        self.tui_exit()
        self.export_data()
        self.tui_init()
    
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
        self.session.set_rodent_name(rodent_name)
    
    def tui_set_trainer_name(self):
        trainers = get_trainers()

        self.stdscr.clear()
        self.lineIdx = 0
        self.stdscr.addstr(self.lineIdx, 0, "Select Trainer:")
        self.lineIdx += 1
        for i, trainer in enumerate(trainers):
            self.stdscr.addstr(self.lineIdx, 0, f"{i + 1}. {trainer}")
            self.lineIdx += 1
        self.stdscr.addstr(self.lineIdx, 0, "Enter your choice: ")
        self.stdscr.refresh()
        key = self.stdscr.getstr(self.lineIdx + 1, 0).decode("utf-8")
        if key.isdigit() and 1 <= int(key) <= len(trainers):
            trainer_name = trainers[int(key) - 1]
            self.session.set_trainer_name(trainer_name)
        else:
            self.stdscr.addstr(self.lineIdx + 2, 0, "Invalid choice")
    
    def tui_set_iti_duration(self):
        self.stdscr.clear()
        self.stdscr.addstr(0, 0, "Enter ITI Duration (seconds): ")
        self.stdscr.refresh()
        iti_duration = self.stdscr.getstr(1, 0).decode("utf-8")
        if iti_duration.isdigit():
            self.session.set_iti_duration(int(iti_duration))
        else:
            logger.error("Invalid ITI Duration entered.")
    
    def tui_set_seq_csv_dir(self):
        self.stdscr.clear()
        self.stdscr.addstr(0, 0, "Enter Sequence CSV directory: ")
        self.stdscr.refresh()
        csv_dir = self.stdscr.getstr(1, 0).decode("utf-8")
        self.session.set_seq_csv_dir(csv_dir)
    
    def tui_set_seq_csv_file(self):
        self.stdscr.clear()
        self.stdscr.addstr(0, 0, "Enter Sequence CSV file: ")
        self.stdscr.refresh()
        csv_file = self.stdscr.getstr(1, 0).decode("utf-8")
        self.session.set_seq_csv_file(csv_file)
    
    def tui_set_data_csv_dir(self):
        self.stdscr.clear()
        self.stdscr.addstr(0, 0, "Enter Data CSV directory: ")
        self.stdscr.refresh()
        csv_dir = self.stdscr.getstr(1, 0).decode("utf-8")
        self.session.set_data_csv_dir(csv_dir)
    
    def tui_set_video_dir(self):
        self.stdscr.clear()
        self.stdscr.addstr(0, 0, "Enter Video directory: ")
        self.stdscr.refresh()
        video_dir = self.stdscr.getstr(1, 0).decode("utf-8")
        self.session.set_video_dir(video_dir)

    def tui_discover_m0s(self):
        self.tui_exit()
        self.session.chamber.discover_m0_boards()
        self.tui_init()
    
    def tui_exit(self):
        curses.nocbreak()
        self.stdscr.keypad(False)
        curses.echo()
        curses.endwin()
    
    def tui_export_data(self):
        self.tui_exit()
        self.session.export_data()
        self.tui_init()
    
    def tui_show_menu(self):
        self.lineIdx = 0
        # Option dictionary
        options = {
            "Discover M0s": self.tui_discover_m0s,
            f"Set Rodent Name ({self.session.rodent_name})": self.tui_set_rodent_name,
            f"Set Trainer Name ({self.session.trainer_name})": self.tui_set_trainer_name,
            f"Set ITI Duration ({self.session.iti_duration})": self.tui_set_iti_duration,
            f"Set Sequence CSV Directory ({self.session.seq_csv_dir})": self.tui_set_seq_csv_dir,
            f"Set Sequence CSV File ({self.session.seq_csv_file})": self.tui_set_seq_csv_file,
            f"Set Data CSV Directory ({self.session.data_csv_dir})": self.tui_set_data_csv_dir,
            f"Set Video Directory ({self.session.video_dir})": self.tui_set_video_dir,
            "Start Recording": self.tui_start_video_recording,
            "Stop Recording": self.tui_stop_video_recording,
            "Start Training": self.tui_start_training,
            "Stop Training": self.tui_stop_training,
            "Start Priming": self.tui_start_priming,
            "Stop Priming": self.tui_stop_priming,
            "Export Data": self.tui_export_data,
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