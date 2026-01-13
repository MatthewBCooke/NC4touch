# Virtual Touchscreen Chamber System

## Overview

The Virtual Chamber system allows you to test your touchscreen chamber training protocols **without physical hardware**. This is invaluable for:

- ✅ Developing and debugging training state machines
- ✅ Testing trial sequences and logic
- ✅ Training new lab members
- ✅ Rapid prototyping of new training protocols
- ✅ Continuous integration testing

## Quick Start

### 1. Basic Usage

```python
from Virtual.VirtualChamber import VirtualChamber

# Create virtual chamber
chamber = VirtualChamber()
chamber.initialize_m0s()

# Use exactly like physical chamber
chamber.reward_led.on()
chamber.reward.dispense()
chamber.left_m0.send_command("DISPLAY:image.bmp")

# Simulate user interactions
chamber.left_m0.simulate_touch(160, 240)
chamber.beambreak.simulate_break()
```

### 2. Using with Session (Recommended)

```python
from Session import Session

# Enable virtual mode in configuration
session_config = {
    "virtual_mode": True,
    "trainer_name": "InitialTouch",
    "rodent_name": "VirtualRat"
}

# Session will automatically use VirtualChamber
session = Session(session_config=session_config)
```

Or use a YAML config file:

```yaml
# session_config.yaml
virtual_mode: true
trainer_name: "InitialTouch"
rodent_name: "VirtualRat001"
```

```python
session = Session(session_config_file='session_config.yaml')
```

### 3. Interactive GUI Testing

```python
from Virtual.VirtualChamber import VirtualChamber
from Virtual.VirtualChamberGUI import VirtualChamberGUI

chamber = VirtualChamber()
chamber.initialize_m0s()

# Launch interactive GUI
gui = VirtualChamberGUI(chamber)
gui.run()  # Blocking, or use gui.run_async() for background
```

## Architecture

### Virtual Hardware Components

All virtual components maintain **identical APIs** to their physical counterparts:

#### VirtualM0Device
- Simulates Arduino M0 touchscreen controllers
- Methods: `initialize()`, `send_command()`, `is_touched()`
- Virtual methods: `simulate_touch(x, y, duration)`, `get_current_image()`

#### VirtualBeamBreak
- Simulates IR beam break sensor in food hopper
- Methods: `activate()`, `deactivate()`, `state`
- Virtual methods: `simulate_break(duration)`, `simulate_restore()`

#### VirtualLED
- Simulates LED lights (reward & punishment)
- Methods: `on(brightness)`, `off()`, `set_color(r, g, b)`
- Virtual methods: `get_state()`

#### VirtualBuzzer
- Simulates audio buzzer
- Methods: `activate()`, `deactivate()`, `set_frequency()`
- Virtual methods: `get_state()`

#### VirtualReward
- Simulates food pump
- Methods: `dispense()`, `stop()`
- Virtual methods: `get_state()`, `reset_counter()`

### VirtualChamber

Complete virtualized chamber matching the `Chamber` class interface:

```python
chamber = VirtualChamber()

# Same interface as Chamber
chamber.left_m0      # VirtualM0Device
chamber.middle_m0    # VirtualM0Device
chamber.right_m0     # VirtualM0Device
chamber.reward       # VirtualReward
chamber.beambreak    # VirtualBeamBreak
chamber.reward_led   # VirtualLED
chamber.punishment_led # VirtualLED
chamber.buzzer       # VirtualBuzzer
```

## Testing Your Trainers

### Example: Testing InitialTouch

```python
from Session import Session
from Virtual.VirtualChamberGUI import VirtualChamberGUI
import threading

# Create virtual session
session = Session(session_config={
    "virtual_mode": True,
    "trainer_name": "InitialTouch",
    "rodent_name": "TestRat"
})

# Launch GUI for interaction
gui = VirtualChamberGUI(session.chamber)
gui_thread = gui.run_async()

# Start training
session.start_session()

# Interact via GUI:
# - Click touchscreens when stimuli appear
# - Click "Break Beam" to simulate eating
# - Watch trial progression
```

### Example: Automated Testing

```python
from Virtual.VirtualChamber import VirtualChamber
import time

def test_must_touch_logic():
    """Automated test for MustTouch trainer."""
    chamber = VirtualChamber()
    chamber.initialize_m0s()
    
    # Your trainer logic here
    # ...
    
    # Simulate animal behavior
    chamber.left_m0.simulate_touch(160, 240)
    time.sleep(0.1)
    
    # Verify expected outcome
    assert chamber.reward.get_state()['total_dispensed'] == 1
    assert chamber.beambreak.state == 0  # Should be waiting at hopper
    
    print("✓ Test passed!")
```

## GUI Controls

The Virtual Chamber GUI provides:

### Touchscreens
- **Click on screen**: Simulate touch at that location
- **"Simulate Touch" button**: Touch at center (160, 240)
- Visual feedback shows current image and touch state

### Beam Break
- **"Break Beam"**: Simulate animal at food hopper
- **"Restore Beam"**: Simulate animal leaving hopper
- Status indicator shows current state

### Monitoring
- Real-time LED states (reward/punishment)
- Buzzer activity indicator
- Reward pump status and counter
- Status log with timestamps

### Debug
- **"Get Chamber State"**: Print complete chamber state
- **"Clear Log"**: Clear status log window

## Advanced Usage

### State Tracking

```python
# Get complete chamber state
state = chamber.get_state()

# Returns dictionary with:
# - All M0 touch states and images
# - LED states and brightness
# - Beam break status
# - Buzzer activity
# - Reward count and status

# Track state over time
chamber.log_state()
history = chamber.get_state_history()
```

### Custom Simulation Sequences

```python
import time

def simulate_correct_trial(chamber):
    """Simulate an animal completing a correct trial."""
    # Stimuli presented
    chamber.left_m0.send_command("DISPLAY:plus.bmp")
    chamber.right_m0.send_command("DISPLAY:minus.bmp")
    
    # Animal chooses left (correct)
    time.sleep(1)
    chamber.left_m0.simulate_touch(160, 240, duration=0.2)
    
    # Reward delivered
    chamber.reward_led.on()
    chamber.reward.dispense()
    time.sleep(0.5)
    chamber.reward.stop()
    
    # Animal eats reward
    chamber.beambreak.simulate_break(duration=2.0)
    time.sleep(2)
    
    # Cleanup
    chamber.reward_led.off()
    chamber.left_m0.send_command("CLEAR")
    chamber.right_m0.send_command("CLEAR")
```

### Integration with Existing Code

**No code changes required!** The virtual components implement the same interface as physical hardware:

```python
# This code works with BOTH physical and virtual chambers:
def run_trial(chamber):
    chamber.reward_led.on()
    chamber.left_m0.send_command("DISPLAY:stim.bmp")
    
    # Wait for touch...
    while not chamber.left_m0.is_touched:
        time.sleep(0.1)
    
    chamber.reward.dispense()
    # ... etc
```

## Troubleshooting

### Import Errors

Make sure you're running from the correct directory:

```python
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Controller'))
```

### GUI Not Appearing

On some systems, you may need to run in the main thread:

```python
# Instead of gui.run_async()
gui.run()  # Blocking call
```

### Testing Without GUI

You can test completely headless:

```python
chamber = VirtualChamber()
# No GUI needed - just simulate interactions programmatically
chamber.left_m0.simulate_touch(160, 240)
```

## Example Test Scripts

See [`scripts/test_virtual_chamber.py`](../scripts/test_virtual_chamber.py) for comprehensive examples:

```bash
# Run from project root
cd NC4touch
python scripts/test_virtual_chamber.py
```

## Next Steps

1. **Test an existing trainer** - Try running InitialTouch or MustTouch in virtual mode
2. **Develop new protocols** - Create and test new training state machines
3. **Automate testing** - Write unit tests for your trainer logic
4. **Train users** - Use virtual chamber for training new lab members

## Tips

- Use the GUI for **interactive development** and debugging
- Use programmatic control for **automated testing** and CI/CD
- Enable `virtual_mode` in your config file for easy toggling
- Check the status log in the GUI for detailed event tracking
- Use `get_state()` to inspect chamber state at any point

---

**Happy Virtual Testing!** 🖥️🐀
