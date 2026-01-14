"""
Example: Testing Simple Discrimination with Virtual Chamber

This demonstrates the complete workflow:
1. Setup BMP images
2. Create virtual chamber with custom image directory
3. Test trainer with GUI
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
from Simple_Discrimination import SimpleDiscrimination


def main():
    """Test Simple Discrimination with virtual chamber."""
    
    print("\n" + "="*70)
    print("  SIMPLE DISCRIMINATION - VIRTUAL CHAMBER TEST")
    print("="*70 + "\n")
    
    # 1. Configure chamber (including image directory)
    chamber_config = {
        "chamber_name": "VirtualTestChamber",
        # Uncomment to use custom image directory:
        # "image_dir": "/path/to/your/bmp/files",
    }
    
    # 2. Create virtual chamber
    print("Creating virtual chamber...")
    chamber = VirtualChamber(chamber_config=chamber_config)
    chamber.initialize_m0s()
    chamber.beambreak.activate()
    
    print(f"Image directory: {chamber.config['image_dir']}")
    print(f"Expected images: A01.bmp (correct), C01.bmp (incorrect)\n")
    
    # 3. Create trainer
    print("Initializing Simple Discrimination trainer...")
    trainer_config = {
        "trainer_name": "SimpleDiscrimination",
        "rodent_name": "VirtualRat001",
        "num_trials": 10,
        "reward_pump_secs": 2.0,
        "touch_timeout": 30,
        "iti_duration": 5,
    }
    
    trainer = SimpleDiscrimination(
        chamber=chamber,
        trainer_config=trainer_config
    )
    
    print("\n" + "="*70)
    print("  INSTRUCTIONS:")
    print("="*70)
    print("• The trainer will randomly place A01 (correct) and C01 (incorrect)")
    print("• Click the touchscreen with the CORRECT image (A01)")
    print("• When reward is given, click 'Break Beam' to simulate eating")
    print("• Watch console for trial feedback")
    print("• Close GUI window when done")
    print("="*70 + "\n")
    
    input("Press ENTER to start training...")
    
    # 4. Run trainer in background thread
    def training_loop():
        trainer.start_training()
        run_interval = 0.1
        
        while True:
            try:
                trainer.run_training()
                time.sleep(run_interval)
            except KeyboardInterrupt:
                break
            except Exception as e:
                logging.error(f"Training error: {e}", exc_info=True)
                break
    
    training_thread = threading.Thread(target=training_loop, daemon=True)
    training_thread.start()
    
    # 5. Launch GUI (runs in main thread)
    print("Starting GUI...\n")
    gui = VirtualChamberGUI(chamber)
    gui.run()  # Blocking
    
    print("\nTest complete!")
    print(f"Total trials completed: {trainer.current_trial}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted. Goodbye!")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
