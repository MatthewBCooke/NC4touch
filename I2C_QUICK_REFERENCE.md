# I2C Quick Reference Card

## Enable I2C on Raspberry Pi

```bash
sudo raspi-config
# Interface Options > I2C > Enable
sudo reboot
```

## Check I2C Bus

```bash
# List I2C devices
ls /dev/i2c-*

# Scan for devices (requires i2c-tools)
sudo apt-get install i2c-tools
sudo i2cdetect -y 1

# Expected output:
#      0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
# 00:          -- -- -- -- -- -- -- -- -- -- -- -- --
# 10: -- 01 02 03 -- -- -- -- -- -- -- -- -- -- -- --
```

## Install Python Dependencies

```bash
pip install smbus2
```

## M0 I2C Address Configuration

| M0 | Pin 10 | Pin 11 | Pin 12 | Address |
|----|--------|--------|--------|---------|
| Left (M0_0) | GND | Float | Float | 0x01 |
| Middle (M0_1) | Float | GND | Float | 0x02 |
| Right (M0_2) | GND | GND | Float | 0x03 |

## Flash I2C Firmware

```bash
cd /home/administrator/.openclaw/workspace/NC4touch

# Compile
~/bin/arduino-cli compile -b DFRobot:samd:mzero_bl M0Touch_I2C/M0Touch_I2C.ino

# Upload (replace /dev/ttyACM0 with correct port)
~/bin/arduino-cli upload --port /dev/ttyACM0 --fqbn DFRobot:samd:mzero_bl M0Touch_I2C/M0Touch_I2C.ino
```

## Test I2C Communication

```python
# Test discovery
python3 -c "
from Controller.M0DeviceI2C import discover_i2c_devices
devices = discover_i2c_devices()
print(f'Found {len(devices)} devices:', devices)
"

# Expected: [(0x01, 'M0_0'), (0x02, 'M0_1'), (0x03, 'M0_2')]
```

## Use I2C in Chamber

```python
from Controller.Chamber import Chamber

# Create chamber with I2C
chamber = Chamber(chamber_config={"use_i2c": True})

# Initialize M0s
chamber.m0_initialize()

# Use normally
chamber.m0_send_command("BLACK")
chamber.m0_send_command("IMG:A01")
chamber.m0_send_command("SHOW")
```

## Run Tests

```bash
cd tests

# Run all tests
python3 test_i2c_integration.py

# Expected: 🎉 All tests passed!
```

## Common Issues

### No devices found

```bash
# Check I2C enabled
sudo i2cdetect -y 1

# Verify wiring:
# - Pi Pin 3 (SDA) → M0 SDA
# - Pi Pin 5 (SCL) → M0 SCL
# - GND → GND
```

### Wrong address

```bash
# Check M0 serial output
screen /dev/ttyACM0 115200
# Should print: "M0 board #X ready on I2C address 0xYY"

# Verify GPIO pins 10, 11, 12 grounding
```

### Communication timeout

```python
# Increase timeout
from Controller.M0DeviceI2C import M0DeviceI2C
M0DeviceI2C.DEFAULT_TIMEOUT = 5.0

# Slow down I2C bus (add to /boot/config.txt)
dtparam=i2c_arm_baudrate=100000
```

### Checksum errors

```bash
# Add pull-up resistors
# 2.2kΩ from SDA to 3.3V
# 2.2kΩ from SCL to 3.3V

# Shorten wires, twist SDA+SCL together
```

## Debug

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Monitor serial output
screen /dev/ttyACM0 115200
```

## Revert to Serial Mode

```python
# Don't pass use_i2c flag (default is False)
chamber = Chamber()

# Or explicitly disable
chamber = Chamber(chamber_config={"use_i2c": False})
```

---

**Full Documentation:** `docs/I2C_IMPLEMENTATION.md`
