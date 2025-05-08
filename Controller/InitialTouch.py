import time
from datetime import datetime
from enum import Enum, auto

from Trainer import Trainer
from Chamber import Chamber

import logging
logger = logging.getLogger(f"session_logger.{__name__}")

#TODO: Complete the InitialTouch trainer class

class InitialTouchState(Enum):
    """Enum for different states in the initial touch trainer."""
    IDLE = auto()
    START_TRAINING = auto()
    START_TRIAL = auto()
    INITIAL_REWARD_START = auto()
    DELIVERING_INITIAL_REWARD = auto()
    POST_REWARD = auto()
    ITI_START = auto()
    ITI = auto()
    END_TRIAL = auto()
    END_TRAINING = auto()

class InitialTouch(Trainer):
    def __init__(self, chamber, trainer_config = {}, trainer_config_file = '~/trainer_InitialTouch_config.yaml'):
        super().__init__(chamber=chamber, trainer_config=trainer_config, trainer_config_file=trainer_config_file)

        # Initialize the trainer configuration.
        # All variables used by the trainer are recommended to be set in the config file.
        # This allows for easy modification of the trainer parameters without changing the code.
        # The trainer will also reinitialize with these parameters.
        # self.config.ensure_param("param_name", default_value)  # Example of setting a parameter
        self.config.ensure_param("trainer_name", "InitialTouch")
        self.config.ensure_param("num_trials", 30)  # Number of trials to run
        self.config.ensure_param("iti_duration", 10) # Duration of the inter-trial interval (ITI)
        self.config.ensure_param("initial_reward_duration", 3.0)  # Duration for which the reward pump is activated

        # Local variables used by the trainer during the training session and not set in the config file.
        self.current_trial = 0
        self.reward_start_time = 0.0
        self.reward_collected = False
        self.state = InitialTouchState.IDLE

    def start_training(self):
        # Starting state
        logger.info("Starting training session...")

        self.chamber.default_state()

        # Start recording data
        self.open_data_file()

        # Initialize the training session
        self.state = InitialTouchState.START_TRAINING
    
    def run_training(self):
        """Main loop for running the training session."""
        current_time = time.time()

        if self.state == InitialTouchState.IDLE:
            # IDLE state, waiting for the start signal
            logger.debug("Current state: IDLE")
            pass

        elif self.state == InitialTouchState.START_TRAINING:
            # START_TRAINING state, initializing the training session
            logger.debug("Current state: START_TRAINING")
            logger.info("Starting training session...")
            self.write_event("StartTraining", 1)

            self.current_trial = 0
            self.state = InitialTouchState.INITIAL_REWARD_START

        elif self.state == InitialTouchState.INITIAL_REWARD_START:
            # DELIVER_REWARD_START state, preparing to deliver the reward
            logger.debug("Current state: INITIAL_REWARD_START")
            self.reward_start_time = current_time
            logger.info(f"Preparing to deliver reward for trial {self.current_trial}...")
            self.write_event("DeliverRewardStart", self.current_trial)
            self.chamber.reward.dispense()
            self.chamber.reward_led.activate()
            self.state = InitialTouchState.DELIVERING_INITIAL_REWARD

        elif self.state == InitialTouchState.DELIVERING_INITIAL_REWARD:
            # DELIVERING_REWARD state, dispensing the reward
            logger.debug("Current state: DELIVERING_INITIAL_REWARD")
            if current_time - self.reward_start_time < self.config["initial_reward_duration"]:
                if self.chamber.beambreak.state==False and not self.reward_collected:
                    # Beam break detected during reward dispense
                    self.reward_collected = True
                    logger.info("Beam broken during reward dispense")
                    self.write_event("BeamBreakDuringReward", self.current_trial)
                    self.chamber.beambreak.deactivate()
                    self.chamber.reward_led.deactivate()
            else:
                # Reward finished dispensing
                logger.info(f"Reward dispense completed")
                self.write_event("RewardDispenseComplete", self.current_trial)
                self.chamber.reward.stop()
                self.state = InitialTouchState.POST_REWARD

        elif self.state == InitialTouchState.START_TRIAL:
            # START_TRIAL state, preparing for the next trial
            logger.debug("Current state: START_TRIAL")
            self.current_trial += 1
            if self.current_trial < self.config["num_trials"]:
                logger.info(f"Starting trial {self.current_trial}...")
                self.write_event("StartTrial", self.current_trial)

                self.state = InitialTouchState.INITIAL_REWARD_START
            else:
                # All trials completed, move to end training state
                logger.info("All trials completed.")
                self.state = InitialTouchState.END_TRAINING
