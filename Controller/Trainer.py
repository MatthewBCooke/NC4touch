import json
import csv
import os
from Chamber import Chamber
from datetime import datetime
from abc import ABC, abstractmethod
from Config import Config

import logging
logger = logging.getLogger(f"session_logger.{__name__}")

def get_trainers():
    # List of available trainers
    return [
        "DoNothingTrainer",
        "Habituation",
        "InitialTouch",
        "MustTouch",
        "Punish_Incorrect",
        "Simple_Discrimination",
        "Complex_Discrimination",
        "PRL",
        "SoundTest",
        # Add more trainers as needed
    ]

class Trainer(ABC):
    # Base trainer class for running training sessions

    def __init__(self, chamber, trainer_config = {}, trainer_config_file = '~/trainer_config.yaml'):
        # Accept both Chamber and VirtualChamber
        try:
            from Virtual.VirtualChamber import VirtualChamber
            valid_chamber = isinstance(chamber, (Chamber, VirtualChamber))
        except ImportError:
            valid_chamber = isinstance(chamber, Chamber)
        
        if not valid_chamber:
            logger.error("chamber must be an instance of Chamber or VirtualChamber")
            raise ValueError("chamber must be an instance of Chamber or VirtualChamber")

        self.chamber = chamber
        self.config = Config(config = trainer_config, config_file = trainer_config_file)

        # Ensure required parameters are set in the config
        self.config.ensure_param("trainer_name", "DoNothingTrainer")
        self.config.ensure_param("rodent_name", "TestRodent")

        self.data_file = None
    
    def read_trainer_seq_file(self, csv_file_path, num_columns):
        # Read trial sequence from CSV file
        trials = []
        try:
            with open(csv_file_path, 'r') as f:
                reader = csv.reader(f)
                # Skip the header row
                next(reader, None)
                # Read the rest of the rows into a list of trials
                trials = [row for row in reader if len(row) >= num_columns]
        except FileNotFoundError:
            logger.error(f"File not found: {csv_file_path}")
        except Exception as e:
            logger.error(f"Error reading file {csv_file_path}: {e}")
        
        return trials

    def open_data_file(self):
        # Create a new JSON file for trial data
        if self.data_file is None:
            date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            chamber_name = self.chamber.config["chamber_name"]
            rodent_name = self.config["rodent_name"]
            trainer_name = self.config["trainer_name"]
            data_dir = self.config["data_dir"] or "/mnt/shared/data"
            os.makedirs(data_dir, exist_ok=True)
            self.data_filename = f"{date_str}_{chamber_name}_{trainer_name}_{rodent_name}_data.json"
            self.data_filepath = os.path.join(data_dir, self.data_filename)
            
            logger.info(f"Creating data file: {self.data_filepath}")
            self.data_file = open(self.data_filepath, "w")
            self.data_file.write("# NC4Touch training data\n")

            # Create a header with metadata
            header = {
                "header": {
                    "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S_%f"),
                    "rodent": self.config["rodent_name"],
                    "chamber": self.chamber.config["chamber_name"],
                    "trainer": self.config["trainer_name"],
                }
            }
            # Write the header to the json file
            json.dump(header, self.data_file)
            self.data_file.write('\n')
            self.data_file.flush()
        else:
            logger.warning("Data file already open. Skipping creation.")
    
    def close_data_file(self):
        # Close the data file when done
        if self.data_file:
            logger.info(f"Closing data file: {self.data_filename}")

            self.data_file.close()
            self.data_file = None
        else:
            logger.debug("Data file already closed; skipping.")
    
    def write_event(self, event, data):
        # Write a single event to the data file
        if self.data_file:
            event_data = {
                "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S_%f"),
                "event": event,
                "data": data,
            }
            json.dump(event_data, self.data_file)
            self.data_file.write('\n')
            self.data_file.flush()
        else:
            logger.warning("Data file is not open. Cannot write event.")
    
    @abstractmethod
    def start_training(self):
        pass
    
    @abstractmethod
    def run_training(self):
        pass
    
    @abstractmethod
    def stop_training(self):
        pass
    
    