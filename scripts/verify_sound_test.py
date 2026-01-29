import sys
import os
import time
import logging

# Add Controller to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Controller'))

from Virtual.VirtualChamber import VirtualChamber
from SoundTest import SoundTest, SoundTestState

# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')
logger = logging.getLogger("verify_sound_test")

def verify_sound_test():
    print("Initializing Virtual Chamber...")
    chamber = VirtualChamber()
    
    # Configure trainer with short duration for testing
    trainer_config = {
        "trainer_name": "SoundTest",
        "num_loops": 1,
        "step_duration": 0.1,  # Short duration for verification
        "rodent_name": "TestRodent"
    }
    
    print("Initializing SoundTest Trainer...")
    trainer = SoundTest(chamber, trainer_config=trainer_config)
    
    print("Starting Training...")
    try:
        trainer.start_training()
        
        # Run loop
        last_state = None
        start_time = time.time()
        
        while trainer.state != SoundTestState.IDLE:
            trainer.run_training()
            
            current_state = trainer.state
            if current_state != last_state:
                print(f"State transition: {last_state} -> {current_state}")
                last_state = current_state
                
            time.sleep(0.01)
            
            # Safety timeout
            if time.time() - start_time > 10: 
                print("Timeout reached!")
                break
                
        print("Test Complete.")
    except Exception as e:
        print(f"Error during verification: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_sound_test()
