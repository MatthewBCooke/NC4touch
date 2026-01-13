# Virtual Chamber System - Implementation Summary

## ✅ What Was Built

A complete virtualization system for your NC4touch touchscreen chambers that allows testing without physical hardware.

## 📂 New Files Created

### Core Virtual Components
- **`Controller/Virtual/VirtualM0Device.py`** - Virtual touchscreen controller
- **`Controller/Virtual/VirtualBeamBreak.py`** - Virtual IR beam sensor  
- **`Controller/Virtual/VirtualLED.py`** - Virtual LED controller
- **`Controller/Virtual/VirtualBuzzer.py`** - Virtual buzzer
- **`Controller/Virtual/VirtualReward.py`** - Virtual food pump
- **`Controller/Virtual/VirtualChamber.py`** - Complete virtual chamber
- **`Controller/Virtual/VirtualChamberGUI.py`** - Interactive GUI
- **`Controller/Virtual/__init__.py`** - Package initialization

### Documentation
- **`Controller/Virtual/README.md`** - Complete virtual system documentation
- **`VIRTUAL_CHAMBER_GUIDE.md`** - Quick start guide (root level)

### Example Scripts
- **`scripts/demo_virtual_chamber.py`** - Interactive demo with menu
- **`scripts/test_virtual_chamber.py`** - Comprehensive test suite
- **`scripts/virtual_chamber_config.yaml`** - Example configuration

## 🔧 Modified Files

### `Controller/Session.py`
Added virtual mode support:
- Imports `VirtualChamber`
- New config parameter: `virtual_mode` (default: `False`)
- Conditional chamber initialization based on `virtual_mode`

## 🎯 Key Features

### 1. **Identical API**
All virtual components implement the exact same interface as physical hardware:
```python
# Works with both physical and virtual chambers
chamber.reward_led.on()
chamber.left_m0.send_command("DISPLAY:image.bmp")
chamber.reward.dispense()
```

### 2. **Interactive GUI**
- Visual representation of 3 touchscreens
- Click to simulate touches
- Control beam break sensor
- Monitor LED states, buzzer, and reward pump in real-time
- Status log with timestamps

### 3. **Programmatic Control**
```python
# Simulate hardware events programmatically
chamber.left_m0.simulate_touch(160, 240, duration=0.2)
chamber.beambreak.simulate_break()
chamber.reward.dispense()
```

### 4. **State Tracking**
```python
# Get complete chamber state at any time
state = chamber.get_state()
# Includes all M0s, LEDs, beam break, buzzer, reward pump
```

### 5. **Session Integration**
```python
# Just set virtual_mode=True in your config!
session = Session(session_config={'virtual_mode': True})
# All your existing trainer code works unchanged
```

## 🚀 How to Use

### Method 1: Quick Demo
```bash
python scripts/demo_virtual_chamber.py
```

### Method 2: With Your Existing Session Code
```python
from Controller.Session import Session

session = Session(session_config={
    'virtual_mode': True,
    'trainer_name': 'InitialTouch',
    'rodent_name': 'VirtualRat'
})

session.start_session()
```

### Method 3: With GUI
```python
from Controller.Virtual import VirtualChamber, VirtualChamberGUI

chamber = VirtualChamber()
chamber.initialize_m0s()

gui = VirtualChamberGUI(chamber)
gui.run()
```

### Method 4: Programmatic Testing
```python
from Controller.Virtual import VirtualChamber
import time

chamber = VirtualChamber()
chamber.initialize_m0s()

# Run your test sequence
chamber.left_m0.send_command("DISPLAY:stim.bmp")
time.sleep(1)
chamber.left_m0.simulate_touch(160, 240)
chamber.reward.dispense()
time.sleep(0.5)
chamber.reward.stop()

# Verify state
state = chamber.get_state()
assert state['reward']['total_dispensed'] == 1
```

## 🎨 Virtual Hardware Components

### VirtualM0Device
- **Purpose**: Simulates Arduino M0 touchscreen controllers
- **Methods**: `initialize()`, `send_command()`, `is_touched()`, `simulate_touch()`
- **State**: Tracks current image, touch status, coordinates

### VirtualBeamBreak
- **Purpose**: Simulates IR beam sensor in food hopper
- **Methods**: `activate()`, `deactivate()`, `simulate_break()`, `simulate_restore()`
- **State**: Tracks beam status with memory (default 200ms)

### VirtualLED
- **Purpose**: Simulates reward and punishment LEDs
- **Methods**: `on()`, `off()`, `set_brightness()`, `set_color()` (if RGB)
- **State**: Tracks on/off status, brightness, color

### VirtualBuzzer
- **Purpose**: Simulates audio buzzer
- **Methods**: `activate()`, `deactivate()`, `set_frequency()`, `set_volume()`
- **State**: Tracks active status, frequency, volume

### VirtualReward
- **Purpose**: Simulates food pump
- **Methods**: `dispense()`, `stop()`, `reset_counter()`
- **State**: Tracks dispensing status, total rewards delivered

### VirtualChamber
- **Purpose**: Complete virtual chamber matching Chamber class
- **Contains**: 3x M0s, reward pump, beam break, 2x LEDs, buzzer
- **Methods**: Same as Chamber + `get_state()`, `log_state()`

## 💡 Use Cases

1. **Development** - Build new training protocols without hardware
2. **Testing** - Automated unit tests for trainer state machines
3. **Training** - Train new lab members without tying up physical chambers
4. **Debugging** - Inspect chamber state at any point during execution
5. **CI/CD** - Include chamber tests in your continuous integration

## 🔄 Switching Between Physical and Virtual

### Option 1: Config File
```yaml
# For virtual testing
virtual_mode: true

# For physical chamber
virtual_mode: false
```

### Option 2: Environment Variable
```python
import os
virtual = os.getenv('VIRTUAL_MODE', 'false').lower() == 'true'
session = Session(session_config={'virtual_mode': virtual})
```

### Option 3: Command Line Argument
```python
import sys
virtual = '--virtual' in sys.argv
session = Session(session_config={'virtual_mode': virtual})
```

## 📊 Testing Your Trainers

### Example: Testing InitialTouch
```python
from Controller.Session import Session
from Controller.Virtual import VirtualChamberGUI

# Create virtual session
session = Session(session_config={
    'virtual_mode': True,
    'trainer_name': 'InitialTouch'
})

# Launch GUI for interaction
gui = VirtualChamberGUI(session.chamber)
gui_thread = gui.run_async()

# Start training
session.start_session()

# Interact via GUI to simulate animal behavior
```

## 🐛 Troubleshooting

**Q: GUI doesn't appear**
- Make sure tkinter is installed: `python -m tkinter`
- Try `gui.run()` instead of `gui.run_async()` if running in main thread

**Q: Import errors**
- Ensure you're running from correct directory or add to path:
  ```python
  import sys, os
  sys.path.insert(0, 'Controller')
  ```

**Q: Can I test without GUI?**
- Yes! Just use the chamber programmatically without creating VirtualChamberGUI

**Q: Does this work on Windows/Mac/Linux?**
- Yes! No hardware dependencies, pure Python

## 📝 Next Steps

1. **Try the demos**: Run `python scripts/demo_virtual_chamber.py`
2. **Test an existing trainer**: Enable `virtual_mode` and run your current training code
3. **Develop new protocols**: Create and test new trainers virtually
4. **Write automated tests**: Build a test suite for your trainer logic
5. **Train users**: Use virtual chamber for onboarding new lab members

## 🎉 Benefits

- ✅ **Zero hardware needed** - Test anywhere, anytime
- ✅ **Faster iteration** - No chamber setup/teardown
- ✅ **No code changes** - Same API as physical hardware  
- ✅ **Visual feedback** - See exactly what's happening
- ✅ **State inspection** - Debug with complete state visibility
- ✅ **Automated testing** - Run tests in CI/CD pipelines
- ✅ **Risk-free** - Test destructive changes safely

## 📚 Documentation Links

- [Virtual/README.md](Controller/Virtual/README.md) - Detailed documentation
- [VIRTUAL_CHAMBER_GUIDE.md](VIRTUAL_CHAMBER_GUIDE.md) - Quick start guide
- [demo_virtual_chamber.py](scripts/demo_virtual_chamber.py) - Interactive examples
- [test_virtual_chamber.py](scripts/test_virtual_chamber.py) - Test suite

---

**Ready to virtualize your testing!** 🚀

For questions or issues, check the documentation or examine the example scripts.
