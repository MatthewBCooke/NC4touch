from Trainer import Trainer
from Chamber import Chamber

from enum import Enum
import time

import logging
logger = logging.getLogger(f"session_logger.{__name__}")

class DoNothingState(Enum):
    """Enum for different states in the DoNothing trainer."""
    IDLE = -1
    DO_NOTHING_1 = 0
    DO_NOTHING_2 = 1
    DO_NOTHING_3 = 2

class DoNothingTrainer(Trainer):
    """
    A trainer that does nothing. This is useful for testing purposes, and as an example of how to implement a trainer.
    """
    def __init__(self, trainer_config = {}, chamber = None):
        super().__init__(trainer_config, chamber)
        self.trainer_name = "DoNothingTrainer"
        self.state = DoNothingState.IDLE
        self.switch_interval = 5 # Time in seconds to switch between states
        self.state_start_time = time.time()

    def start_training(self):
        """Start the training session."""
        logger.info(f"Starting training session...")
    
    def run_training(self):
        """Run the training session."""
        self.current_time = time.time()

        if self.state == DoNothingState.IDLE:
            logger.debug("DoNothingTrainer is idle.")
            self.state = DoNothingState.DO_NOTHING_1
            logger.info("Switching to DoNothingTrainer state 1.")
            self.state_start_time = self.current_time
            
        elif self.state == DoNothingState.DO_NOTHING_1:
            if self.current_time - self.state_start_time < self.switch_interval:
                logger.debug("DoNothingTrainer is doing nothing 1.")
            else:
                self.state = DoNothingState.DO_NOTHING_2
                self.state_start_time = self.current_time
                logger.info("Switching to DoNothingTrainer state 2.")
        
        elif self.state == DoNothingState.DO_NOTHING_2:
            if self.current_time - self.state_start_time < self.switch_interval:
                logger.debug("DoNothingTrainer is doing nothing 2.")
            else:
                self.state = DoNothingState.DO_NOTHING_3
                self.state_start_time = self.current_time
                logger.info("Switching to DoNothingTrainer state 3.")
        
        elif self.state == DoNothingState.DO_NOTHING_3:
            if self.current_time - self.state_start_time < self.switch_interval:
                logger.debug("DoNothingTrainer is doing nothing 3.")
            else:
                self.state = DoNothingState.IDLE
                self.state_start_time = self.current_time
                logger.info("Switching to DoNothingTrainer state IDLE.")


    def stop_training(self):
        """Stop the training session."""
        logger.info(f"Stopping training session...")
