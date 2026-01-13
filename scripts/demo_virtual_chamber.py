"""
Simple Virtual Chamber Demo

A minimal example showing virtual chamber usage.
Great for quick testing and learning the system.
"""

import sys
import os
import time

# Add Controller to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Controller'))

import logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

from Virtual.VirtualChamber import VirtualChamber
from Virtual.VirtualChamberGUI import VirtualChamberGUI


def simple_demo():
    """Simple demonstration of virtual chamber."""
    print("\n" + "="*60)
    print("  SIMPLE VIRTUAL CHAMBER DEMO")
    print("="*60 + "\n")

    # Create and initialize virtual chamber
    print("Creating virtual chamber...")
    chamber = VirtualChamber()
    chamber.initialize_m0s()
    chamber.beambreak.activate()

    # Test each component
    print("\n1. Testing LEDs...")
    print("   - Reward LED ON")
    chamber.reward_led.on(brightness=200)
    time.sleep(1)
    print("   - Reward LED OFF")
    chamber.reward_led.off()
    time.sleep(0.5)

    print("\n2. Testing Buzzer...")
    print("   - Buzzer activated (1 second)")
    chamber.buzzer.activate()
    time.sleep(1)
    chamber.buzzer.deactivate()
    time.sleep(0.5)

    print("\n3. Testing Touchscreens...")
    print("   - Displaying images on left and right screens")
    chamber.left_m0.send_command("DISPLAY:/data/images/stimulus_left.bmp")
    chamber.right_m0.send_command("DISPLAY:/data/images/stimulus_right.bmp")
    time.sleep(1)

    print("   - Simulating touch on LEFT screen")
    chamber.left_m0.simulate_touch(160, 240, duration=0.3)
    time.sleep(0.5)

    print("\n4. Testing Reward System...")
    print("   - Dispensing reward")
    chamber.reward.dispense()
    time.sleep(0.5)
    chamber.reward.stop()
    
    print("   - Simulating beam break (animal eating)")
    chamber.beambreak.simulate_break()
    time.sleep(1)
    chamber.beambreak.simulate_restore()
    time.sleep(0.5)

    print("\n5. Getting chamber state...")
    state = chamber.get_state()
    print(f"   - Total rewards dispensed: {state['reward']['total_dispensed']}")
    print(f"   - Left screen image: {state['left_m0']['current_image']}")
    print(f"   - Beam break state: {'BROKEN' if state['beambreak']['state'] == 0 else 'OK'}")

    print("\n" + "="*60)
    print("  DEMO COMPLETED SUCCESSFULLY!")
    print("="*60 + "\n")


def interactive_demo():
    """Interactive demo with GUI."""
    print("\n" + "="*60)
    print("  INTERACTIVE VIRTUAL CHAMBER DEMO")
    print("="*60 + "\n")
    
    print("Creating virtual chamber with GUI...\n")
    
    # Create chamber
    chamber = VirtualChamber()
    chamber.initialize_m0s()
    chamber.beambreak.activate()

    # Display some initial content
    chamber.left_m0.send_command("DISPLAY:left_stimulus.bmp")
    chamber.right_m0.send_command("DISPLAY:right_stimulus.bmp")

    print("GUI Controls:")
    print("  • Click on touchscreens to simulate touches")
    print("  • Use 'Break Beam' button to simulate animal at hopper")
    print("  • Use 'Restore Beam' to simulate animal leaving")
    print("  • Watch LED/buzzer states update in real-time")
    print("  • Click 'Get Chamber State' to see full state")
    print("\nClose the window to exit.\n")

    # Create and run GUI
    gui = VirtualChamberGUI(chamber)
    gui.run()

    print("\nGUI closed. Demo complete!")


def automated_trial_demo():
    """Demonstrate a complete automated trial."""
    print("\n" + "="*60)
    print("  AUTOMATED TRIAL DEMO")
    print("="*60 + "\n")

    chamber = VirtualChamber()
    chamber.initialize_m0s()
    chamber.beambreak.activate()

    print("Simulating a complete training trial...\n")

    # ITI
    print("[ITI] Inter-trial interval (3 seconds)")
    time.sleep(1)

    # Present stimuli
    print("[TRIAL START] Presenting stimuli")
    chamber.left_m0.send_command("DISPLAY:plus.bmp")
    chamber.right_m0.send_command("DISPLAY:minus.bmp")
    chamber.reward_led.on(brightness=100)  # House light
    time.sleep(1)

    # Animal makes choice (left = correct)
    print("[RESPONSE] Animal touches LEFT screen (correct!)")
    chamber.left_m0.simulate_touch(160, 240, duration=0.2)
    time.sleep(0.5)

    # Deliver reward
    print("[REWARD] Delivering reward")
    chamber.reward_led.on(brightness=255)  # Bright reward light
    chamber.reward.dispense()
    time.sleep(0.5)
    chamber.reward.stop()
    time.sleep(0.5)

    # Animal consumes reward
    print("[CONSUMPTION] Animal at hopper (beam broken)")
    chamber.beambreak.simulate_break()
    time.sleep(2)
    print("[CONSUMPTION] Animal leaves hopper (beam restored)")
    chamber.beambreak.simulate_restore()

    # Clear screens
    print("[CLEANUP] Clearing screens")
    chamber.left_m0.send_command("CLEAR")
    chamber.right_m0.send_command("CLEAR")
    chamber.reward_led.off()

    # Show results
    state = chamber.get_state()
    print(f"\n[RESULT] Trial complete!")
    print(f"  - Rewards dispensed: {state['reward']['total_dispensed']}")
    print(f"  - Choice: LEFT (correct)")
    print(f"  - Outcome: REWARDED")

    print("\n" + "="*60)
    print("  Trial simulation complete!")
    print("="*60 + "\n")


def main():
    """Main menu."""
    print("\n" + "="*70)
    print("  VIRTUAL CHAMBER DEMONSTRATION")
    print("="*70)
    
    print("\nChoose a demo:")
    print("  1. Simple Demo - Basic component testing")
    print("  2. Interactive Demo - GUI with manual control")
    print("  3. Automated Trial - Complete trial simulation")
    print("  4. Exit")

    choice = input("\nEnter choice (1-4): ").strip()

    if choice == "1":
        simple_demo()
    elif choice == "2":
        interactive_demo()
    elif choice == "3":
        automated_trial_demo()
    elif choice == "4":
        print("Goodbye!")
        return
    else:
        print("Invalid choice!")
        return

    # Ask if user wants to run another demo
    again = input("\nRun another demo? (y/n): ").strip().lower()
    if again == 'y':
        main()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted. Goodbye!")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
