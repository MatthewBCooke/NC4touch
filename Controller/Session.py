import os
import time
import pigpio
import yaml
import netifaces
import importlib
import logging
import threading

# Local modules
from Chamber import Chamber
from Trainer import Trainer
from DoNothingTrainer import DoNothingTrainer

import logging
session_logger = logging.getLogger('session_logger')
session_logger.setLevel(logging.DEBUG)
logger = session_logger.getChild(__name__)
logger.setLevel(logging.DEBUG)

class Session:
    """
    This class manages the session configuration, hardware initialization, and training phases.
    It uses the Chamber class to manage the hardware components and the Trainer class to manage the training phases.
    """
    def __init__(self, session_config_file=None):
        code_dir = os.path.dirname(os.path.realpath(__file__))

        # Find and load the config files
        if not session_config_file:
            self.session_config_file = os.path.join(code_dir, 'session_config.yaml')
        else:
            self.session_config_file = session_config_file

        # Initialize config files
        self.session_config = self.load_config(self.session_config_file)

        self.trainer_name = self.session_config.get("trainer_name", "DoNothingTrainer")
        self.rodent_name = self.session_config.get("rodent_name", "TestRodent")
        self.iti_duration = self.session_config.get("iti_duration", 10)
        self.seq_csv_dir = self.session_config.get("seq_csv_dir", os.path.join(code_dir, "sequences"))
        self.seq_csv_file = self.session_config.get("seq_csv_file", "sequences.csv")
        self.data_csv_dir = self.session_config.get("data_csv_dir", os.path.join(code_dir, "data"))
        self.video_dir = self.session_config.get("video_dir", os.path.join(code_dir, "videos"))

        self.chamber = Chamber()
        self.set_trainer_name('DoNothingTrainer')

        # Video Recording
        self.is_video_recording = False

        self.session_timer = threading.Timer(0.1, self.trainer.run_training)

    def start_training(self):
        if not self.trainer:
            logger.error("Trainer not initialized.")
            return
        if not isinstance(self.trainer, Trainer):
            logger.error("Trainer is not an instance of Trainer.")
            return
        
        self.trainer.rodent_name = self.rodent_name
        self.trainer.iti_duration = self.iti_duration
        self.trainer.seq_csv_dir = self.seq_csv_dir
        self.trainer.seq_csv_file = self.seq_csv_file
        self.trainer.start_training()
        self.session_timer.start()
        logger.info("Training session started.")

    def stop_video_recording(self):
        if self.is_video_recording:
            self.chamber.camera.stop_recording()
            self.is_video_recording = False
            logger.info("Recording stopped.")
        else:
            logger.warning("No recording in progress to stop.")
    
    def start_video_recording(self):
        if not self.is_video_recording:
            datetime_str = time.strftime("%Y%m%d_%H%M%S")
            video_file = os.path.join(self.video_dir, f"{datetime_str}_{self.chamber.chamber_name}_{self.rodent_name}.mp4")

            self.chamber.camera.start_recording(video_file)
            self.is_video_recording = True
            logger.info(f"Recording started to: {video_file}")
        else:
            logger.warning("Recording is already in progress.")
    
    def load_config(self, config_file):
        if os.path.isfile(config_file):
            with open(config_file, 'r') as file:
                config = yaml.safe_load(file)
            return config
        else:
            logger.error(f"Config file {config_file} not found.")
            return {}

    def save_to_session_config(self, key, value):
        self.session_config[key] = value
        with open(self.session_config_file, 'w') as f:
            yaml.dump(self.session_config, f)

    def set_iti_duration(self, iti_duration):
        if isinstance(iti_duration, int) and iti_duration > 0:
            self.iti_duration = iti_duration
            logger.debug(f"ITI Duration set to: {self.iti_duration} seconds")
            self.save_to_session_config("iti_duration", self.iti_duration)
        else:
            logger.error("Invalid ITI Duration entered. Must be a positive integer.")

    def set_seq_csv_dir(self, seq_csv_dir):
        if os.path.isdir(seq_csv_dir):
            self.seq_csv_dir = seq_csv_dir
            logger.debug(f"Seq CSV directory set to: {self.seq_csv_dir}")
            self.save_to_session_config("seq_csv_dir", self.seq_csv_dir)
        else:
            logger.error("Invalid Sequence directory entered.")

    def set_seq_csv_file(self, seq_csv_file):
        if os.path.isfile(os.path.join(self.seq_csv_dir, seq_csv_file)):
            self.seq_csv_file = seq_csv_file
            logger.debug(f"Seq CSV file set to: {self.seq_csv_file}")
            self.save_to_session_config("seq_csv_file", self.seq_csv_file)
        else:
            logger.error("Invalid Sequence CSV file entered.")

    def set_video_dir(self, video_dir):
        if os.path.isdir(video_dir):
            self.video_dir = video_dir
            logger.debug(f"Video directory set to: {self.video_dir}")
            self.save_to_session_config("video_dir", self.video_dir)
        else:
            logger.error("Invalid Video directory entered.")

    def set_data_csv_dir(self, data_csv_dir):
        if os.path.isdir(data_csv_dir):
            self.data_csv_dir = data_csv_dir
            logger.debug(f"Data CSV directory set to: {self.data_csv_dir}")
            self.save_to_session_config("data_csv_dir", self.data_csv_dir)
        else:
            logger.error("Invalid Data directory entered.")
    
    def set_trainer_name(self, trainer_name):
        if trainer_name:
            try:
                # Dynamically load the trainer class based on the name
                module = importlib.import_module(f"{trainer_name}")
                trainer_class = getattr(module, trainer_name)
                self.trainer = trainer_class(self.chamber, {})
                self.trainer_name = trainer_name
            except ImportError as e:
                logger.error(f"Error loading trainer {trainer_name}: {e}")
                return
            except Exception as e:
                logger.error(f"Error initializing trainer {trainer_name}: {e}")
                return

            logger.debug(f"Trainer loaded: {self.trainer_name}")
            self.save_to_session_config("trainer_name", trainer_name)
        else:
            logger.error("No Trainer name entered.")
            self.trainer = DoNothingTrainer(self.chamber, {})

    def set_rodent_name(self, rodent_name):
        if rodent_name:
            self.rodent_name = rodent_name
            logger.debug(f"Rodent name set to: {self.rodent_name}")
            self.save_to_session_config("rodent_name", rodent_name)
        else:
            logger.error("No Rodent name entered.")

    def export_data(self):
        if not self.trainer:
            logger.error("No trainer to export data from.")
            return
        if not self.trainer.trial_data:
            logger.warning("No trial data to export.")
            return
        
        datetime_str = time.strftime("%Y%m%d_%H%M%S")
        data_csv_file = os.path.join(self.data_csv_dir, f"{datetime_str}_{self.chamber.chamber_name}_{self.rodent_name}_data.csv")
        self.trainer.export_results_csv(data_csv_file)
        logger.info(f"Data exported to {data_csv_file}")

    def stop_training(self):
        if self.trainer:
            self.session_timer.cancel()
            self.trainer.stop_training()
            logger.info("Training session ended.")
        else:
            logger.warning("No training session to stop.")