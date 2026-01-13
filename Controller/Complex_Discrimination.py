from enum import Enum, auto
from random import random
import time
import logging
from Trainer import Trainer

logger = logging.getLogger(f"session_logger.{__name__}")

class SDState(Enum):
    IDLE = auto()
    START_TRAINING = auto()
    START_TRIAL = auto()
    INITIATION = auto()
    SHOW_STIMULI = auto()
    WAIT_FOR_TOUCH = auto()
    CORRECT = auto()
    ERROR = auto()
    ITI_START = auto()
    ITI = auto()
    END_TRIAL = auto()
    END_TRAINING = auto()

class SimpleDiscrimination(Trainer):

    CORRECT_IMAGE = "E01"
    INCORRECT_IMAGE = "D01"

    def __init__(self, chamber, trainer_config={}, trainer_config_file="~/trainer_SD_config.yaml"):
        super().__init__(chamber, trainer_config, trainer_config_file)

        self.config.ensure_param("trainer_name", "Simple Discrimination")
        self.config.ensure_param("num_trials", 60)
        self.config.ensure_param("reward_pump_secs", 3.5)
        self.config.ensure_param("beam_break_wait_time", 10)
        self.config.ensure_param("iti_duration", 10)
        self.config.ensure_param("max_corrections", 3)
        self.config.ensure_param("touch_timeout", 300)

        self.state = SDState.IDLE
        self.current_trial = 0
        self.correction_count = 0

        self.left_image = None
        self.right_image = None

    # ---------- helper methods ----------

    def randomize_images(self):
        """Randomly assign correct/incorrect images to left/right."""
        if random() < 0.5:
            self.left_image = self.CORRECT_IMAGE
            self.right_image = self.INCORRECT_IMAGE
        else:
            self.left_image = self.INCORRECT_IMAGE
            self.right_image = self.CORRECT_IMAGE

    def load_images(self):
        self.chamber.left_m0.send_command(f"IMG:{self.left_image}")
        self.chamber.right_m0.send_command(f"IMG:{self.right_image}")

    def show_images(self):
        self.chamber.left_m0.send_command("SHOW")
        self.chamber.right_m0.send_command("SHOW")

    def clear_images(self):
        self.chamber.left_m0.send_command("BLACK")
        self.chamber.right_m0.send_command("BLACK")

    # ---------- session control ----------

    def start_training(self):
        logger.info("Starting Simple Discrimination (no punishment)")
        self.chamber.default_state()
        self.open_data_file()
        self.state = SDState.START_TRAINING

    def run_training(self):
        now = time.time()

        if self.state == SDState.START_TRAINING:
            self.current_trial = 0
            self.state = SDState.START_TRIAL

        elif self.state == SDState.START_TRIAL:
            self.current_trial += 1
            self.correction_count = 0

            if self.current_trial > self.config["num_trials"]:
                self.state = SDState.END_TRAINING
                return

            # randomize ONLY on first attempt
            self.randomize_images()
            self.load_images()

            if self.current_trial == 1:
                self.free_reward()
                self.state = SDState.SHOW_STIMULI
            else:
                self.state = SDState.INITIATION

        elif self.state == SDState.INITIATION:
            if self.wait_for_trial_initiation():
                self.state = SDState.SHOW_STIMULI

        elif self.state == SDState.SHOW_STIMULI:
            self.show_images()
            self.trial_start_time = now
            self.state = SDState.WAIT_FOR_TOUCH

        elif self.state == SDState.WAIT_FOR_TOUCH:
            if now - self.trial_start_time > self.config["touch_timeout"]:
                self.state = SDState.ITI_START
                return

            side = self.check_touch()
            if side is None:
                return

            if side == "LEFT":
                touched_image = self.left_image
            elif side == "RIGHT":
                touched_image = self.right_image
            else:
                return

            if touched_image == self.CORRECT_IMAGE:
                self.state = SDState.CORRECT
            else:
                self.state = SDState.ERROR

        elif self.state == SDState.CORRECT:
            self.clear_images()
            self.deliver_reward()

            self.write_trial_data({
                "trial": self.current_trial,
                "outcome": "correct",
                "corrections": self.correction_count,
                "rt": now - self.trial_start_time
            })

            self.state = SDState.ITI_START

        elif self.state == SDState.ERROR:
            self.clear_images()
            self.correction_count += 1

            if self.correction_count < self.config["max_corrections"]:
                # correction trial: DO NOT randomize again
                self.load_images()
                self.state = SDState.SHOW_STIMULI
            else:
                self.write_trial_data({
                    "trial": self.current_trial,
                    "outcome": "incorrect",
                    "corrections": self.correction_count,
                    "rt": None
                })
                self.state = SDState.ITI_START

        elif self.state == SDState.ITI_START:
            self.iti_start_time = now
            self.state = SDState.ITI

        elif self.state == SDState.ITI:
            if now - self.iti_start_time >= self.config["iti_duration"]:
                self.state = SDState.END_TRIAL

        elif self.state == SDState.END_TRIAL:
            self.state = SDState.START_TRIAL

        elif self.state == SDState.END_TRAINING:
            self.stop_training()
