import json
from Chamber import Chamber
from datetime import datetime
from abc import ABC, abstractmethod
from Config import Config

import logging
logger = logging.getLogger(f"session_logger.{__name__}")

def get_trainers():
    """
    Returns a list of available trainers.
    """
    return [
        "DoNothingTrainer",
        "Habituation",
        "InitialTouch",
        # Add more trainers as needed
    ]

class Trainer(ABC):
    """
    Orchestrates phases for rodent training using M0 boards for visual stimuli,
    and pigpio-based hardware for reward, LED, beam break, etc.
    """

    def __init__(self, chamber, trainer_config = {}, trainer_config_file = '~/trainer_config.yaml'):
        if not isinstance(chamber, Chamber):
            logger.error("chamber must be an instance of Chamber")
            raise ValueError("chamber must be an instance of Chamber")

        self.chamber = chamber
        self.config = Config(config = trainer_config, config_file = trainer_config_file)

        # Ensure required parameters are set in the config
        self.config.ensure_param("trainer_name", "DoNothingTrainer")
        self.config.ensure_param("rodent_name", "TestRodent")

        self.data_file = None

    def open_data_file(self):
        """
        Opens a json file for writing trial data.
        """
        if self.data_file is None:
            date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            chamber_name = self.chamber.config["name"]
            rodent_name = self.config["rodent_name"]
            trainer_name = self.config["trainer_name"]
            self.data_filename = f"{date_str}_{chamber_name}_{trainer_name}_{rodent_name}_data.json"
            
            logger.info(f"Creating data file: {self.data_filename}")
            self.data_file = open(self.data_filename, "w")
            self.data_file.write("# NC4Touch training data\n")

            # Create a header with metadata
            header = {
                "header": {
                    "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S_%f"),
                    "rodent": self.config["rodent_name"],
                    "chamber": self.chamber.config["name"],
                    "trainer": self.config["trainer_name"],
                }
            }
            # Write the header to the json file
            json.dump(header, self.data_file)
        else:
            logger.warning("Data file already open. Skipping creation.")
    
    def close_data_file(self):
        """
        Closes the data file.
        """
        if self.data_file:
            logger.info(f"Closing data file: {self.data_filename}")

            self.data_file.close()
            self.data_file = None
        else:
            logger.warning("Data file is already closed.")
    
    def write_event(self, event, data):
        """
        Writes a single event to the YAML file.
        """
        if self.data_file:
            event_data = {
                "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S_%f"),
                "event": event,
                "data": data,
            }
            json.dump(event_data, self.data_file)
        else:
            logger.warning("Data file is not open. Cannot write event.")
    
    @abstractmethod
    def start_training(self):
        """
        Starts the trainer.
        This should be overridden in subclasses to implement specific training logic.
        """
        raise NotImplementedError("start_training() must be implemented in subclasses.")
    
    @abstractmethod
    def run_training(self):
        """
        Main loop for running the trainer.
        This should be overridden in subclasses to implement specific training logic.
        """
        raise NotImplementedError("run_training() must be implemented in subclasses.")
    
    @abstractmethod
    def stop_training(self):
        """
        Ends the trainer.
        This should be overridden in subclasses to implement specific training logic.
        """
        raise NotImplementedError("stop_training() must be implemented in subclasses.")
    
    