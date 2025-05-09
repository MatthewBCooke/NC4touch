import time
from enum import Enum, auto
import os

from Trainer import Trainer

import logging
logger = logging.getLogger(f"session_logger.{__name__}")

#TODO: Complete the InitialTouch trainer class

class InitialTouchState(Enum):
    """Enum for different states in the initial touch trainer."""
    IDLE = auto()
    START_TRAINING = auto()
    START_TRIAL = auto()
    WAIT_FOR_TOUCH = auto()
    LARGE_REWARD_START = auto()
    DELIVERING_LARGE_REWARD = auto()
    SMALL_REWARD_START = auto()
    DELIVERING_SMALL_REWARD = auto()
    CORRECT = auto()
    ERROR = auto()
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
        self.config.ensure_param("large_reward_duration", 3.0)  # Duration of the large reward
        self.config.ensure_param("small_reward_duration", 1.5)  # Duration of the small reward
        self.config.ensure_param("trainer_seq_dir", "")  # Directory for the trainer sequence file
        self.config.ensure_param("trainer_seq_file", "")  # Sequence file for the trainer
        self.config.ensure_param("touch_timeout", 120)  # Directory for saving data files

        # Local variables used by the trainer during the training session and not set in the config file.
        self.current_trial = 0
        self.reward_start_time = 0.0
        self.reward_collected = False
        self.left_image = ""
        self.right_image = ""
        self.state = InitialTouchState.IDLE

    def start_training(self):
        # Starting state
        logger.info("Starting training session...")

        self.chamber.default_state()

        # Open sequence file
        trainer_seq_file = os.path.join(self.config["trainer_seq_dir"], self.config["trainer_seq_file"])
        self.trials = self.read_trainer_seq_file(trainer_seq_file, 2)
        if not self.trials:
            logger.error(f"Failed to read trainer sequence file: {trainer_seq_file}")
            return

        # Check if the number of trials is valid
        if len(self.trials) > self.config["num_trials"]:
            logger.warning(f"Number of trials in the sequence file exceeds the expected number of trials: {self.config['num_trials']}")
            # Truncate the trials list to the expected number
            self.trials = self.trials[:self.config["num_trials"]]
        elif len(self.trials) < self.config["num_trials"]:
            logger.error(f"Number of trials in the sequence file does not match the expected number of trials: {self.config['num_trials']}")
            return

        # Start recording data
        self.open_data_file()

        # Initialize the training session
        self.state = InitialTouchState.START_TRAINING
    
    def load_images(self, trial_num):
        """Load images for the current trial."""
        # Load images from the sequence file
        self.left_image = self.trials[trial_num][0]
        self.right_image = self.trials[trial_num][1]

        # Send commands to M0 devices to load images
        self.chamber.left_m0.send_command(f"IMG:{self.left_image}")
        self.chamber.right_m0.send_command(f"IMG:{self.right_image}")
    
    def show_images(self):
        """Display images on the M0 devices."""
        # Send commands to M0 devices to show images
        self.chamber.left_m0.send_command("SHOW")
        self.chamber.right_m0.send_command("SHOW")
    
    def clear_images(self):
        """Clear the images on the M0 devices."""
        # Send commands to M0 devices to blank images
        self.chamber.left_m0.send_command("BLACK")
        self.chamber.right_m0.send_command("BLACK")
    
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

            self.current_trial = 1
            # Start by delivering a large reward
            self.state = InitialTouchState.LARGE_REWARD_START

        elif self.state == InitialTouchState.LARGE_REWARD_START:
            # Load images for the current trial during reward
            self.load_images(self.current_trial - 1)

            # DELIVER_REWARD_START state, preparing to deliver the reward
            logger.debug("Current state: INITIAL_REWARD_START")
            self.reward_start_time = current_time
            logger.info(f"Preparing to deliver large reward for trial {self.current_trial}...")
            self.write_event("DeliverRewardStart", self.current_trial)
            self.chamber.reward.dispense()
            self.chamber.reward_led.activate()
            
            self.state = InitialTouchState.DELIVERING_LARGE_REWARD

        elif self.state == InitialTouchState.DELIVERING_LARGE_REWARD:
            # DELIVERING_REWARD state, dispensing the reward
            logger.debug("Current state: DELIVERING_LARGE_REWARD")
            if current_time - self.reward_start_time < self.config["large_reward_duration"]:
                if self.chamber.beambreak.state==False and not self.reward_collected:
                    # Beam break detected during reward dispense
                    self.reward_collected = True
                    logger.info("Beam broken during reward dispense")
                    self.write_event("BeamBreakDuringLargeReward", self.current_trial)
                    self.chamber.beambreak.deactivate()
                    self.chamber.reward_led.deactivate()
            else:
                # Reward finished dispensing
                logger.info(f"Large reward dispense completed")
                self.write_event("LargeRewardComplete", self.current_trial)
                self.chamber.reward.stop()
                self.state = InitialTouchState.ITI_START
        
        elif self.state == InitialTouchState.SMALL_REWARD_START:
            # Load images for the current trial during reward
            self.load_images(self.current_trial - 1)

            # SMALL_REWARD_START state, preparing to deliver a small reward
            logger.debug("Current state: SMALL_REWARD_START")
            self.reward_start_time = current_time
            logger.info(f"Preparing to deliver small reward for trial {self.current_trial}...")
            self.write_event("SmallRewardStart", self.current_trial)
            self.chamber.reward.dispense()
            self.chamber.reward_led.activate()
            
            self.state = InitialTouchState.DELIVERING_SMALL_REWARD
        
        elif self.state == InitialTouchState.DELIVERING_SMALL_REWARD:
            # DELIVERING_SMALL_REWARD state, dispensing the small reward
            logger.debug("Current state: DELIVERING_SMALL_REWARD")
            if current_time - self.reward_start_time < self.config["small_reward_duration"]:
                if self.chamber.beambreak.state==False and not self.reward_collected:
                    # Beam break detected during small reward dispense
                    self.reward_collected = True
                    logger.info("Beam broken during small reward dispense")
                    self.write_event("BeamBreakDuringSmallReward", self.current_trial)
                    self.chamber.beambreak.deactivate()
                    self.chamber.reward_led.deactivate()
            else:
                # Small reward finished dispensing
                logger.info(f"Small reward dispense completed")
                self.write_event("SmallRewardComplete", self.current_trial)
                self.chamber.reward.stop()
                self.state = InitialTouchState.ITI_START

        elif self.state == InitialTouchState.START_TRIAL:
            # START_TRIAL state, preparing for the next trial
            logger.debug("Current state: START_TRIAL")
            if self.current_trial <= self.config["num_trials"]:
                logger.info(f"Starting trial {self.current_trial}...")
                self.write_event("StartTrial", self.current_trial)

                # Show images for the next trial
                self.show_images()
                self.trial_start_time = current_time

                self.state = InitialTouchState.WAIT_FOR_TOUCH
            else:
                # All trials completed, move to end training state
                logger.info("All trials completed.")
                self.state = InitialTouchState.END_TRAINING
        
        elif self.state == InitialTouchState.WAIT_FOR_TOUCH:
            # WAIT_FOR_TOUCH state, waiting for the animal to touch the screen
            logger.debug("Current state: WAIT_FOR_TOUCH")
            if current_time - self.trial_start_time <= self.config["touch_timeout"]:
                if self.chamber.left_m0.is_touched():
                    logger.info("Left screen touched")
                    self.write_event("LeftScreenTouched", self.current_trial)

                    if self.left_image == "A01":
                        self.state = InitialTouchState.CORRECT
                    else:
                        self.state = InitialTouchState.ERROR
                elif self.chamber.right_m0.is_touched():
                    logger.info("Right screen touched")
                    self.write_event("RightScreenTouched", self.current_trial)

                    if self.right_image == "A01":
                        self.state = InitialTouchState.CORRECT
                    else:
                        self.state = InitialTouchState.ERROR
            else:
                # Timeout occurred, move to ITI state
                logger.info("Touch timeout occurred.")
                self.write_event("TouchTimeout", self.current_trial)
                self.state = InitialTouchState.ITI_START
        
        elif self.state == InitialTouchState.CORRECT:
            # CORRECT state, handling correct touch
            logger.debug("Current state: CORRECT")
            logger.info("Correct touch detected.")
            self.write_event("CorrectTouch", self.current_trial)

            self.clear_images()
            self.state = InitialTouchState.LARGE_REWARD_START
        
        elif self.state == InitialTouchState.ERROR:
            # ERROR state, handling incorrect touch
            logger.debug("Current state: ERROR")
            logger.info("Incorrect touch detected.")
            self.write_event("IncorrectTouch", self.current_trial)

            self.clear_images()
            self.state = InitialTouchState.SMALL_REWARD_START
        
        elif self.state == InitialTouchState.ITI_START:
            # ITI_START state, preparing for the inter-trial interval
            logger.debug("Current state: ITI_START")
            self.iti_start_time = current_time
            logger.info("Starting inter-trial interval...")
            self.write_event("ITIStart", self.current_trial)
            self.state = InitialTouchState.ITI
        
        elif self.state == InitialTouchState.ITI:
            # ITI state, waiting for the inter-trial interval to complete
            logger.debug("Current state: ITI")
            if current_time - self.iti_start_time >= self.config["iti_duration"]:
                # ITI completed, move to start trial state
                logger.info("Inter-trial interval completed.")
                self.write_event("ITIComplete", self.current_trial)
                self.current_trial += 1
                self.state = InitialTouchState.START_TRIAL

        elif self.state == InitialTouchState.END_TRAINING:
            # End the training session
            logger.debug("Current state: END_TRAINING")
            logger.info("Ending training session...")
            self.write_event("EndTraining", 1)
            self.state = InitialTouchState.IDLE
            self.stop_training()

    def stop_training(self):
        # Stop the training session
        logger.info("Stopping training session...")
        self.chamber.reward.stop()
        self.chamber.reward_led.deactivate()
        self.chamber.punishment_led.deactivate()
        self.chamber.beambreak.deactivate()
        self.close_data_file()
        self.state = InitialTouchState.IDLE