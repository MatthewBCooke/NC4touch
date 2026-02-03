# I2C Quick Start Guide

**For NC4touch M0 Touchscreen Controllers**

---

## Hardware Setup (5 Minutes)

### 1. Wire Connections

```
Raspberry Pi → All M0 Boards
────────────────────────────
GPIO 2 (SDA) → SDA on each M0
GPIO 3 (SCL) → SCL on each M0
GND          → GND on each M0

Reset Pins (keep existing):
GPIO 25 → M0 Left RST
GPIO 5  → M0 Middle RST
GPIO 6  → M0 Right RST
```

### 2. Set I2C Addresses

**On each M0 board, connect these pins:**

| M0 Device | Pin 10 | Pin 11 | Pin 12 | Address |
|-----------|--------|--------|--------|---------|
| Left      | GND    | GND    | GND    | 0x00    |
| Middle    | HIGH   | GND    | GND    | 0x01    |
| Right     | GND    | HIGH   | GND    | 0x02    |

*HIGH = leave floating (internal pull-up)*

### 3. Pull-up Resistors

Check if your M0 boards have built-in pull-ups. If not:
- Add 4.7kΩ from +5V to SDA
- Add 4.7kΩ from +5V to SCL

---

## Software Setup (10 Minutes)

### 1. Enable I2C on Raspberry Pi

```bash
sudo raspi-config
# Navigate to: Interface Options → I2C → Enable
sudo reboot
```

### 2. Install Dependencies

```bash
pip3 install smbus2
```

### 3. Flash I2C Firmware

```bash
cd /path/to/NC4touch

# Compile firmware
~/bin/arduino-cli compile -b DFRobot:samd:mzero_bl M0Touch_I2C/M0Touch_I2C.ino

# Upload to each M0 (one at a time)
~/bin/arduino-cli upload --port /dev/ttyACM0 --fqbn DFRobot:samd:mzero_bl M0Touch_I2C/M0Touch_I2C.ino
# Repeat for ttyACM1 and ttyACM2
```

### 4. Update Configuration

Edit `~/chamber_config.yaml`:

```yaml
use_i2c: true
```

---

## Testing (2 Minutes)

### 1. Check I2C Bus

```bash
sudo apt-get install i2c-tools
sudo i2cdetect -y 1

# Should show devices at addresses 0x00, 0x01, 0x02
```

### 2. Test Discovery

```python
python3 << 'EOF'
from Controller.M0DeviceI2C import discover_i2c_devices

devices = discover_i2c_devices()
print(f"Found {len(devices)} devices:")
for addr, device_id in devices:
    print(f"  {addr:#04x}: {device_id}")
EOF

# Expected output:
# Found 3 devices:
#   0x00: M0_0
#   0x01: M0_1
#   0x02: M0_2
```

### 3. Test Chamber

```python
python3 << 'EOF'
from Controller.Chamber import Chamber

chamber = Chamber()
chamber.m0_initialize()

# Test each screen
for m0 in chamber.m0s:
    print(f"Testing {m0.id}...")
    m0.send_command("SHOW")

print("Success! All M0s responding via I2C")
EOF
```

---

## Common Commands

```python
from Controller.Chamber import Chamber

# Initialize with I2C
chamber = Chamber(chamber_config={"use_i2c": True})

# Send commands
chamber.m0s[0].send_command("IMG:A01")  # Load image
chamber.m0s[0].send_command("SHOW")     # Turn on screen
chamber.m0s[0].send_command("BLACK")    # Turn off screen

# Check for touch
if chamber.m0s[0].is_touched:
    print(f"Touch at ({chamber.m0s[0].last_touch_x}, {chamber.m0s[0].last_touch_y})")
```

---

## Troubleshooting

### No devices found

```bash
# Check I2C enabled
ls /dev/i2c-*  # Should show /dev/i2c-1

# Scan bus
sudo i2cdetect -y 1

# Check wiring
# - Verify SDA, SCL, GND connections
# - Check address pins on each M0
```

### Wrong device IDs

```bash
# Verify address configuration
# Re-flash firmware if needed
```

### Checksum errors

```bash
# Shorten I2C wires (< 30 cm)
# Add pull-up resistors if missing
# Check ground connection
```

---

## Rollback to Serial

If issues occur:

1. **Update config:**
   ```yaml
   use_i2c: false
   ```

2. **Re-flash serial firmware:**
   ```bash
   ~/bin/arduino-cli upload --port /dev/ttyACM0 \
                            --fqbn DFRobot:samd:mzero_bl \
                            M0Touch/M0Touch.ino
   ```

---

## Support

- **Full Documentation:** `docs/I2C_IMPLEMENTATION.md`
- **Implementation Summary:** `I2C_IMPLEMENTATION_SUMMARY.md`
- **Test Suite:** `tests/test_i2c.py`

---

**Setup Time:** ~15 minutes  
**Difficulty:** Intermediate  
**Reliability:** High (no USB race conditions)
