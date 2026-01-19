import time
from enum import Enum, auto

from Trainer import Trainer

import logging
import random
logger = logging.getLogger(f"session_logger.{__name__}")

class PRLState(Enum):
    """Enum for different states in the PRL trainer."""
    IDLE = auto()
    START_TRAINING = auto()
    START_TRIAL = auto()
    CORRECT = auto()
    ERROR = auto()
    WAIT_FOR_TOUCH = auto()
    DELIVER_REWARD_START = auto()
    DELIVERING_REWARD = auto()
    POST_REWARD = auto()
    ITI_START = auto()
    ITI = auto()
    END_TRIAL = auto()
    END_TRAINING = auto()

class PRL(Trainer):
    """
    PRL trainer for the rodent training session.

    In PRL , the animal is required to respond to a randomly assigned "high reward probability" 
    or "low reward probability" lever. 

    ##GITHUB EXAMPLE TEST

    The trainer will dispense a reward for a set duration at 80%/20% (high/low) set in config, and the animal will
    interact with the reward system. The trainer will also monitor
    the beam break sensor to detect if the animal is interacting with the reward
    system. If the beam is broken, the trainer will turn off the reward LED. Once the reward is 
    dispensed, the trainer will wait for a set duration for the beam to be broken before moving on.

    The trainer will next wait for a set ITI duration before starting the next trial.

    The trainer will repeat this process for a set number of trials.

    At a set trial number, the trainer will switch the probability of the reward to 20%/80% (adjust in config) until the end of the training session.


    State machine:
    IDLE -> START_TRAINING -> START_TRIAL -> WAIT_FOR_TOUCH -> CORRECT/ERROR -> DELIVER_REWARD_START -> DELIVERING_REWARD -> POST_REWARD -> ITI_START -> ITI -> END_TRIAL -> END_TRAINING
    """
    def __init__(self, chamber, trainer_config = {}, trainer_config_file = '~/trainer_PRL_config.yaml'):
        super().__init__(chamber=chamber, trainer_config=trainer_config, trainer_config_file=trainer_config_file)

        # Initialize the trainer configuration.
        # All variables used by the trainer are recommended to be set in the config file.
        # This allows for easy modification of the trainer parameters without changing the code.
        # The trainer will also reinitialize with these parameters.
        # self.config.ensure_param("param_name", default_value)  # Example of setting a parameter
        self.config.ensure_param("trainer_name", "ProbabilisticReversalLearning")  # Name of the trainer
        self.config.ensure_param("num_trials", 60)  # Number of trials to run
        self.config.ensure_param("high_reward_probability", 0.9)  # Probability of high reward
        self.config.ensure_param("low_reward_probability", 0.1)
        self.config.ensure_param("reward_pump_secs", 1.5)  # Duration for which the reward pump is activated
        self.config.ensure_param("beam_break_wait_time", 10) # Time to wait for beam break after reward delivery
        self.config.ensure_param("iti_duration", 10) # Duration of the inter-trial interval (ITI)
        self.config.ensure_param("max_iti_duration", 30) # Maximum ITI duration


        # Local variables used by the trainer during the training session and not set in the config file.
        self.config.ensure_param("touch_timeout", 30) # Timeout for waiting for touch
        self.config.ensure_param("trial_to_reverse", 30) # Trial at which to reverse reward probabilities
        self.reward_start_time = time.time()
        self.reward_collected = False
        self.last_beam_break_time = time.time()
        self.iti_start_time = time.time()

        self.left_image = "A01.bmp"
        self.right_image = "B01.bmp"
        self.left_reward_probability = 0
        self.right_reward_probability = 0
        self.current_trial = 0
        self.current_trial_iti = self.config["iti_duration"]
        self.state = PRLState.IDLE


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


    def start_training(self):
        # Starting state
        logger.info("Starting training session...")

        self.chamber.default_state()

        # Start recording data
        self.open_data_file()

        # Initialize the training session
        self.state = PRLState.START_TRAINING

    def run_training(self):
        """Main loop for running the training session."""
        current_time = time.time()

        if self.state == PRLState.IDLE:
            # IDLE state, waiting for the start signal
            logger.debug("Current state: IDLE")
            pass 

        elif self.state == PRLState.START_TRAINING:
            # START_TRAINING state, initializing the training session
            logger.debug("Current state: START_TRAINING")
            logger.info("Starting training session...")
            self.write_event("StartTraining ", 1)
            ##randomly assign the reward probability to the touch screens
            if random.random() < 0.5:
                self.left_reward_probability=(self.config["high_reward_probability"])
                self.right_reward_probability=(self.config["low_reward_probability"])
            else:
                self.left_reward_probability=(self.config["low_reward_probability"])
                self.right_reward_probability=(self.config["high_reward_probability"])
            self.current_trial = 0
            self.state = PRLState.START_TRIAL

        elif self.state == PRLState.START_TRIAL:
            # START_TRIAL state, preparing for the next trial
            logger.debug("Current state: START_TRIAL")
            self.current_trial += 1
            if self.current_trial < self.config["num_trials"]:
                logger.info(f"Starting trial {self.current_trial}...")
                self.write_event("StartTrial ", self.current_trial)
                if self.current_trial == self.config["trial_to_reverse"]:
                    # Reverse the reward probabilities
                    logger.info("Reversing reward probabilities...")
                    if self.left_reward_probability == self.config["high_reward_probability"]:
                        self.left_reward_probability = self.config["low_reward_probability"]
                        self.right_reward_probability = self.config["high_reward_probability"]
                    else:
                        self.left_reward_probability = self.config["high_reward_probability"]
                        self.right_reward_probability = self.config["low_reward_probability"]
                # Load images for the current trial
                self.load_images()
                # Show images on the M0 devices
                self.show_images()
                # Start the trial timer
                self.trial_start_time = current_time
                # Move to WAIT_FOR_TOUCH state
                logger.info(f"Images loaded for trial {self.current_trial}: {self.left_image}, {self.right_image}")
                logger.info(f"Reward probabilities set for trial {self.current_trial}: {self.left_reward_probability} (left), {self.right_reward_probability} (right)")
                self.write_event("ImagesLoaded", self.current_trial)
                self.write_event("RewardProbabilitiesSet", self.current_trial)
                self.show_images()
                self.state = PRLState.WAIT_FOR_TOUCH
            else:
                # All trials completed, move to end training state
                logger.info("All trials completed.")
                self.state = PRLState.END_TRAINING
        
        elif self.state == PRLState.WAIT_FOR_TOUCH:
            # WAIT_FOR_TOUCH state, waiting for the animal to touch the screen
            logger.debug("Current state: WAIT_FOR_TOUCH")
            if current_time - self.trial_start_time <= self.config["touch_timeout"]:
                if self.chamber.left_m0.is_touched():
                    logger.info("Left screen touched")
                    self.write_event("LeftScreenTouched ", self.current_trial)

                    if self.left_reward_probability == self.config["high_reward_probability"]:
                        self.state = PRLState.CORRECT
                    else:
                        self.state = PRLState.ERROR
                elif self.chamber.right_m0.is_touched():
                    logger.info("Right screen touched")
                    self.write_event("RightScreenTouched", self.current_trial)

                    if self.right_reward_probability == self.config["high_reward_probability"]:
                        self.state = PRLState.CORRECT
                    else:
                        self.state = PRLState.ERROR
            else:
                # Timeout occurred, move to ITI state
                logger.info("Touch timeout occurred.")
                self.write_event("TouchTimeout ", self.current_trial)
                self.state = PRLState.ITI_START
        
        elif self.state == PRLState.CORRECT:
            # CORRECT state, handling correct touch
            logger.debug("Current state: CORRECT")
            logger.info("Correct touch detected.")
            self.write_event("CorrectTouch ", self.current_trial)

            self.clear_images()
            if random.random() <= self.config["high_reward_probability"]:
                self.state = PRLState.DELIVER_REWARD_START
                logger.info("Delivering reward...")
                self.write_event("DeliverRewardStart ", self.current_trial)
            else:
                self.state = PRLState.ITI_START
                logger.info("No reward delivered, moving to ITI...")
                self.write_event("NoReward ", self.current_trial)
        
        elif self.state == PRLState.ERROR:
            # ERROR state, handling incorrect touch
            logger.debug("Current state: ERROR")
            logger.info("Incorrect touch detected.")
            self.write_event("IncorrectTouch ", self.current_trial)

            self.clear_images()
            if random.random() <= self.config["low_reward_probability"]:
                self.state = PRLState.DELIVER_REWARD_START
                logger.info("Delivering reward...")
                self.write_event("DeliverRewardStart ", self.current_trial)
            else:
                self.state = PRLState.ITI_START
                logger.info("No reward delivered, moving to ITI...")
                self.write_event("NoReward ", self.current_trial)

        elif self.state == PRLState.DELIVER_REWARD_START:
            # DELIVER_REWARD_START state, preparing to deliver the reward
            logger.debug("Current state: DELIVER_REWARD_START")
            self.reward_start_time = current_time
            logger.info(f"Preparing to deliver reward for trial {self.current_trial}...")
            self.write_event("DeliverRewardStart", self.current_trial)
            self.chamber.reward.dispense()
            self.chamber.reward_led.activate()
            self.chamber.beambreak.activate()
            self.state = PRLState.DELIVERING_REWARD

        elif self.state == PRLState.DELIVERING_REWARD:
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
                self.state = PRLState.POST_REWARD

        elif self.state == PRLState.POST_REWARD:
            # POST_REWARD state, waiting for beam break or timeout
            logger.debug("Current state: POST_REWARD")
            if (current_time - self.reward_start_time) < self.config["beam_break_wait_time"]:
                if not self.reward_collected and self.chamber.beambreak.state==False:
                    # Beam break detected after reward dispense
                    self.reward_collected = True
                    logger.info("Beam broken after reward dispense")
                    self.write_event("BeamBreakAfterReward", self.current_trial)
                    self.chamber.reward_led.deactivate()
                    self.state = PRLState.ITI_START
            else:
                    logger.info(f"Beam break timeout")
                    self.write_event("BeamBreakTimeout", self.current_trial)
                    self.chamber.reward_led.deactivate()
                    self.state = PRLState.ITI_START
        
        elif self.state == PRLState.ITI_START:
            # ITI_START state, preparing for the ITI period
            logger.debug("Current state: ITI_START")
            self.write_event("ITIStart", self.current_trial)
            #self.chamber.beambreak.activate()
            self.chamber.reward_led.deactivate()
            # Turn off house lights during ITI
            # self.chamber.house_lights.deactivate()
            self.current_trial_iti = self.config["iti_duration"]
            self.iti_start_time = current_time
            self.state = PRLState.ITI
        
        elif self.state == PRLState.ITI:
            # ITI state, waiting for the ITI duration
            logger.debug("Current state: ITI")
            if current_time - self.iti_start_time < self.current_trial_iti:
                # Check if beam break is detected during ITI
                # if self.chamber.beambreak.state==False:
                #     logger.info("Beam broken during ITI. Adding 1 second to ITI duration.")
                #     self.write_event("BeamBreakDuringITI", self.current_trial)
                #     if self.current_trial_iti < self.config["max_iti_duration"]:
                #         self.current_trial_iti += 1
                pass
            else:
                logger.info(f"ITI duration of {self.current_trial_iti} seconds completed")
                self.state = PRLState.END_TRIAL
        
        elif self.state == PRLState.END_TRIAL:
            # END_TRIAL state, finalizing the trial
            logger.debug("Current state: END_TRIAL")
            logger.info(f"Ending trial {self.current_trial}...")
            self.write_event("EndTrial", self.current_trial)
            self.state = PRLState.START_TRIAL

        elif self.state == PRLState.END_TRAINING:
            # End the training session
            logger.debug("Current state: END_TRAINING")
            logger.info("Ending training session...")
            self.write_event("EndTraining", 1)
            self.state = PRLState.IDLE
            self.stop_training()

    def stop_training(self):
        # Stop the training session
        logger.info("Stopping training session...")
        self.chamber.reward.stop()
        self.chamber.reward_led.deactivate()
        self.chamber.punishment_led.deactivate()
        self.chamber.beambreak.deactivate()
        self.close_data_file()
        self.state = PRLState.IDLE