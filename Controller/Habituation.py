import time
from datetime import datetime
from enum import Enum, auto

from Trainer import Trainer
from Chamber import Chamber

import logging
logger = logging.getLogger(f"session_logger.{__name__}")

class HabituationState(Enum):
    """Enum for different states in the habituation trainer."""
    IDLE = auto()
    START_TRAINING = auto()
    START_TRIAL = auto()
    DELIVER_REWARD_START = auto()
    DELIVERING_REWARD = auto()
    POST_REWARD = auto()
    ITI_START = auto()
    ITI = auto()
    END_TRIAL = auto()
    END_TRAINING = auto()

class Habituation(Trainer):
    """
    Habituation trainer for the rodent training session.

    In Habituation , the animal is exposed to the reward system
    without any additional stimuli. The goal is to get the animal used to the
    reward system and the environment.

    The trainer will dispense a reward for a set duration, and the animal will
    be allowed to interact with the reward system. The trainer will also monitor
    the beam break sensor to detect if the animal is interacting with the reward
    system. If the beam is broken, the trainer will turn off the reward LED. Once the reward is 
    dispensed, the trainer will wait for a set duration for the beam to be broken before moving on.

    The trainer will next wait for a set ITI duration before starting the next trial. If the animal breaks the beam during the
    ITI, one second will be added to the ITI duration.

    The trainer will repeat this process for a set number of trials.

    State machine:
    IDLE -> START_TRAINING -> START_TRIAL -> DELIVER_REWARD_START -> DELIVERING_REWARD -> POST_REWARD -> ITI_START -> ITI -> END_TRIAL -> END_TRAINING
    """
    def __init__(self, chamber, trainer_config = {}, trainer_config_file = '~/trainer_Habituation_config.yaml'):
        super().__init__(chamber=chamber, trainer_config=trainer_config, trainer_config_file=trainer_config_file)

        # Initialize the trainer configuration.
        # All variables used by the trainer are recommended to be set in the config file.
        # This allows for easy modification of the trainer parameters without changing the code.
        # The trainer will also reinitialize with these parameters.
        # self.config.ensure_param("param_name", default_value)  # Example of setting a parameter
        self.config.ensure_param("trainer_name", "Habituation")
        self.config.ensure_param("num_trials", 30)  # Number of trials to run
        self.config.ensure_param("reward_pump_secs", 3.5)  # Duration for which the reward pump is activated
        self.config.ensure_param("beam_break_wait_time", 10) # Time to wait for beam break after reward delivery
        self.config.ensure_param("iti_duration", 10) # Duration of the inter-trial interval (ITI)
        self.config.ensure_param("max_iti_duration", 30) # Maximum ITI duration

        # Local variables used by the trainer during the training session and not set in the config file.
        self.reward_start_time = time.time()
        self.reward_collected = False
        self.last_beam_break_time = time.time()

        self.current_trial = 0
        self.current_trial_iti = self.config["iti_duration"]
        self.state = HabituationState.IDLE

    def start_training(self):
        # Starting state
        logger.info("Starting training session...")

        self.chamber.default_state()

        # Start recording data
        self.open_data_file()

        # Initialize the training session
        self.state = HabituationState.START_TRAINING

    def run_training(self):
        """Main loop for running the training session."""
        current_time = time.time()

        if self.state == HabituationState.IDLE:
            # IDLE state, waiting for the start signal
            logger.debug("Current state: IDLE")
            pass 

        elif self.state == HabituationState.START_TRAINING:
            # START_TRAINING state, initializing the training session
            logger.debug("Current state: START_TRAINING")
            logger.info("Starting training session...")
            self.write_event("StartTraining", 1)

            self.current_trial = 0
            self.state = HabituationState.START_TRIAL

        elif self.state == HabituationState.START_TRIAL:
            # START_TRIAL state, preparing for the next trial
            logger.debug("Current state: START_TRIAL")
            self.current_trial += 1
            if self.current_trial < self.config["num_trials"]:
                logger.info(f"Starting trial {self.current_trial}...")
                self.write_event("StartTrial", self.current_trial)

                self.state = HabituationState.DELIVER_REWARD_START
            else:
                # All trials completed, move to end training state
                logger.info("All trials completed.")
                self.state = HabituationState.END_TRAINING

        elif self.state == HabituationState.DELIVER_REWARD_START:
            # DELIVER_REWARD_START state, preparing to deliver the reward
            logger.debug("Current state: DELIVER_REWARD_START")
            self.reward_start_time = current_time
            logger.info(f"Preparing to deliver reward for trial {self.current_trial}...")
            self.write_event("DeliverRewardStart", self.current_trial)
            self.chamber.reward.dispense()
            self.chamber.reward_led.activate()
            self.chamber.beambreak.activate()
            self.state = HabituationState.DELIVERING_REWARD

        elif self.state == HabituationState.DELIVERING_REWARD:
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
                self.state = HabituationState.POST_REWARD

        elif self.state == HabituationState.POST_REWARD:
            # POST_REWARD state, waiting for beam break or timeout
            logger.debug("Current state: POST_REWARD")
            if (current_time - self.reward_start_time) < self.config["beam_break_wait_time"]:
                if not self.reward_collected and self.chamber.beambreak.state==False:
                    # Beam break detected after reward dispense
                    self.reward_collected = True
                    logger.info("Beam broken after reward dispense")
                    self.write_event("BeamBreakAfterReward", self.current_trial)
                    self.chamber.reward_led.deactivate()
                    self.state = HabituationState.ITI_START
            else:
                    logger.info(f"Beam break timeout")
                    self.write_event("BeamBreakTimeout", self.current_trial)
                    self.chamber.reward_led.deactivate()
                    self.state = HabituationState.ITI_START
        
        elif self.state == HabituationState.ITI_START:
            # ITI_START state, preparing for the ITI period
            logger.debug("Current state: ITI_START")
            self.write_event("ITIStart", self.current_trial)
            self.chamber.beambreak.activate()
            self.chamber.reward_led.deactivate()
            self.current_trial_iti = self.config["iti_duration"]
            self.iti_start_time = current_time
            self.state = HabituationState.ITI
        
        elif self.state == HabituationState.ITI:
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
                self.state = HabituationState.END_TRIAL
        
        elif self.state == HabituationState.END_TRIAL:
            # END_TRIAL state, finalizing the trial
            logger.debug("Current state: END_TRIAL")
            logger.info(f"Ending trial {self.current_trial}...")
            self.write_event("EndTrial", self.current_trial)
            self.state = HabituationState.START_TRIAL

        elif self.state == HabituationState.END_TRAINING:
            # End the training session
            logger.debug("Current state: END_TRAINING")
            logger.info("Ending training session...")
            self.write_event("EndTraining", 1)
            self.state = HabituationState.IDLE
            self.stop_training()

    def stop_training(self):
        # Stop the training session
        logger.info("Stopping training session...")
        self.chamber.reward.stop()
        self.chamber.reward_led.deactivate()
        self.chamber.punishment_led.deactivate()
        self.chamber.beambreak.deactivate()
        self.close_data_file()
        self.state = HabituationState.IDLE