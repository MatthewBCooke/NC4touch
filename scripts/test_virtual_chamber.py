"""
Virtual Chamber Test Script

This script demonstrates how to use the virtual chamber for testing
your training protocols without physical hardware.

Usage:
    python test_virtual_chamber.py
"""

import sys
import os
import time

# Add Controller directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Controller'))

from Virtual.VirtualChamber import VirtualChamber
from Virtual.VirtualChamberGUI import VirtualChamberGUI
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s:%(name)s:%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


def test_basic_operations():
    """Test basic virtual chamber operations."""
    print("\n" + "="*60)
    print("TEST 1: Basic Virtual Chamber Operations")
    print("="*60)

    # Create virtual chamber
    chamber = VirtualChamber()

    # Initialize M0 devices
    chamber.initialize_m0s()

    # Test LED control
    print("\n--- Testing LEDs ---")
    chamber.reward_led.on(brightness=200)
    time.sleep(1)
    chamber.reward_led.off()

    chamber.punishment_led.on(brightness=255)
    time.sleep(1)
    chamber.punishment_led.off()

    # Test buzzer
    print("\n--- Testing Buzzer ---")
    chamber.buzzer.activate()
    time.sleep(0.5)
    chamber.buzzer.deactivate()

    # Test reward pump
    print("\n--- Testing Reward Pump ---")
    chamber.reward.dispense()
    time.sleep(0.5)
    chamber.reward.stop()

    # Test beam break
    print("\n--- Testing Beam Break ---")
    chamber.beambreak.activate()
    print(f"Initial beam state: {chamber.beambreak.get_state()}")
    
    chamber.beambreak.simulate_break()
    time.sleep(0.1)
    print(f"After break: {chamber.beambreak.get_state()}")
    
    chamber.beambreak.simulate_restore()
    time.sleep(0.3)
    print(f"After restore: {chamber.beambreak.get_state()}")

    # Test touchscreens
    print("\n--- Testing Touchscreens ---")
    chamber.left_m0.send_command("DISPLAY:/path/to/image.bmp")
    chamber.left_m0.simulate_touch(160, 240, duration=0.2)
    time.sleep(0.3)

    # Get final state
    print("\n--- Final Chamber State ---")
    state = chamber.get_state()
    print(f"Reward count: {state['reward']['total_dispensed']}")
    print(f"Left screen image: {state['left_m0']['current_image']}")

    print("\n✓ Basic operations test completed!")


def test_with_gui():
    """Test virtual chamber with interactive GUI."""
    print("\n" + "="*60)
    print("TEST 2: Virtual Chamber with GUI")
    print("="*60)
    print("\nLaunching Virtual Chamber GUI...")
    print("Instructions:")
    print("  - Click on touchscreens to simulate touches")
    print("  - Use 'Break Beam' button to simulate animal at hopper")
    print("  - Watch LED/buzzer states update in real-time")
    print("  - Close the GUI window when done")
    print()

    # Create virtual chamber
    chamber = VirtualChamber()
    chamber.initialize_m0s()
    chamber.beambreak.activate()

    # Create and run GUI
    gui = VirtualChamberGUI(chamber)
    
    # Simulate some activity to demonstrate
    def demo_activity():
        time.sleep(2)
        logger.info("Simulating demo activity...")
        
        # Display images
        chamber.left_m0.send_command("DISPLAY:stimulus_left.bmp")
        chamber.right_m0.send_command("DISPLAY:stimulus_right.bmp")
        time.sleep(1)
        
        # Reward LED on
        chamber.reward_led.on()
        time.sleep(2)
        chamber.reward_led.off()
        
        logger.info("Demo complete - now you can interact with the GUI")

    import threading
    demo_thread = threading.Thread(target=demo_activity, daemon=True)
    demo_thread.start()

    # Run GUI (blocking)
    gui.run()

    print("\n✓ GUI test completed!")


def test_session_integration():
    """Test virtual chamber integration with Session."""
    print("\n" + "="*60)
    print("TEST 3: Session Integration with Virtual Chamber")
    print("="*60)

    try:
        from Session import Session

        # Create session with virtual mode enabled
        session_config = {
            "virtual_mode": True,
            "trainer_name": "DoNothingTrainer",
            "rodent_name": "VirtualRodent",
            "chamber_name": "VirtualChamber0"
        }

        print("\nCreating session with virtual_mode=True...")
        session = Session(session_config=session_config)

        print(f"Chamber type: {type(session.chamber).__name__}")
        print(f"Chamber name: {session.chamber.config['chamber_name']}")

        # Test that trainer can interact with virtual chamber
        print("\nTesting trainer-chamber interaction...")
        session.chamber.reward_led.on()
        time.sleep(0.5)
        session.chamber.reward_led.off()

        print("\n✓ Session integration test completed!")

    except Exception as e:
        print(f"\n✗ Session integration test failed: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("  VIRTUAL CHAMBER TEST SUITE")
    print("="*70)

    tests = [
        ("Basic Operations", test_basic_operations),
        ("GUI Interface", test_with_gui),
        ("Session Integration", test_session_integration),
    ]

    print("\nAvailable tests:")
    for i, (name, _) in enumerate(tests, 1):
        print(f"  {i}. {name}")
    print(f"  {len(tests)+1}. Run all tests")

    choice = input(f"\nSelect test to run (1-{len(tests)+1}): ").strip()

    try:
        choice_num = int(choice)
        if 1 <= choice_num <= len(tests):
            tests[choice_num - 1][1]()
        elif choice_num == len(tests) + 1:
            for name, test_func in tests:
                test_func()
        else:
            print("Invalid choice")
    except ValueError:
        print("Invalid input")
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
