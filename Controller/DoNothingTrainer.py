from Trainer import Trainer
from Chamber import Chamber

class DoNothingTrainer(Trainer):
    """
    A trainer that does nothing. This is useful for testing purposes.
    """
    def __init__(self, trainer_config = {}, chamber = None):
        super().__init__(trainer_config, chamber)
        self.trainer_name = "DoNothingTrainer"

    def start_training(self):
        """Start the training session."""
        print(f"{self.trainer_name}: Training started.")
    
    def run_training(self):
        """Run the training session."""
        print(f"{self.trainer_name}: Running training session...")

    def stop_training(self):
        """Stop the training session."""
        print(f"{self.trainer_name}: Training stopped.")
