import os
import sys
import time
import yaml
import importlib
import threading

# Local modules
from Chamber import Chamber
from Trainer import Trainer
from Config import Config
from Virtual.VirtualChamber import VirtualChamber

import logging
session_logger = logging.getLogger('session_logger')
session_logger.setLevel(logging.DEBUG)

# Create a stream handler for logging to the console
stream_handler = logging.StreamHandler(stream=sys.stdout)
stream_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('[%(asctime)s:%(name)s:%(levelname)s] %(message)s')
stream_handler.setFormatter(formatter)
session_logger.addHandler(stream_handler)

# File handler is configured in Session.__init__ once chamber_name is known

logger = logging.getLogger(f"session_logger.{__name__}")

#TODO: Make camera reinitialization more reliable

class Session:
    """
    This class manages the session configuration, hardware initialization, and training phases.
    It uses the Chamber class to manage the hardware components and the Trainer class to manage the training phases.
    """
    def __init__(self, session_config = {}, session_config_file='~/session_config.yaml'):
        """
        Initializes the session with the given configuration.
        """
        logger.info("Initializing session...")
        code_dir = os.path.dirname(os.path.abspath(__file__))
        self.config = Config(config=session_config, config_file=session_config_file)
        
        # Construct session config by loading parameters from session_config argument > session_config_file > default values
        self.config.ensure_param("trainer_name", "DoNothingTrainer")
        self.config.ensure_param("rodent_name", "TestRodent")
        self.config.ensure_param("iti_duration", 10)
        self.config.ensure_param("trainer_seq_dir", os.path.join(code_dir, "sequences"))
        self.config.ensure_param("trainer_seq_file", "sequences.csv")
        self.config.ensure_param("data_dir", "/mnt/shared/data")
        self.config.ensure_param("video_dir", "/mnt/shared/videos")
        self.config.ensure_param("run_interval", 0.1)
        self.config.ensure_param("priming_duration", 20)
        self.config.ensure_param("chamber_name", "Chamber0")
        self.config.ensure_param("session_start_time", None)
        self.config.ensure_param("virtual_mode", False)  # Enable virtual chamber for testing
        
        # Initialize directories in case they don't exist
        os.makedirs(self.config["data_dir"], exist_ok=True)
        os.makedirs(self.config["video_dir"], exist_ok=True)

        # Create a file handler for logging to a file (include chamber name)
        if not self.config["session_start_time"]:
            self.config["session_start_time"] = time.strftime("%Y%m%d_%H%M%S")
        current_time = self.config["session_start_time"]
        log_dir = os.path.join(os.getcwd(), "log")
        os.makedirs(log_dir, exist_ok=True)
        self.session_log_file = os.path.join(
            log_dir,
            f"{current_time}_{self.config['chamber_name']}_session_log.log",
        )

        for handler in list(session_logger.handlers):
            if isinstance(handler, logging.FileHandler):
                session_logger.removeHandler(handler)

        file_handler = logging.FileHandler(self.session_log_file)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        session_logger.addHandler(file_handler)

        chamber_config = {
            "chamber_name": self.config["chamber_name"],
        }
        
        # Initialize chamber (virtual or physical)
        if self.config["virtual_mode"]:
            logger.info("=" * 60)
            logger.info("VIRTUAL MODE ENABLED - Using virtual chamber")
            logger.info("=" * 60)
            self.chamber = VirtualChamber(chamber_config=chamber_config)
        else:
            self.chamber = Chamber(chamber_config=chamber_config)
        
        self.set_trainer_name(self.config["trainer_name"])
        self.session_timer = threading.Timer(0.1, self.trainer.run_training)

        self.priming_timer = threading.Timer(0.1, self.run_priming)
        self.priming_start_time = time.time()

        # Video Recording
        self.is_video_recording = False
    
    def __del__(self):
        """Clean up the session by stopping timers and copying log files."""
        logger.info("Cleaning up session...")
        # Stop the session timer if it's running
        if hasattr(self, 'session_timer') and self.session_timer.is_alive():
            self.session_timer.cancel()
        if hasattr(self, 'priming_timer') and self.priming_timer.is_alive():
            self.priming_timer.cancel()
        # Copy log file to data directory
        if hasattr(self, 'config') and hasattr(self, 'session_log_file') and os.path.isfile(self.session_log_file):
            try:
                data_dir = self.config["data_dir"] or "/mnt/shared/data"
                new_log_file = os.path.join(data_dir, os.path.basename(self.session_log_file))
                os.rename(self.session_log_file, new_log_file)
                logger.info(f"Log file copied to {new_log_file}")
            except Exception as e:
                logger.error(f"Error copying log file: {e}")
        if hasattr(self, 'config'):
            self.config["session_start_time"] = None
    
    def set_chamber_name(self, chamber_name):
        if chamber_name:
            self.config["chamber_name"] = chamber_name
            self.chamber.config["chamber_name"] = chamber_name
            logger.debug(f"Chamber name set to: {chamber_name}")
        else:
            logger.error("No Chamber name entered.")
    
    def start_training(self):
        if not isinstance(self.trainer, Trainer):
            logger.error("Trainer is not an instance of Trainer.")
            return
        
        trainer_config = {"rodent_name": self.config["rodent_name"],
                          "chamber_name": self.config["chamber_name"],
                          "trainer_name": self.config["trainer_name"],
                          "iti_duration": self.config["iti_duration"],
                          "trainer_seq_dir": self.config["trainer_seq_dir"],
                          "trainer_seq_file": self.config["trainer_seq_file"],
                          "data_dir": self.config["data_dir"]}
        self.trainer.config.update_with_dict(trainer_config)
        self.trainer.start_training()

        self.session_timer.cancel()
        self.session_timer = threading.Timer(self.config["run_interval"], self.run_training)
        self.session_timer.start()
        logger.info("Training session started.")
    
    def run_training(self):
        self.session_timer.cancel()
        self.trainer.run_training()
        self.session_timer = threading.Timer(self.config["run_interval"], self.run_training)
        self.session_timer.start()
    
    def toggle_video_recording(self):
        if self.is_video_recording:
            self.stop_video_recording()
        else:
            self.start_video_recording()

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

            chamber_name = self.config["chamber_name"]
            rodent_name = self.config["rodent_name"]
            video_dir = self.config["video_dir"]
                        
            video_file = os.path.join(video_dir, f"{datetime_str}_{chamber_name}_{rodent_name}.mp4")

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

    def set_iti_duration(self, iti_duration):
        if isinstance(iti_duration, int) and iti_duration > 0:
            self.config["iti_duration"] = iti_duration
            logger.debug(f"ITI Duration set to: {iti_duration} seconds")
        else:
            logger.error("Invalid ITI Duration entered. Must be a positive integer.")

    def set_trainer_seq_dir(self, trainer_seq_dir):
        if os.path.isdir(trainer_seq_dir):
            self.config["trainer_seq_dir"] = trainer_seq_dir
            logger.debug(f"Trainer Seq directory set to: {trainer_seq_dir}")
        else:
            logger.error("Invalid Sequence directory entered.")

    def set_trainer_seq_file(self, trainer_seq_file):
        if os.path.isfile(os.path.join(self.config["trainer_seq_dir"], trainer_seq_file)):
            self.config["trainer_seq_file"] = trainer_seq_file
            logger.debug(f"Trainer Seq file set to: {trainer_seq_file}")
        else:
            logger.error("Invalid Sequence file entered.")

    def set_video_dir(self, video_dir):
        if os.path.isdir(video_dir):
            self.config["video_dir"] = video_dir
            logger.debug(f"Video directory set to: {video_dir}")
        else:
            logger.error("Invalid Video directory entered.")

    def set_data_dir(self, data_dir):
        if os.path.isdir(data_dir):
            self.config["data_dir"] = data_dir
            logger.debug(f"Data CSV directory set to: {data_dir}")
        else:
            logger.error("Invalid Data directory entered.")
    
    def set_trainer_name(self, trainer_name):
        try:
            module = importlib.import_module(f"{trainer_name}")
            trainer_class = getattr(module, trainer_name)
            self.trainer = trainer_class(self.chamber, {})
            logger.debug(f"Trainer class loaded: {self.trainer}")
            self.config["trainer_name"] = trainer_name
            logger.info(f"Setting trainer name to: {trainer_name}")
        except ImportError as e:
            logger.error(f"Error loading trainer class {trainer_name}: {e}")
            return
        except Exception as e:
            logger.error(f"Error initializing trainer class {trainer_name}: {e}")
            return

    def set_rodent_name(self, rodent_name):
        if rodent_name:
            self.config["rodent_name"] = rodent_name
            logger.debug(f"Rodent name set to: {rodent_name}")
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
        data_csv_file = os.path.join(self.data_dir, f"{datetime_str}_{self.chamber.chamber_name}_{self.rodent_name}_data.csv")
        self.trainer.export_results_csv(data_csv_file)
        logger.info(f"Data exported to {data_csv_file}")

    def stop_training(self):
        if self.trainer:
            self.session_timer.cancel()
            self.trainer.stop_training()
            logger.info("Training session ended.")
        else:
            logger.warning("No training session to stop.")

    def start_priming(self):
        self.priming_start_time = time.time()
        self.priming_timer.cancel()
        self.priming_timer = threading.Timer(0.1, self.run_priming)
        self.priming_timer.start()
        self.chamber.reward.dispense()
        logger.info("Priming started.")
    
    def run_priming(self):
        self.priming_timer.cancel()
        if time.time() - self.priming_start_time < self.priming_duration:
            self.priming_timer = threading.Timer(self.run_interval, self.run_priming)
            self.priming_timer.start()

    def stop_priming(self):
        self.priming_timer.cancel()
        self.chamber.reward.stop()
        logger.info("Priming stopped.")
