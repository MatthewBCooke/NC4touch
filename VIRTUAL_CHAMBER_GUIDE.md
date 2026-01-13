# Virtual Chamber Testing Guide

## 🎯 Overview

The Virtual Chamber system lets you test and develop touchscreen chamber training protocols **without physical hardware access**. Perfect for:

- Developing new training protocols
- Debugging state machine logic
- Testing trial sequences
- Training new users
- Continuous integration testing

## 🚀 Quick Start (3 Steps)

### 1. Enable Virtual Mode

Add to your session config:

```yaml
# session_config.yaml
virtual_mode: true
trainer_name: "InitialTouch"
rodent_name: "VirtualRat"
```

### 2. Run Your Session

```python
from Controller.Session import Session

session = Session(session_config_file='session_config.yaml')
session.start_session()
```

### 3. Interact with GUI

The virtual chamber GUI will allow you to:
- Click touchscreens to simulate touches
- Trigger beam breaks
- Monitor all hardware states in real-time

## 📖 Usage Examples

### Example 1: Test with GUI

```python
from Controller.Virtual import VirtualChamber, VirtualChamberGUI

# Create chamber
chamber = VirtualChamber()
chamber.initialize_m0s()

# Launch GUI
gui = VirtualChamberGUI(chamber)
gui.run()
```

### Example 2: Programmatic Testing

```python
from Controller.Virtual import VirtualChamber
import time

chamber = VirtualChamber()
chamber.initialize_m0s()

# Display stimuli
chamber.left_m0.send_command("DISPLAY:plus.bmp")
chamber.right_m0.send_command("DISPLAY:minus.bmp")

# Simulate correct response
time.sleep(1)
chamber.left_m0.simulate_touch(160, 240)

# Deliver reward
chamber.reward.dispense()
time.sleep(0.5)
chamber.reward.stop()

# Simulate consumption
chamber.beambreak.simulate_break(duration=2.0)
```

### Example 3: With Session

```python
from Controller.Session import Session

# Just set virtual_mode=True!
session = Session(session_config={
    "virtual_mode": True,
    "trainer_name": "MustTouch"
})

# Everything else works exactly the same
session.start_session()
```

## 🎮 Demo Scripts

Try the included demos:

```bash
# Interactive demo with menu
python scripts/demo_virtual_chamber.py

# Comprehensive test suite
python scripts/test_virtual_chamber.py
```

## 📚 Documentation

- **[Virtual/README.md](Controller/Virtual/README.md)** - Complete documentation
- **[demo_virtual_chamber.py](scripts/demo_virtual_chamber.py)** - Interactive demos
- **[test_virtual_chamber.py](scripts/test_virtual_chamber.py)** - Test suite
- **[virtual_chamber_config.yaml](scripts/virtual_chamber_config.yaml)** - Example config

## 🔧 Virtual Hardware Components

All virtual components maintain **identical APIs** to physical hardware:

- `VirtualM0Device` - Touchscreen controllers (3x)
- `VirtualBeamBreak` - IR beam sensor
- `VirtualLED` - Reward & punishment LEDs
- `VirtualBuzzer` - Audio feedback
- `VirtualReward` - Food pump
- `VirtualChamber` - Complete chamber wrapper

## 💡 Tips

1. **No code changes needed** - Virtual components implement the same interface as physical hardware
2. **Use GUI for development** - Visual feedback makes debugging easier
3. **Use programmatic for testing** - Automated tests don't need the GUI
4. **Toggle easily** - Just change `virtual_mode` in config

## 🐛 Troubleshooting

**Import errors?**
```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Controller'))
```

**GUI not appearing?**
- Make sure you're using `gui.run()` not `gui.run_async()` if in main thread
- Check that tkinter is installed: `python -m tkinter`

**Want to test without GUI?**
- Just don't create the GUI object - use chamber programmatically!

## 📦 Requirements

- Python 3.7+
- tkinter (for GUI, usually included with Python)
- PyYAML (for config files)

No hardware dependencies! Works on any platform (Windows, Mac, Linux).

---

**Ready to test?** Run `python scripts/demo_virtual_chamber.py` to get started! 🚀
