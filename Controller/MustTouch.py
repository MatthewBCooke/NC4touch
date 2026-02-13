import time
import os
from enum import Enum, auto

from Trainer import Trainer

import logging
logger = logging.getLogger(f"session_logger.{__name__}")

class MustTouchState(Enum):
    """Enum for different states in the must touch trainer."""
    IDLE = auto()
    START_TRAINING = auto()
    START_TRIAL = auto()
    WAIT_FOR_TOUCH = auto()
    DELIVER_REWARD_START = auto()
    DELIVERING_REWARD = auto()
    POST_REWARD = auto()
    CORRECT = auto()
    ERROR = auto()
    ITI_START = auto()
    ITI = auto()
    END_TRIAL = auto()
    END_TRAINING = auto()

class MustTouch(Trainer):
    """
    MustTouch trainer for the rodent training session.

    In MustTouch, the animal is required to touch the correct screen
    before a reward is dispensed. The goal is to teach the animal to
    associate touching the correct target with receiving a reward.

    If the animal touches the correct target (the one with an image), a reward will be dispensed for a set duration. 
    The trainer will also monitor the beam break sensor to detect if the animal is interacting with the reward
    system. If the beam is broken, the trainer will turn off the reward LED. Once the reward is 
    dispensed, the trainer will wait for a set duration for the beam to be broken before moving on.

    The trainer will next wait for a set ITI duration before starting the next trial. If the animal breaks the beam during the
    ITI, one second will be added to the ITI duration.

    The trainer will repeat this process for a set number of trials.

    State machine:
    IDLE -> START_TRAINING -> START_TRIAL -> CORRECT -> DELIVER_REWARD_START -> DELIVERING_REWARD -> POST_REWARD -> ITI_START -> ITI -> END_TRIAL -> END_TRAINING
    """
    def __init__(self, chamber, trainer_config = {}, trainer_config_file = '~/trainer_MustTouch_config.yaml'):
        super().__init__(chamber=chamber, trainer_config=trainer_config, trainer_config_file=trainer_config_file)

        # Initialize the trainer configuration.
        # All variables used by the trainer are recommended to be set in the config file.
        # This allows for easy modification of the trainer parameters without changing the code.
        # The trainer will also reinitialize with these parameters.
        # self.config.ensure_param("param_name", default_value)  # Example of setting a parameter
        self.config.ensure_param("trainer_name", "MustTouch")
        self.config.ensure_param("num_trials", 30)  # Number of trials to run
        self.config.ensure_param("reward_pump_secs", 3.5)  # Duration for which the reward pump is activated
        self.config.ensure_param("beam_break_wait_time", 10) # Time to wait for beam break after reward delivery
        self.config.ensure_param("iti_duration", 10) # Duration of the inter-trial interval (ITI)
        self.config.ensure_param("max_iti_duration", 30) # Maximum ITI duration

        # Local variables used by the trainer during the training session and not set in the config file.
        self.reward_start_time = time.time()
        self.reward_collected = False
        self.last_beam_break_time = time.time()
        self.iti_start_time = time.time()

        self.current_trial = 0
        self.current_trial_iti = self.config["iti_duration"]
        self.state = MustTouchState.IDLE

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
        self.state = MustTouchState.START_TRAINING
    
    def load_images(self):
        """Load images for the current trial."""
        # Load images from the sequence file
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

        if self.state == MustTouchState.IDLE:
            pass

        elif self.state == MustTouchState.START_TRAINING:
            logger.info("Starting training session...")
            self.write_event("StartTraining", 1)
            self.current_trial = 0
            self.state = MustTouchState.START_TRIAL

        elif self.state == MustTouchState.START_TRIAL:
            self.current_trial += 1
            if self.current_trial <= self.config["num_trials"]:
                logger.info(f"Starting trial {self.current_trial}...")
                self.write_event("StartTrial", self.current_trial)

                # Load and show images for this trial
                self.load_images()
                self.show_images()
                self.trial_start_time = current_time
                self.reward_collected = False

                self.state = MustTouchState.WAIT_FOR_TOUCH
            else:
                logger.info("All trials completed.")
                self.state = MustTouchState.END_TRAINING

        elif self.state == MustTouchState.WAIT_FOR_TOUCH:
            # Check for 300s timeout on first trial
            if self.current_trial == 1 and current_time - self.trial_start_time >= 300:
                logger.info("300s Timeout - Moving to next trial")
                self.write_event("TouchTimeout", self.current_trial)
                self.clear_images()
                self.state = MustTouchState.ITI_START
                return

            # Check for touches
            if self.chamber.left_m0.is_touched():
                logger.info("Left screen touched")
                self.write_event("LeftScreenTouched", self.current_trial)
                if self.left_image == "A01":
                    self.state = MustTouchState.CORRECT
                else:
                    self.state = MustTouchState.ERROR

            elif self.chamber.right_m0.is_touched():
                logger.info("Right screen touched")
                self.write_event("RightScreenTouched", self.current_trial)
                if self.right_image == "A01":
                    self.state = MustTouchState.CORRECT
                else:
                    self.state = MustTouchState.ERROR
            # If nothing touched, stay in WAIT_FOR_TOUCH

        elif self.state == MustTouchState.CORRECT:
            logger.info(f"Correct response for trial {self.current_trial}")
            self.write_event("CorrectTouch", self.current_trial)
            self.clear_images()
            self.state = MustTouchState.DELIVER_REWARD_START

        elif self.state == MustTouchState.ERROR:
            logger.info(f"Incorrect response for trial {self.current_trial}")
            self.write_event("IncorrectTouch", self.current_trial)
            self.clear_images()
            self.state = MustTouchState.ITI_START

        elif self.state == MustTouchState.DELIVER_REWARD_START:
            logger.info(f"Delivering reward for trial {self.current_trial}...")
            self.reward_start_time = current_time
            self.chamber.reward.dispense()
            self.chamber.reward_led.activate()
            self.chamber.beambreak.activate()
            self.state = MustTouchState.DELIVERING_REWARD

        elif self.state == MustTouchState.DELIVERING_REWARD:
            # DELIVERING_REWARD state, dispensing the reward
            logger.debug("Current state: DELIVERING_REWARD")
            if current_time - self.reward_start_time < self.config["reward_pump_secs"]:
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
                self.state = MustTouchState.POST_REWARD

        elif self.state == MustTouchState.POST_REWARD:
            # POST_REWARD state, waiting for beam break or timeout
            logger.debug("Current state: POST_REWARD")
            if (current_time - self.reward_start_time) < self.config["beam_break_wait_time"]:
                if not self.reward_collected and self.chamber.beambreak.state==False:
                    # Beam break detected after reward dispense
                    self.reward_collected = True
                    logger.info("Beam broken after reward dispense")
                    self.write_event("BeamBreakAfterReward", self.current_trial)
                    self.chamber.reward_led.deactivate()
                    self.state = MustTouchState.ITI_START
            else:
                    logger.info(f"Beam break timeout")
                    self.write_event("BeamBreakTimeout", self.current_trial)
                    self.chamber.reward_led.deactivate()
                    self.state = MustTouchState.ITI_START

        elif self.state == MustTouchState.ITI_START:
            # ITI_START state, preparing for the ITI period
            logger.debug("Current state: ITI_START")
            self.write_event("ITIStart", self.current_trial)
            self.chamber.beambreak.activate()
            self.chamber.reward_led.deactivate()
            self.current_trial_iti = self.config["iti_duration"]
            self.iti_start_time = current_time
            self.state = MustTouchState.ITI
        
        elif self.state == MustTouchState.ITI:
            # ITI state, waiting for the ITI duration
            logger.debug("Current state: ITI")
            if current_time - self.iti_start_time < self.current_trial_iti:
                # Check if beam break is detected during ITI
                if self.chamber.beambreak.state==False:
                    logger.info("Beam broken during ITI. Adding 1 second to ITI duration.")
                    self.write_event("BeamBreakDuringITI", self.current_trial)
                    if self.current_trial_iti < self.config["max_iti_duration"]:
                        self.current_trial_iti += 1
            else:
                logger.info(f"ITI duration of {self.current_trial_iti} seconds completed")
                self.state = MustTouchState.END_TRIAL

        elif self.state == MustTouchState.END_TRIAL:
            # END_TRIAL state, finalizing the trial
            logger.debug("Current state: END_TRIAL")
            logger.info(f"Ending trial {self.current_trial}...")
            self.write_event("EndTrial", self.current_trial)
            self.state = MustTouchState.START_TRIAL

        elif self.state == MustTouchState.END_TRAINING:
            # End the training session
            logger.debug("Current state: END_TRAINING")
            logger.info("Ending training session...")
            self.write_event("EndTraining", 1)
            self.state = MustTouchState.IDLE
            self.stop_training()

    def stop_training(self):
        # Stop the training session
        logger.info("Stopping training session...")
        self.chamber.reward.stop()
        self.chamber.reward_led.deactivate()
        self.chamber.punishment_led.deactivate()
        self.chamber.beambreak.deactivate()
        self.close_data_file()
        self.state = MustTouchState.IDLE