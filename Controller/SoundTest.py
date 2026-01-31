import time
from enum import Enum, auto
from Trainer import Trainer
import logging

logger = logging.getLogger(f"session_logger.{__name__}")

class SoundTestState(Enum):
    """Enum for different states in the sound test."""
    IDLE = auto()
    START_LOOP = auto()
    HOUSE_LIGHT = auto()
    REWARD_LED = auto()
    PUNISHMENT_LED = auto()
    BUZZER_60 = auto()
    IMAGES = auto()
    REWARD = auto()
    END_LOOP = auto()
    END_TRAINING = auto()

class SoundTest(Trainer):
    """
    SoundTest trainer for hardware verification.
    Cycles through hardware activations for 10s each.
    """
    def __init__(self, chamber, trainer_config={}, trainer_config_file='~/trainer_SoundTest_config.yaml'):
        super().__init__(chamber=chamber, trainer_config=trainer_config, trainer_config_file=trainer_config_file)

        self.config.ensure_param("trainer_name", "SoundTest")
        self.config.ensure_param("num_loops", 5)
        self.config.ensure_param("step_duration", 10.0)

        self.state_start_time = time.time()
        self.current_loop = 0
        self.state = SoundTestState.IDLE

    def start_training(self):
        logger.info("Starting sound test session...")
        self.chamber.default_state()
        self.open_data_file()
        self.state = SoundTestState.START_LOOP
        self.current_loop = 0

    def check_duration(self, duration):
        """Check if the duration has passed since state_start_time."""
        return (time.time() - self.state_start_time) >= duration

    def run_training(self):
        """Main loop for running the test session."""
        current_time = time.time()

        if self.state == SoundTestState.IDLE:
            pass

        elif self.state == SoundTestState.START_LOOP:
            self.chamber.m0_clear()
            self.current_loop += 1
            if self.current_loop <= self.config["num_loops"]:
                logger.info(f"Starting loop {self.current_loop}")
                self.write_event("StartLoop", self.current_loop)
                self.state = SoundTestState.HOUSE_LIGHT
            else:
                self.state = SoundTestState.END_TRAINING

        elif self.state == SoundTestState.HOUSE_LIGHT:
            if not getattr(self, 'house_light_active', False):
                logger.info("House Light ON")
                self.write_event("HouseLight", "ON")
                self.chamber.house_led.set_brightness(255)
                self.chamber.house_led.activate()
                self.house_light_active = True
                self.state_start_time = current_time
            
            if self.check_duration(self.config["step_duration"]):
                logger.info("House Light OFF")
                self.write_event("HouseLight", "OFF")
                self.chamber.house_led.deactivate()
                self.house_light_active = False
                self.state = SoundTestState.REWARD_LED

        elif self.state == SoundTestState.REWARD_LED:
            if not getattr(self, 'reward_led_active', False):
                logger.info("Reward LED ON")
                self.write_event("RewardLED", "ON")
                self.chamber.reward_led.activate()
                self.reward_led_active = True
                self.state_start_time = current_time

            if self.check_duration(self.config["step_duration"]):
                logger.info("Reward LED OFF")
                self.write_event("RewardLED", "OFF")
                self.chamber.reward_led.deactivate()
                self.reward_led_active = False
                self.state = SoundTestState.PUNISHMENT_LED

        elif self.state == SoundTestState.PUNISHMENT_LED:
            if not getattr(self, 'punishment_led_active', False):
                logger.info("Punishment LED ON")
                self.write_event("PunishmentLED", "ON")
                self.chamber.punishment_led.activate()
                self.punishment_led_active = True
                self.state_start_time = current_time

            if self.check_duration(self.config["step_duration"]):
                logger.info("Punishment LED OFF")
                self.write_event("PunishmentLED", "OFF")
                self.chamber.punishment_led.deactivate()
                self.punishment_led_active = False
                self.state = SoundTestState.BUZZER_60


        elif self.state == SoundTestState.BUZZER_60:
            if not getattr(self, 'buzzer_60_active', False):
                logger.info("Buzzer 60% Volume ON")
                self.write_event("Buzzer60", "ON")
                self.chamber.buzzer.volume = 60
                self.chamber.buzzer.activate()
                self.buzzer_60_active = True
                self.state_start_time = current_time

            if self.check_duration(self.config["step_duration"]):
                logger.info("Buzzer 60% Volume OFF")
                self.write_event("Buzzer60", "OFF")
                self.chamber.buzzer.deactivate()
                self.buzzer_60_active = False
                self.state = SoundTestState.IMAGES



        elif self.state == SoundTestState.IMAGES:
            if not getattr(self, 'images_active', False):
                logger.info("Images ON")
                self.write_event("Images", "ON")
                self.chamber.m0_show_image()
                self.images_active = True
                self.state_start_time = current_time

            if self.check_duration(self.config["step_duration"]):
                logger.info("Images OFF")
                self.write_event("Images", "OFF")
                self.chamber.m0_clear()
                self.images_active = False
                self.state = SoundTestState.REWARD

        elif self.state == SoundTestState.REWARD:
            if not getattr(self, 'reward_active', False):
                logger.info("Reward Dispense ON")
                self.write_event("Reward", "ON")
                self.chamber.reward.dispense()
                self.reward_active = True
                self.state_start_time = current_time

            if self.check_duration(self.config["step_duration"]):
                logger.info("Reward Dispense OFF")
                self.write_event("Reward", "OFF")
                self.chamber.reward.stop()
                self.reward_active = False
                self.state = SoundTestState.END_LOOP

        elif self.state == SoundTestState.END_LOOP:
            self.write_event("EndLoop", self.current_loop)
            self.state = SoundTestState.START_LOOP

        elif self.state == SoundTestState.END_TRAINING:
            logger.info("Sound test completed.")
            self.write_event("EndTraining", 1)
            self.stop_training()

    def stop_training(self):
        logger.info("Stopping sound test...")
        self.chamber.default_state()
        self.close_data_file()
        self.state = SoundTestState.IDLE
