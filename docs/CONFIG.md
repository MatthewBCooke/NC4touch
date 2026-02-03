# NC4touch Configuration System

## Overview

NC4touch uses a centralized configuration system based on Python dataclasses. This provides type-safe configuration with validation, sensible defaults, and YAML serialization support.

## Architecture

The configuration is organized into component-specific dataclasses:

```
HardwareConfig (root)
├── GPIOPinConfig        # All GPIO pin assignments
├── PWMConfig            # PWM settings for LEDs and pumps
├── M0SerialConfig       # Serial communication parameters
├── M0I2CConfig          # I2C communication parameters
├── CameraConfig         # Camera and video settings
├── DirectoryConfig      # File system paths
└── BeamBreakConfig      # Sensor parameters
```

## Configuration Files

### Location
- Default: `~/chamber_config.yaml`
- Can be overridden via constructor parameter

### Format
YAML format with nested structure matching the dataclass hierarchy:

```yaml
chamber_name: Chamber0
use_i2c: false

gpio_pins:
  reward_led_pin: 21
  punishment_led_pin: 17
  house_led_pin: 20
  reward_pump_pin: 27
  beambreak_pin: 4
  buzzer_pin: 16
  m0_reset_pins: [25, 5, 6]

pwm:
  frequency: 5000
  range: 255
  reward_led_brightness: 140
  punishment_led_brightness: 255
  house_led_brightness: 100
  pump_duty_cycle: 255

m0_serial:
  baudrate: 115200
  timeout: 5.0
  max_retries: 3
  retry_backoff_base: 0.1
  read_loop_interval: 0.1
  reset_pulse_duration: 0.01
  reset_recovery_time: 0.5
  discovery_wait_time: 3.0
  flush_on_send: true
  vendor_id: "0x2341"
  product_id: "0x0244"

m0_i2c:
  bus_number: 1
  addresses: [0x00, 0x01, 0x02]
  timeout: 2.0
  poll_interval: 0.1
  max_retries: 3
  retry_backoff_base: 0.1
  reset_pulse_duration: 0.01
  reset_recovery_time: 0.5

camera:
  device_path: /dev/video0
  stream_port: 8080
  stream_format: MJPEG
  video_codec: libx264
  kill_existing_on_start: true

directories:
  data_dir: /mnt/shared/data
  image_dir: ../data/images
  m0_sketch_dir: ../M0Touch
  m0_sketch_i2c_dir: ../M0Touch_I2C

beambreak:
  memory_duration: 0.2
  read_interval: 0.05
```

## Python API

### Using the New Config System (Recommended)

```python
from config import HardwareConfig, get_default_config, GPIOPinConfig

# Option 1: Use defaults
config = get_default_config()

# Option 2: Override specific values
config = HardwareConfig(
    chamber_name="Chamber1",
    use_i2c=True,
    gpio_pins=GPIOPinConfig(reward_led_pin=22)
)

# Option 3: Load from YAML
from config import load_config_from_yaml
config = load_config_from_yaml("~/my_chamber_config.yaml")

# Use with Chamber
from Chamber import Chamber
chamber = Chamber(hw_config=config)
```

### Backward Compatibility with Legacy Config

The new system maintains full backward compatibility with the old `Config` class:

```python
# Old way (still works)
chamber = Chamber(
    chamber_config={'reward_LED_pin': 22, 'use_i2c': True},
    chamber_config_file='~/chamber_config.yaml'
)

# New config is created automatically from legacy config
# and used internally
```

### Saving Configuration

```python
from config import save_config_to_yaml

config = get_default_config()
config.gpio_pins.reward_led_pin = 22
config.use_i2c = True

save_config_to_yaml(config, "~/my_chamber_config.yaml")
```

## Configuration Components

### GPIOPinConfig

GPIO pin assignments for all peripherals.

**Attributes:**
- `reward_led_pin` (int, default: 21)
- `punishment_led_pin` (int, default: 17)
- `house_led_pin` (int, default: 20)
- `reward_pump_pin` (int, default: 27)
- `beambreak_pin` (int, default: 4)
- `buzzer_pin` (int, default: 16)
- `m0_reset_pins` (List[int], default: [25, 5, 6])

**Validation:**
- Checks for duplicate pin assignments

### PWMConfig

PWM settings for LEDs and reward pump.

**Attributes:**
- `frequency` (int, default: 5000) - PWM frequency in Hz
- `range` (int, default: 255) - PWM range (8-bit resolution)
- `reward_led_brightness` (int, default: 140) - 0-255
- `punishment_led_brightness` (int, default: 255) - 0-255
- `house_led_brightness` (int, default: 100) - 0-255
- `pump_duty_cycle` (int, default: 255) - 0-255

### M0SerialConfig

Serial communication parameters for M0 devices.

**Attributes:**
- `baudrate` (int, default: 115200)
- `timeout` (float, default: 5.0) - Serial read timeout in seconds
- `vendor_id` (str, default: "0x2341") - USB VID for discovery
- `product_id` (str, default: "0x0244") - USB PID for discovery
- `max_retries` (int, default: 3) - Connection retry attempts
- `retry_backoff_base` (float, default: 0.1) - Exponential backoff base in seconds
- `read_loop_interval` (float, default: 0.1) - Background read polling interval
- `reset_pulse_duration` (float, default: 0.01) - Hardware reset pulse duration
- `reset_recovery_time` (float, default: 0.5) - Time to wait after reset
- `discovery_wait_time` (float, default: 3.0) - Time to wait for device enumeration
- `flush_on_send` (bool, default: True) - Flush buffers before sending commands

### M0I2CConfig

I2C communication parameters for M0 devices.

**Attributes:**
- `bus_number` (int, default: 1) - I2C bus number (Raspberry Pi bus 1)
- `addresses` (List[int], default: [0x00, 0x01, 0x02]) - I2C device addresses
- `timeout` (float, default: 2.0) - I2C transaction timeout
- `poll_interval` (float, default: 0.1) - Touch polling interval
- `max_retries` (int, default: 3) - Communication retry attempts
- `retry_backoff_base` (float, default: 0.1) - Exponential backoff base
- `reset_pulse_duration` (float, default: 0.01) - Hardware reset pulse
- `reset_recovery_time` (float, default: 0.5) - Post-reset recovery time

**Validation:**
- Ensures I2C addresses are in range 0x00-0x07

### CameraConfig

Camera and video recording configuration.

**Attributes:**
- `device_path` (str, default: "/dev/video0") - V4L2 device path
- `stream_port` (int, default: 8080) - HTTP streaming port
- `stream_format` (str, default: "MJPEG") - Video stream format
- `video_codec` (str, default: "libx264") - Recording codec
- `kill_existing_on_start` (bool, default: True) - Kill existing ustreamer processes

### DirectoryConfig

File system paths for data storage.

**Attributes:**
- `data_dir` (str, default: "/mnt/shared/data") - Base data directory
- `video_dir` (Optional[str], default: None) - Video storage (falls back to data_dir)
- `image_dir` (str, default: "../data/images") - Image folder for M0s
- `log_dir` (Optional[str], default: None) - Log storage (falls back to data_dir)
- `m0_sketch_dir` (str, default: "../M0Touch") - Serial M0 sketch path
- `m0_sketch_i2c_dir` (str, default: "../M0Touch_I2C") - I2C M0 sketch path

**Helper Methods:**
- `get_video_dir()` - Returns video directory with fallback
- `get_log_dir()` - Returns log directory with fallback
- `get_m0_sketch_path(use_i2c=False)` - Returns full path to .ino file

### BeamBreakConfig

Beam break sensor configuration.

**Attributes:**
- `memory_duration` (float, default: 0.2) - Memory duration to prevent bouncing (seconds)
- `read_interval` (float, default: 0.05) - Polling interval (seconds)

## Migration Guide

### From Hardcoded Values

**Before:**
```python
# In Chamber.py
self.reward_led = LED(pi=self.pi, pin=21, brightness=140)
```

**After:**
```python
# In Chamber.py
pins = self.hw_config.gpio_pins
pwm = self.hw_config.pwm
self.reward_led = LED(
    pi=self.pi,
    pin=pins.reward_led_pin,
    brightness=pwm.reward_led_brightness
)
```

### From Legacy Config Dict

**Before:**
```python
self.config.ensure_param("reward_LED_pin", 21)
pin = self.config["reward_LED_pin"]
```

**After:**
```python
pin = self.hw_config.gpio_pins.reward_led_pin
```

### From M0Device Hardcoded Constants

**Before:**
```python
# In M0Device.py
self.baudrate = 115200
self.read_loop_interval = 0.1
```

**After:**
```python
# In M0Device.py
self.baudrate = config.baudrate
self.read_loop_interval = config.read_loop_interval
```

## Benefits

1. **Type Safety**: Dataclasses provide type checking and IDE autocomplete
2. **Validation**: Pin conflicts and invalid addresses detected at initialization
3. **Documentation**: Self-documenting with docstrings and type hints
4. **Centralized**: All hardware parameters in one place
5. **Backward Compatible**: Works with existing code using legacy Config
6. **Testable**: Easy to create test configs with specific values
7. **Version Control**: YAML config files are human-readable diffs

## Testing

```python
# Test with custom config
from config import HardwareConfig, GPIOPinConfig

test_config = HardwareConfig(
    gpio_pins=GPIOPinConfig(
        reward_led_pin=22,  # Use different pin for testing
        m0_reset_pins=[10, 11, 12]
    )
)

chamber = Chamber(hw_config=test_config)
```

## Troubleshooting

### Duplicate Pin Assignment Error
```
ValueError: Duplicate GPIO pin assignments detected
```
**Solution:** Check your config YAML for duplicate pin numbers.

### Invalid I2C Address
```
ValueError: I2C address 0x08 out of valid range 0x00-0x07
```
**Solution:** I2C addresses must be 0x00-0x07 (set by M0 GPIO pins).

### Config Not Found
```
FileNotFoundError: Config file not found: ~/chamber_config.yaml
```
**Solution:** Create config file or use `get_default_config()` to generate one.

## Future Enhancements

Planned improvements:
- JSON schema export for config validation
- Config migration tool for version updates
- Web UI for config editing
- Per-chamber config profiles
- Runtime config reloading without restart
