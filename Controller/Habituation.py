import time
from datetime import datetime
from enum import Enum

from Trainer import Trainer
from Chamber import Chamber

import logging
session_logger = logging.getLogger('session_logger')
logger = session_logger.getChild(__name__)
logger.setLevel(logging.DEBUG)

class HabituationState(Enum):
    """Enum for different states in the habituation phase."""
    IDLE = -1
    START_TRAINING = 0
    START_TRIAL = 1
    DELIVER_REWARD_START = 2
    DELIVERING_REWARD = 3
    POST_REWARD = 4
    ITI_START = 5
    ITI = 6
    END_TRIAL = 7
    END_TRAINING = 8

class Habituation(Trainer):
    """
    Habituation phase for the rodent training session.

    In the Habituation phase, the animal is exposed to the reward system
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
    def __init__(self, trainer_config = {}, chamber = None):
        super().__init__(trainer_config, chamber)
        self.trainer_name = "Habituation"
        self.trial_data = []

        self.num_trials = 30
        self.current_trial = 0

        self.pump_secs = 3.5  # Duration for which the reward pump is activated
        self.beam_break_wait_time = 10  # Time to wait for beam break after reward delivery
        self.iti_duration = 10
        self.reward_start_time = time.time()
        self.reward_collected = False
        self.last_beam_break_time = time.time()
        self.current_trial_iti = self.iti_duration
        self.max_iti_duration = 30  # Maximum ITI duration
        self.is_running = False

        self.state = HabituationState.IDLE

    def start_training(self):
        # Starting state
        # Turn screens off
        self.chamber.beambreak.deactivate()
        self.chamber.reward_led.activate()
        self.chamber.punishment_led.deactivate()
        self.chamber.reward.stop()

        # Initialize the training session
        self.is_running = True
        self.state = HabituationState.START_TRAINING

    def run_training(self):
        """Main loop for running the training session."""
        current_time = time.time()
        logger.debug(f"Current time: {current_time}")

        if self.state == HabituationState.IDLE:
            # IDLE state, waiting for the start signal
            pass 

        elif self.state == HabituationState.START_TRAINING:
            # START_TRAINING state, initializing the training session
            logger.info("Starting training session...")
            self.is_session_active = True
            self.current_trial_start_time = datetime.now().strftime("%H:%M:%S")
            self.open_realtime_csv(phase_name=self.trainer_name)
            self.current_trial = 0
            self.state = HabituationState.START_TRIAL

        elif self.state == HabituationState.START_TRIAL:
            # START_TRIAL state, preparing for the next trial
            self.current_trial += 1
            if self.current_trial < self.num_trials:
                logger.info(f"Starting trial {self.current_trial}...")
                self.current_trial_start_time = datetime.now().strftime("%H:%M:%S")
                self.state = HabituationState.DELIVER_REWARD_START
            else:
                # All trials completed, move to end training state
                logger.info("All trials completed.")
                self.state = HabituationState.END_TRAINING

        elif self.state == HabituationState.DELIVER_REWARD_START:
            # DELIVER_REWARD_START state, preparing to deliver the reward
            self.reward_start_time = current_time
            logger.info(f"Preparing to deliver reward for trial {self.current_trial}...")
            self.chamber.reward.dispense()
            self.chamber.reward_led.activate()
            self.chamber.beambreak.activate()
            self.state = HabituationState.DELIVERING_REWARD

        elif self.state == HabituationState.DELIVERING_REWARD:
            # DELIVERING_REWARD state, dispensing the reward
            if current_time - self.reward_start_time < self.pump_secs:
                if self.chamber.beambreak.sensor_state==False and not self.reward_collected:
                    # Beam break detected during reward dispense
                    self.reward_collected = True
                    logger.info("Beam broken during reward dispense")
                    self.chamber.beambreak.deactivate()
                    self.chamber.reward_led.deactivate()
            else:
                # Reward finished dispensing
                logger.info(f"Reward dispense time of {self.pump_secs} seconds completed")
                self.chamber.reward.stop()
                self.state = HabituationState.POST_REWARD

        elif self.state == HabituationState.POST_REWARD:
            # POST_REWARD state, waiting for beam break or timeout
            if (current_time - self.reward_start_time) < self.beam_break_wait_time:
                if not self.reward_collected and self.chamber.beambreak.sensor_state==False:
                    # Beam break detected after reward dispense
                    self.reward_collected = True
                    logger.info("Beam broken after reward dispense")
                    self.chamber.reward_led.deactivate()
                    self.state = HabituationState.ITI_START
            else:
                    logger.info(f"Beam break wait time of {self.beam_break_wait_time} seconds exceeded")
                    self.chamber.reward_led.deactivate()
                    self.state = HabituationState.ITI_START
        
        elif self.state == HabituationState.ITI_START:
            # ITI_START state, preparing for the ITI period
            logger.info(f"Preparing for ITI for trial {self.current_trial}...")
            self.chamber.beambreak.activate()
            self.chamber.reward_led.deactivate()
            self.current_trial_iti = self.iti_duration
            self.iti_start_time = current_time
            self.state = HabituationState.ITI
        
        elif self.state == HabituationState.ITI:
            # ITI state, waiting for the ITI duration
            if current_time - self.iti_start_time < self.current_trial_iti:
                # Check if beam break is detected during ITI
                if self.chamber.beambreak.sensor_state==False:
                    logger.info("Beam broken during ITI. Adding 1 second to ITI duration.")
                    if self.current_trial_iti < self.max_iti_duration:
                        self.current_trial_iti += 1
            else:
                logger.info(f"ITI duration of {self.current_trial_iti} seconds completed")
                self.state = HabituationState.END_TRIAL
        
        elif self.state == HabituationState.END_TRIAL:
            # END_TRIAL state, finalizing the trial
            logger.info(f"Ending trial {self.current_trial}...")
            self.current_trial_end_time = datetime.now().strftime("%H:%M:%S")
            self.trial_data.append({
                "ID": self.trainer_name,
                "TrialNumber": self.current_trial,
                "StartTraining": self.current_trial_start_time,
                "EndTraining": self.current_trial_end_time,
                "Reward": self.reward_collected,
                "InitiationTime": self.iti_start_time,
                "StartTraining": self.current_trial_start_time,
                "EndTraining": self.current_trial_end_time
            })
            self._write_realtime_csv_row(self.trial_data[-1])
            self.state = HabituationState.START_TRIAL

        elif self.state == HabituationState.END_TRAINING:
            # End the training session
            logger.info("Ending training session...")
            self.is_session_active = False
            # self.close_realtime_csv()
            self.state = HabituationState.IDLE
            self.stop_training()

    def stop_training(self):
        # Stop the training session
        logger.info("Stopping training session...")
        self.chamber.reward.stop()
        self.chamber.reward_led.deactivate()
        self.chamber.beambreak.deactivate()
        self.state = HabituationState.IDLE