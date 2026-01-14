"""
General Template for Testing Any Trainer with Virtual Chamber

Use this template to test any of your state machines:
- Habituation
- InitialTouch
- MustTouch
- Simple_Discrimination
- Complex_Discrimination
- PRL
etc.
"""

import sys
import os
import time
import threading

# Add Controller to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Controller'))

import logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s:%(levelname)s] %(message)s'
)

from Virtual.VirtualChamber import VirtualChamber
from Virtual.VirtualChamberGUI import VirtualChamberGUI

# Import your trainer here
# from Habituation import Habituation
# from InitialTouch import InitialTouch
# from MustTouch import MustTouch
# from PRL import PRL
# etc.


def test_trainer_with_gui(TrainerClass, trainer_config=None, chamber_config=None):
    """Test any trainer with the GUI."""
    print("\n" + "="*70)
    print(f"  {TrainerClass.__name__.upper()} - VIRTUAL CHAMBER TEST")
    print("="*70)
    
    # Setup chamber
    print("Creating virtual chamber...")
    chamber = VirtualChamber(chamber_config=chamber_config or {})
    chamber.initialize_m0s()
    chamber.beambreak.activate()
    
    # Init trainer
    print(f"Initializing {TrainerClass.__name__} trainer...")
    trainer = TrainerClass(
        chamber=chamber,
        trainer_config=trainer_config or {}
    )
    
    print("\n" + "="*70)
    print("  QUICK START:")
    print("="*70)
    print("• Click touchscreens when stimuli show up")
    print("• Hit 'Break Beam' to simulate reward collection")
    print("• Watch the console for state changes")
    print("• Close the window when done")
    print("="*70 + "\n")
    
    input("Press ENTER to start training...")
    
    # Training loop - mirrors what Session does
    def training_loop():
        trainer.start_training()  # Initialize training
        run_interval = 0.1  # Same as Session default
        
        while True:
            try:
                trainer.run_training()
                time.sleep(run_interval)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Training error: {e}")
                break
    
    training_thread = threading.Thread(target=training_loop, daemon=True)
    training_thread.start()
    
    # GUI needs to run in main thread
    print("Starting GUI...\n")
    gui = VirtualChamberGUI(chamber)
    gui.run()  # Blocking call in main thread
    
    print(f"\n{TrainerClass.__name__} test complete!")


def main():
    """Just uncomment whichever trainer you wanna test."""
    
    # Configure image directory (where your BMP files are stored)
    # By default, it looks in: <project_root>/data/images/
    # You can override it like this:
    chamber_config = {
        # \"image_dir\": \"/path/to/your/bmp/files\",  # Uncomment to use custom path
    }
    
    # Example 1: Test Habituation
    # from Habituation import Habituation
    # test_trainer_with_gui(Habituation, 
    #     trainer_config={
    #         \"trainer_name\": \"Habituation\",
    #         \"rodent_name\": \"VirtualRat\",
    #         \"num_trials\": 5,
    #         \"reward_duration\": 0.5,
    #         \"iti_duration\": 5,
    #     },
    #     chamber_config=chamber_config
    # )
    
    # Example 2: Test InitialTouch
    # from InitialTouch import InitialTouch
    # test_trainer_with_gui(InitialTouch, 
    #     trainer_config={
    #         "trainer_name": "InitialTouch",
    #         "rodent_name": "VirtualRat",
    #         "num_trials": 10,
    #         "touch_timeout": 30,
    #     },
    #     chamber_config=chamber_config
    # )
    
    # Example 3: Test MustTouch
    # from MustTouch import MustTouch
    # test_trainer_with_gui(MustTouch, 
    #     trainer_config={
    #         "trainer_name": "MustTouch",
    #         "rodent_name": "VirtualRat",
    #         "num_trials": 20,
    #     },
    #     chamber_config=chamber_config
    # )

    # Example 4: Test PRL
    from PRL import PRL
    test_trainer_with_gui(PRL, 
        trainer_config={
            "trainer_name": "PRL",
            "rodent_name": "VirtualRat",
            "num_trials": 10,
            "iti_duration": 5,
            "reward_duration": 0.5,
        },
        chamber_config=chamber_config
    )
    
    # Example 5: Test punish incorrect
    # from Punish_Incorrect import PunishIncorrect
    # test_trainer_with_gui(PunishIncorrect, 
    #     trainer_config={
    #         "trainer_name": "PunishIncorrect",
    #         "rodent_name": "VirtualRat",
    #         "num_trials": 10,
    #         "initiation_timeout": 15,
    #         "iti_duration": 5,
    #         "trainer_seq_file": "scripts/seq_file.csv",
    #     },
    #     chamber_config=chamber_config
    # )



if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted. Goodbye!")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
