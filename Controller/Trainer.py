import csv
from Chamber import Chamber
from datetime import datetime
from abc import ABC, abstractmethod

def get_trainers():
    """
    Returns a list of available trainers.
    """
    return [
        "DoNothingTrainer",
        "Habituation",
        # Add more trainers as needed
    ]
class Trainer(ABC):
    """
    Orchestrates phases for rodent training using M0 boards for visual stimuli,
    and pigpio-based hardware for reward, LED, beam break, etc.
    """

    def __init__(self, trainer_config = {}, chamber = None):
        if not isinstance(chamber, Chamber):
            raise ValueError("chamber must be an instance of Chamber")

        if not isinstance(trainer_config, dict):
            raise ValueError("trainer_config must be a dictionary")

        self.chamber = chamber

        self.trainer_config = trainer_config

        self.num_trials = 0  # Number of trials
        self.current_trial = 0
        self.current_trial_start_time = None  # Start time of the current trial
        self.current_trial_end_time = None

        # In-memory trial data + persistent CSV tracking
        self.session_data = []
        self.data_csv_file = None
        self.data_csv_writer = None
        self.data_csv_filename = None

        self.is_running = False

    def _init_csv_fields(self):
        return [
            "Training Stage", "ID", "TrialNumber",
            "M0_0", "M0_1", "M0_2",
            "touched_m0", "Choice",
            "InitiationTime", "StartTraining", "EndTraining", "Reward"
        ]

    ## [PERSISTENT CSV SESSION]
    def open_realtime_csv(self, phase_name="FullSession"):
        """
        Opens a persistent CSV file for the entire session.
        Call this once (right after the Trainer is created) so that all trial rows
        are appended to the same file.
        """
        if self.data_csv_file is None:
            date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            self.data_csv_filename = f"{date_str}_{phase_name}.csv"
            print(f"Opening persistent CSV file: {self.data_csv_filename}")

            self.data_csv_file = open(self.data_csv_filename, "w", newline="")
            fieldnames = self._init_csv_fields()
            self.data_csv_writer = csv.DictWriter(self.data_csv_file, fieldnames=fieldnames)
            self.data_csv_writer.writeheader()
            self.data_csv_file.flush()

            self.session_start_time = datetime.now().strftime("%H:%M:%S")
        else:
            print(f"Persistent CSV already open: {self.data_csv_filename}")

    def _write_realtime_csv_row(self, row_data):
        """
        Writes a single row to the persistent CSV file and flushes immediately.
        """
        row_data["Training Stage"] = self.current_phase if self.current_phase else "N/A"
        if self.data_csv_writer:
            self.data_csv_writer.writerow(row_data)
            self.data_csv_file.flush()

    def close_realtime_csv(self):
        """
        Closes the persistent CSV file.
        This should be called on GUI close or when ending the session.
        """
        if self.data_csv_file:
            self.session_end_time = datetime.now().strftime("%H:%M:%S")
            print(f"Closing persistent CSV file: {self.data_csv_filename}")
            self.data_csv_file.close()
            self.data_csv_file = None
            self.data_csv_writer = None
            self.data_csv_filename = None

    def finalize_training_timestamp(self):
    # Record the training finish timestamp
        self.session_end_time = datetime.now().strftime("%H:%M:%S")
        if self.trial_data:
            last_row = self.trial_data[-1]
            last_row["EndTraining"] = self.session_end_time
            self._write_realtime_csv_row(last_row)
        print(f"Training finished at {self.session_end_time}.")


    def export_results_csv(self, filename):
        """
        Exports the in-memory trial data to a new CSV file if needed.
        (This is separate from the persistent CSV.)
        """
        if not self.trial_data:
            print("No trial data to export.")
            return
        fieldnames = self._init_csv_fields()
        with open(filename, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in self.trial_data:
                # Ensure that each exported row has the training stage (if not already set)
                if "Training Stage" not in row:
                    row["Training Stage"] = self.current_phase if self.current_phase else "N/A"
                writer.writerow(row)
        print(f"Trial data exported to {filename}.")

    # def flush_message_queues(self):
    #     """Flush out any remaining messages in each M0 device's message queue."""
    #     for dev in self.m0_devices.values():
    #         while not dev.message_queue.empty():
    #             try:
    #                 dev.message_queue.get_nowait()
    #             except queue.Empty:
    #                 break

    def stop_session(self):
        """
        Stop the current training session WITHOUT closing the persistent CSV file.
        When called manually, this also updates the EndTraining timestamp in the CSV.
        """
        if self.is_session_active:
            print("Forcing session to stop.")
            self.is_session_active = False
            # Record the manual stop time in the EndTraining column.
            self.finalize_training_timestamp()

        # Flush message queues so that old events do not interfere with the next phase.
        # self.flush_message_queues()
        
        # Optionally, clear trial data if you want a fresh start for the next phase.
        self.trial_data.clear()
        
        # Deactivate peripherals
        # self.peripherals['reward_led'].deactivate()
        # self.peripherals['reward'].stop_reward_dispense()
        # self.peripherals['beam_break'].deactivate_beam_break()
        
        print("Session stopped and EndTraining timestamp logged.")

    
    @abstractmethod
    def start_training(self):
        """
        Starts the training session.
        This should be overridden in subclasses to implement specific training logic.
        """
        raise NotImplementedError("start_training() must be implemented in subclasses.")
    
    @abstractmethod
    def run_training(self):
        """
        Main loop for running the training session.
        This should be overridden in subclasses to implement specific training logic.
        """
        raise NotImplementedError("run_training() must be implemented in subclasses.")
    
    @abstractmethod
    def stop_training(self):
        """
        Ends the training session.
        This should be overridden in subclasses to implement specific training logic.
        """
        raise NotImplementedError("end_training() must be implemented in subclasses.")
    
    