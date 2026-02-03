# NC4touch Architecture Documentation

## Overview

NC4touch is a touchscreen-based rodent training system built on Raspberry Pi. The system coordinates multiple touchscreen displays (M0 devices), peripheral hardware (LEDs, pumps, sensors), and training protocols to run behavioral experiments.

## Class Hierarchy

```
Session
├── Chamber (or VirtualChamber in virtual mode)
│   ├── HardwareConfig (new centralized configuration)
│   │   ├── GPIOPinConfig
│   │   ├── PWMConfig
│   │   ├── M0SerialConfig / M0I2CConfig
│   │   ├── CameraConfig
│   │   ├── DirectoryConfig
│   │   └── BeamBreakConfig
│   ├── M0Device (left_m0) or M0DeviceI2C
│   ├── M0Device (middle_m0) or M0DeviceI2C
│   ├── M0Device (right_m0) or M0DeviceI2C
│   ├── LED (reward_led)
│   ├── LED (punishment_led)
│   ├── LED (house_led)
│   ├── BeamBreak (beambreak)
│   ├── Buzzer (buzzer)
│   ├── Reward (reward)
│   └── Camera (camera)
└── Trainer (abstract base class)
    ├── DoNothingTrainer
    ├── Habituation
    ├── InitialTouch
    ├── MustTouch
    ├── Punish_Incorrect
    ├── Simple_Discrimination
    ├── Complex_Discrimination
    ├── PRL
    └── SoundTest

Config (legacy, used by Session and Trainer)
```

## File Purposes

### Core System Files
- **`Session.py`** - Top-level session manager; initializes chamber and trainer, manages video recording and logging
- **`Chamber.py`** - Hardware abstraction layer; manages all physical components and M0 device discovery. Uses HardwareConfig for centralized configuration.
- **`Trainer.py`** - Abstract base class for all training protocols; defines interface for trial management and data recording
- **`Config.py`** - Legacy configuration management class; handles YAML config files (being phased out in favor of HardwareConfig)

### Configuration Package (`config/`)
- **`hardware_config.py`** - Centralized hardware configuration using Python dataclasses
  - `HardwareConfig` - Root configuration class
  - `GPIOPinConfig` - GPIO pin assignments
  - `PWMConfig` - PWM settings for LEDs and pumps
  - `M0SerialConfig` - Serial communication parameters
  - `M0I2CConfig` - I2C communication parameters
  - `CameraConfig` - Camera and video settings
  - `DirectoryConfig` - File system paths
  - `BeamBreakConfig` - Sensor parameters
- See [CONFIG.md](CONFIG.md) for detailed documentation

### Hardware Component Files
- **`M0Device.py`** - Interface to individual M0 touchscreen boards; handles serial communication and state management. Uses M0SerialConfig for all serial parameters.
- **`M0DeviceI2C.py`** - I2C-based interface to M0 boards; alternative to serial communication. Uses M0I2CConfig for all I2C parameters.
- **`m0_devices.py`** - Utilities for M0 device management
- **`LED.py`** - PWM-based LED control (supports single-color and RGB)
- **`Reward.py`** - Reward pump control via PWM
- **`BeamBreak.py`** - IR beam break sensor monitoring with memory
- **`Buzzer.py`** - Buzzer/speaker control
- **`Camera.py`** - Video streaming (ustreamer) and recording (ffmpeg) management

### Trainer Implementations
- **`DoNothingTrainer.py`** - Null trainer for testing; does nothing
- **`Habituation.py`** - Initial habituation phase; free rewards to introduce system
- **`InitialTouch.py`** - First touch training; rewards any correct screen touch
- **`MustTouch.py`** - Requires correct screen touch before reward; adds ITI punishment
- **`Punish_Incorrect.py`** - Adds punishment for incorrect touches
- **`Simple_Discrimination.py`** - Two-choice discrimination task
- **`Complex_Discrimination.py`** - Multi-stimulus discrimination task
- **`PRL.py`** - Probabilistic reversal learning task
- **`SoundTest.py`** - Auditory stimulus testing

### User Interface Files
- **`Main.py`** - Main entry point; integrates GUI, TUI, or WebUI
- **`GUI.py`** - PyQt5-based graphical user interface
- **`TUI.py`** - Terminal user interface
- **`WebUI.py`** - Web-based interface (Flask)
- **`file_picker.py`** - File picker dialog utility
- **`video_recorder.py`** - Video recording utilities

### Utility Files
- **`helpers.py`** - Helper functions (get IP address, wait for dmesg)
- **`requirements.txt`** - Python dependencies

### Virtual Mode (Testing)
- **`Virtual/VirtualChamber.py`** - Software simulation of chamber hardware
- **`Virtual/VirtualM0Device.py`** - Software simulation of M0 touchscreens
- **`Virtual/VirtualChamberGUI.py`** - GUI for virtual chamber interaction
- **`Virtual/VirtualLED.py`** - Virtual LED simulation
- **`Virtual/VirtualBuzzer.py`** - Virtual buzzer simulation
- **`Virtual/VirtualReward.py`** - Virtual reward simulation
- **`Virtual/VirtualBeamBreak.py`** - Virtual beam break simulation

## Core Flow: How a Training Session Works

### 1. Session Initialization
```
Session.__init__()
├── Load configuration (YAML or dict)
├── Initialize logging (session_log.log)
├── Create Chamber (or VirtualChamber if virtual_mode=True)
│   ├── Initialize pigpio connection
│   ├── Create 3x M0Device instances (left, middle, right)
│   ├── Discover M0 boards via arduino-cli
│   ├── Initialize peripherals (LEDs, reward pump, beam break, buzzer, camera)
│   └── Start camera streaming
└── Load Trainer class dynamically (importlib)
    ├── Instantiate trainer with Chamber reference
    └── Initialize trainer config
```

### 2. Starting Training
```
Session.start_training()
├── Configure trainer parameters (rodent name, data dir, etc.)
├── Trainer.start_training()
│   ├── Reset chamber to default state
│   ├── Load trial sequence from CSV file
│   ├── Open JSON data file for logging
│   └── Set state to START_TRAINING
└── Start run_training() timer loop (default 0.1s interval)
```

### 3. Training Loop (State Machine)
```
Session.run_training() [called every 0.1s]
└── Trainer.run_training()
    ├── Check current state (Enum-based state machine)
    ├── Execute state-specific logic:
    │   ├── START_TRIAL: Load images to M0s, show stimuli
    │   ├── WAIT_FOR_TOUCH: Monitor M0 touch events
    │   ├── CORRECT: Clear screen, trigger reward
    │   ├── DELIVER_REWARD: Dispense reward, monitor beam break
    │   ├── ITI: Wait for inter-trial interval
    │   └── END_TRIAL: Log data, increment trial counter
    ├── Write events to JSON log (timestamps, trial data)
    └── Transition to next state

Example (InitialTouch):
IDLE → START_TRAINING → LARGE_REWARD_START → DELIVERING_LARGE_REWARD 
→ ITI_START → ITI → START_TRIAL → WAIT_FOR_TOUCH → CORRECT/ERROR 
→ LARGE_REWARD_START/SMALL_REWARD_START → ... → END_TRAINING → IDLE
```

### 4. M0 Device Interaction
```
Trainer sends commands to M0 devices:
├── Load image: chamber.left_m0.send_command("IMG:A01")
├── Show image: chamber.left_m0.send_command("SHOW")
├── Clear screen: chamber.left_m0.send_command("BLACK")
└── Check touch: chamber.left_m0.is_touched()

M0Device state:
├── Serial connection runs in background thread (read_loop)
├── Incoming messages queued: (device_id, message_text)
├── Touch events set is_touched flag
└── Commands sent via write_lock for thread safety
```

### 5. Peripheral Control
```
During training states:
├── Reward delivery:
│   ├── chamber.reward.dispense() → PWM pin HIGH
│   ├── chamber.reward_led.activate() → PWM brightness
│   └── chamber.beambreak monitors collection
├── ITI period:
│   ├── chamber.beambreak.activate() → starts monitoring
│   ├── Beam break during ITI → add time penalty
│   └── chamber.reward_led.deactivate()
└── Punishment (if applicable):
    ├── chamber.punishment_led.activate()
    └── chamber.buzzer.activate()
```

### 6. Data Logging
```
Trainer.write_event(event_name, trial_data)
├── Create event dict:
│   ├── timestamp: "20250203_123045_123456"
│   ├── event: "LeftScreenTouched"
│   └── data: trial_number or other info
└── Write JSON line to data file

Events logged:
├── StartTraining, StartTrial, EndTrial, EndTraining
├── LeftScreenTouched, RightScreenTouched
├── CorrectTouch, IncorrectTouch
├── DeliverRewardStart, RewardDispenseComplete
├── BeamBreakDuringReward, BeamBreakAfterReward
└── ITIStart, ITIComplete, TouchTimeout
```

### 7. Stopping Training
```
Session.stop_training()
├── Cancel timer thread
├── Trainer.stop_training()
│   ├── Reset chamber state (LEDs off, reward off)
│   ├── Close JSON data file
│   └── Set state to IDLE
└── Move session log to data directory
```

## Data Flow: Touch Events (M0 → Python → Logged)

### 1. M0 Firmware Detection
```
[M0 Touchscreen Hardware]
├── Capacitive touch controller detects finger
├── M0 Arduino firmware reads touch coordinates
├── Firmware formats message: "TOUCH:x,y"
└── Sends via USB serial (115200 baud)
```

### 2. Serial Communication
```
[M0Device.read_loop() - Background Thread]
├── ser.readline() blocks waiting for data
├── Receive: "TOUCH:x,y\n"
├── Decode UTF-8 and strip whitespace
├── Log: "[M0_0] TOUCH:x,y"
├── Queue message: message_queue.put(("M0_0", "TOUCH:x,y"))
└── Set flag: self.is_touched = True
```

### 3. Trainer Polling
```
[Trainer.run_training() - Main Loop]
├── State: WAIT_FOR_TOUCH
├── Poll: chamber.left_m0.is_touched()
├── If True:
│   ├── Reset flag: is_touched = False
│   ├── Log event: logger.info("Left screen touched")
│   └── Transition state based on correctness
└── Repeat every 0.1 seconds
```

### 4. Event Logging
```
[Trainer.write_event()]
├── Event: "LeftScreenTouched"
├── Data: current_trial number
├── Create JSON object:
│   {
│       "timestamp": "20250203_123045_123456",
│       "event": "LeftScreenTouched",
│       "data": 5
│   }
├── Write to data file: json.dump(event_data, self.data_file)
└── File: /mnt/shared/data/20250203_123045_Chamber0_InitialTouch_Rat01_data.json
```

### 5. Complete Touch Event Timeline
```
Time    Component           Action
------  ------------------  -------------------------------------------------
0.000s  M0 Hardware         Touch detected at (120, 80)
0.001s  M0 Firmware         Format message "TOUCH:120,80\n"
0.002s  M0 Serial           Transmit over USB serial
0.003s  M0Device.read_loop  Receive message, queue, set is_touched=True
0.100s  Trainer.run_training Poll is_touched(), detect touch
0.101s  Trainer             Log "LeftScreenTouched" to console
0.102s  Trainer             Write JSON event to data file
0.103s  Trainer             Transition to CORRECT state
0.104s  Trainer             Send "BLACK" command to clear screen
0.105s  M0Device            Transmit "BLACK\n" over serial
0.106s  M0 Firmware         Receive command, clear display
```

### 6. Message Queue Structure
```
M0Device.message_queue (thread-safe queue.Queue)
├── Items: tuples of (device_id, message_text)
├── Example: ("M0_0", "TOUCH:120,80")
├── Consumed by: Trainer logic (implicitly via is_touched flag)
└── Flushed via: flush_message_queue() to clear old messages
```

### 7. Data File Structure
```json
# Header
{
    "header": {
        "timestamp": "20250203_123045_000000",
        "rodent": "Rat01",
        "chamber": "Chamber0",
        "trainer": "InitialTouch"
    }
}

# Events (one JSON object per line)
{"timestamp": "20250203_123045_123456", "event": "StartTraining", "data": 1}
{"timestamp": "20250203_123046_234567", "event": "StartTrial", "data": 1}
{"timestamp": "20250203_123050_345678", "event": "LeftScreenTouched", "data": 1}
{"timestamp": "20250203_123050_456789", "event": "CorrectTouch", "data": 1}
{"timestamp": "20250203_123050_567890", "event": "DeliverRewardStart", "data": 1}
...
```

## Communication Protocols

### Serial to M0 Devices
- **Protocol:** USB CDC (Virtual COM Port)
- **Baud Rate:** 115200
- **Format:** ASCII text, newline-terminated
- **Direction:** Bidirectional
- **Commands (Python → M0):**
  - `WHOAREYOU?` - Request device ID
  - `IMG:filename` - Load image from SD card
  - `SHOW` - Display loaded image
  - `BLACK` - Clear screen to black
- **Responses (M0 → Python):**
  - `ID:M0_0` - Device identification
  - `TOUCH:x,y` - Touch event with coordinates
  - `IMG:OK` - Image loaded successfully
  - `IMG:ERROR` - Image load failed

### GPIO via pigpio
- **Library:** pigpio daemon (socket-based)
- **Components:** LEDs, reward pump, beam break, buzzer
- **Methods:**
  - `pi.set_mode(pin, pigpio.OUTPUT/INPUT)`
  - `pi.set_PWM_dutycycle(pin, value)` - PWM control
  - `pi.read(pin)` - Digital input
  - `pi.set_pull_up_down(pin, pigpio.PUD_UP)` - Enable pull-up

### Camera Streaming
- **Streaming:** ustreamer (low-latency MJPEG over HTTP)
- **Recording:** ustreamer-dump → ffmpeg (H.264 MP4)
- **Port:** 8080 (configurable)
- **Protocol:** HTTP MJPEG stream

## Configuration System

NC4touch uses a dual configuration system for backward compatibility:

### New Configuration (Recommended)
- **Package:** `config/hardware_config.py`
- **Format:** Python dataclasses with type safety and validation
- **Usage:** 
  ```python
  from config import get_default_config
  hw_config = get_default_config()
  chamber = Chamber(hw_config=hw_config)
  ```
- **Benefits:**
  - Type checking and IDE autocomplete
  - Centralized hardware parameters
  - YAML import/export support
  - Validation (e.g., duplicate pin detection)

See [CONFIG.md](CONFIG.md) for complete documentation.

### Legacy Configuration
- **Class:** `Config.py`
- **Format:** Dictionary-based with YAML persistence
- **Usage:** 
  ```python
  config = Config(config={'param': value}, config_file='~/config.yaml')
  ```
- **Status:** Maintained for backward compatibility; gradually being replaced

### Configuration Mapping

The new HardwareConfig automatically maps to legacy Config for components that haven't been updated:

```python
# Legacy (old)
self.config.ensure_param("reward_LED_pin", 21)
pin = self.config["reward_LED_pin"]

# New (current)
pin = self.hw_config.gpio_pins.reward_led_pin
```

All components use the configuration pattern:

All components accept configuration via constructor parameters:

```python
# Chamber with new config
from config import get_default_config
hw_config = get_default_config()
chamber = Chamber(hw_config=hw_config)

# Chamber with legacy config (backward compatible)
chamber = Chamber(
    chamber_config={'use_i2c': True},
    chamber_config_file='~/chamber_config.yaml'
)

# M0Device with config
from config import M0SerialConfig
serial_config = M0SerialConfig(baudrate=115200, max_retries=5)
m0 = M0Device(pi=pi, id="M0_0", reset_pin=25, config=serial_config)

# M0DeviceI2C with config
from config import M0I2CConfig
i2c_config = M0I2CConfig(bus_number=1, timeout=3.0)
m0 = M0DeviceI2C(pi=pi, id="M0_0", address=0x00, reset_pin=25, config=i2c_config)
```

## Error Handling and Recovery

### M0 Device Recovery
- **Serial port reopening:** `_attempt_reopen()` on communication errors
- **Hardware reset:** GPIO toggle via reset_pin
- **Device discovery:** arduino-cli JSON parsing with fallback

### Logging
- **Session log:** Timestamped events to file and console
- **Log levels:** DEBUG, INFO, WARNING, ERROR
- **Log rotation:** Logs moved to data directory on session end

### Virtual Mode
- **Purpose:** Test training protocols without hardware
- **Activation:** `virtual_mode=True` in session config
- **Simulates:** M0 touches, beam breaks, LEDs (no actual GPIO)
