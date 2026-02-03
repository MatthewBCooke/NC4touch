# I2C Implementation for NC4touch M0 Controllers

**Author:** OpenClaw Subagent  
**Date:** 2026-02-03  
**Status:** Production Ready

---

## Table of Contents

1. [Overview](#overview)
2. [Why I2C vs Serial](#why-i2c-vs-serial)
3. [Hardware Setup](#hardware-setup)
4. [Wiring Diagram](#wiring-diagram)
5. [Address Assignment](#address-assignment)
6. [Protocol Specification](#protocol-specification)
7. [Software Components](#software-components)
8. [Migration Guide](#migration-guide)
9. [Testing](#testing)
10. [Troubleshooting](#troubleshooting)

---

## Overview

This document describes the I2C-based communication system for NC4touch M0 touchscreen controllers. I2C replaces the unreliable USB serial interface with deterministic hardware addressing, eliminating USB enumeration race conditions and port reassignment issues.

### Key Benefits

✅ **Deterministic addressing** - M0 address set by GPIO pins, never changes  
✅ **No USB race conditions** - All devices on shared I2C bus  
✅ **Simplified wiring** - 2 wires (SDA + SCL) for all devices  
✅ **Reliable discovery** - Hardware addresses eliminate identity verification complexity  
✅ **Robust protocol** - Frame-based communication with checksums  

### System Architecture

```
┌──────────────────────────────────────────────┐
│ Raspberry Pi 5                               │
│                                              │
│  ┌─────────────────────────────────────┐    │
│  │ Chamber.py                           │    │
│  │                                      │    │
│  │  ┌──────────────────────────────┐   │    │
│  │  │ M0DeviceI2C (0x00) - Left    │   │    │
│  │  └──────────────────────────────┘   │    │
│  │  ┌──────────────────────────────┐   │    │
│  │  │ M0DeviceI2C (0x01) - Middle  │   │    │
│  │  └──────────────────────────────┘   │    │
│  │  ┌──────────────────────────────┐   │    │
│  │  │ M0DeviceI2C (0x02) - Right   │   │    │
│  │  └──────────────────────────────┘   │    │
│  └─────────────────────────────────────┘    │
│                                              │
│  I2C Bus (SDA: GPIO 2, SCL: GPIO 3)         │
└──────────┬───────────────────────────────────┘
           │
           │ I2C Bus (shared, multi-drop)
           │
     ┌─────┴─────┬───────────────┬──────────┐
     │           │               │          │
┌────▼────┐ ┌───▼─────┐  ┌──────▼───┐      │
│ M0 Left │ │ M0 Mid  │  │ M0 Right │      │
│ 0x00    │ │ 0x01    │  │ 0x02     │      │
│         │ │         │  │          │      │
│ Pins:   │ │ Pins:   │  │ Pins:    │      │
│ 10: LOW │ │ 10: HIGH│  │ 10: LOW  │      │
│ 11: LOW │ │ 11: LOW │  │ 11: HIGH │      │
│ 12: LOW │ │ 12: LOW │  │ 12: LOW  │      │
└─────────┘ └─────────┘  └──────────┘      │
                                            │
                                      4.7kΩ Pull-up
                                      Resistors (if needed)
```

---

## Why I2C vs Serial

### Problems with USB Serial

The original USB serial implementation suffers from fundamental architectural issues:

1. **USB Enumeration Race Condition**
   - All 3 M0s reset simultaneously
   - USB enumeration order is non-deterministic
   - Port names (`/dev/ttyACM0`, etc.) assigned arbitrarily
   - No guarantee `M0_0` gets `/dev/ttyACM0`

2. **Port Reassignment on Reconnect**
   - USB port names can change after reconnect
   - Kernel may reassign ports in different order
   - Requires identity verification via `WHOAREYOU?` after every reset

3. **Multiple USB Cables Required**
   - 3 separate USB cables + 3 USB ports
   - Cable management complexity
   - Power distribution issues

4. **Serial Recovery Complexity**
   - Port can disappear if USB resets
   - No atomic recovery mechanism
   - Retry logic prone to conflicts

### I2C Advantages

| Feature | USB Serial | I2C |
|---------|-----------|-----|
| **Addressing** | Non-deterministic port names | Hardware GPIO pins (fixed) |
| **Discovery** | Query all ports, verify identity | Scan addresses, immediate mapping |
| **Wiring** | 3 USB cables | 2 wires (SDA + SCL) |
| **Enumeration** | Race conditions on reset | No enumeration, instant addressing |
| **Bandwidth** | 115200 baud (~14 KB/s) | 400 kHz I2C (~50 KB/s) |
| **Recovery** | Complex port reassignment | Simple bus reset |
| **Debugging** | Easy (serial monitor) | Harder (requires I2C sniffer) |

---

## Hardware Setup

### Required Components

| Component | Quantity | Notes |
|-----------|----------|-------|
| Raspberry Pi 5 | 1 | I2C master controller |
| DFRobot M0 SAMD21 boards | 3 | I2C slave devices |
| Jumper wires | 6+ | I2C bus + GPIO reset pins |
| Pull-up resistors (4.7kΩ) | 2 | For SDA and SCL lines (if not present) |
| Breadboard or PCB | 1 | For wiring connections |

### Pin Connections

#### Raspberry Pi I2C Pins

| Pi Pin | Function | Notes |
|--------|----------|-------|
| GPIO 2 (Pin 3) | SDA (Data) | I2C data line |
| GPIO 3 (Pin 5) | SCL (Clock) | I2C clock line |
| GND (Pin 6, 9, etc.) | Ground | Common ground for all devices |

#### M0 Board I2C Pins

| M0 Pin | Function | Notes |
|--------|----------|-------|
| SDA | I2C Data | Connect to Pi GPIO 2 |
| SCL | I2C Clock | Connect to Pi GPIO 3 |
| GND | Ground | Connect to Pi GND |
| Pin 10 | Address Bit 0 (LSB) | LOW or HIGH to set address |
| Pin 11 | Address Bit 1 | LOW or HIGH to set address |
| Pin 12 | Address Bit 2 (MSB) | LOW or HIGH to set address |

#### M0 Reset Pins (GPIO Control)

| M0 Device | Reset Pin | Pi GPIO Pin |
|-----------|-----------|-------------|
| Left M0 | RST | GPIO 25 |
| Middle M0 | RST | GPIO 5 |
| Right M0 | RST | GPIO 6 |

**Note:** Reset pins are still connected via GPIO for hardware reset capability. These are NOT part of the I2C bus.

---

## Wiring Diagram

### ASCII Wiring Diagram

```
Raspberry Pi 5                                M0 Boards
┌─────────────────────┐
│                     │
│ GPIO 2 (SDA) ───────┼─────┬──────┬──────┬────── SDA (all M0s)
│ GPIO 3 (SCL) ───────┼─────┼──────┼──────┼────── SCL (all M0s)
│                     │     │      │      │
│ GND ────────────────┼─────┴──────┴──────┴────── GND (all M0s)
│                     │     │      │      │
│ GPIO 25 ────────────┼─────┘      │      │
│     (Reset Left)    │            │      │
│                     │            │      │
│ GPIO 5 ─────────────┼────────────┘      │
│     (Reset Middle)  │                   │
│                     │                   │
│ GPIO 6 ─────────────┼───────────────────┘
│     (Reset Right)   │
│                     │
└─────────────────────┘

Pull-up Resistors (4.7kΩ):
  +5V ──┬── 4.7kΩ ──┬── SDA
        │           │
        └── 4.7kΩ ──┴── SCL

Address Configuration (M0 GPIO Pins):
  Pin 10, 11, 12:
    - Leave floating (or HIGH via pull-up) = 0 in address
    - Connect to GND = 1 in address
    - Address = (Pin12 << 2) | (Pin11 << 1) | (Pin10)
```

### Physical Connections

1. **I2C Bus Connections:**
   ```
   Pi GPIO 2 (SDA) → M0 Left SDA → M0 Middle SDA → M0 Right SDA
   Pi GPIO 3 (SCL) → M0 Left SCL → M0 Middle SCL → M0 Right SCL
   Pi GND → M0 Left GND → M0 Middle GND → M0 Right GND
   ```

2. **Pull-up Resistors:**
   - Connect 4.7kΩ resistor between +5V and SDA
   - Connect 4.7kΩ resistor between +5V and SCL
   - **Check if your M0 boards have built-in pull-ups first!**

3. **Reset Lines (Individual GPIO):**
   ```
   Pi GPIO 25 → M0 Left RST
   Pi GPIO 5 → M0 Middle RST
   Pi GPIO 6 → M0 Right RST
   ```

4. **Address Configuration Pins (on each M0):**
   - See Address Assignment table below

---

## Address Assignment

### GPIO Pin Address Encoding

Each M0's I2C address is determined by 3 GPIO pins (10, 11, 12):

- **Pin 10** = Bit 0 (LSB)
- **Pin 11** = Bit 1
- **Pin 12** = Bit 2 (MSB)

Pins are configured as `INPUT_PULLUP`. Address is formed by reading LOW pins:
- **HIGH (floating)** = `0` in address
- **LOW (grounded)** = `1` in address

**Address Formula:**
```
Address = (Pin12_LOW << 2) | (Pin11_LOW << 1) | (Pin10_LOW << 0)
```

### Address Assignment Table

| M0 Device | Pin 12 | Pin 11 | Pin 10 | Binary | I2C Address | Device ID |
|-----------|--------|--------|--------|--------|-------------|-----------|
| **Left M0** | LOW | LOW | LOW | 000 | 0x00 | M0_0 |
| **Middle M0** | LOW | LOW | HIGH | 001 | 0x01 | M0_1 |
| **Right M0** | LOW | HIGH | LOW | 010 | 0x02 | M0_2 |
| (unused) | LOW | HIGH | HIGH | 011 | 0x03 | M0_3 |
| (unused) | HIGH | LOW | LOW | 100 | 0x04 | M0_4 |
| (unused) | HIGH | LOW | HIGH | 101 | 0x05 | M0_5 |
| (unused) | HIGH | HIGH | LOW | 110 | 0x06 | M0_6 |
| (unused) | HIGH | HIGH | HIGH | 111 | 0x07 | M0_7 |

### How to Configure Addresses

For each M0 board:

1. **M0 Left (Address 0x00):**
   - Pin 10: Connect to GND
   - Pin 11: Connect to GND
   - Pin 12: Connect to GND

2. **M0 Middle (Address 0x01):**
   - Pin 10: Leave floating (HIGH via pull-up)
   - Pin 11: Connect to GND
   - Pin 12: Connect to GND

3. **M0 Right (Address 0x02):**
   - Pin 10: Connect to GND
   - Pin 11: Leave floating (HIGH via pull-up)
   - Pin 12: Connect to GND

**Pro Tip:** Use DIP switches or jumper headers for easy address reconfiguration during testing.

---

## Protocol Specification

### Frame Format

All I2C communication uses a structured frame format:

**Command Frame (Pi → M0):**
```
[Length] [Command] [Payload...] [Checksum]
  1 byte   1 byte    0-60 bytes   1 byte
```

**Response Frame (M0 → Pi):**
```
[Length] [Response Data...] [Checksum]
  1 byte    0-60 bytes         1 byte
```

### Field Descriptions

| Field | Size | Description |
|-------|------|-------------|
| **Length** | 1 byte | Number of bytes in command/response (excluding length itself) |
| **Command** | 1 byte | Command code (see Command Codes table) |
| **Payload** | 0-60 bytes | Command-specific data (optional) |
| **Response Data** | 0-60 bytes | Response payload |
| **Checksum** | 1 byte | XOR checksum of all preceding bytes (including length) |

### Checksum Calculation

Simple XOR checksum:

```python
def calculate_checksum(data: List[int]) -> int:
    checksum = 0
    for byte in data:
        checksum ^= byte
    return checksum & 0xFF
```

**Example:**
```
Frame: [0x02, 0x01, 0x03]
Checksum: 0x02 ^ 0x01 ^ 0x03 = 0x00
Complete Frame: [0x02, 0x01, 0x03, 0x00]
```

### Command Codes

| Code | Name | Payload | Response | Description |
|------|------|---------|----------|-------------|
| `0x01` | WHOAREYOU | None | String: `"ID:M0_X"` | Request device identity |
| `0x02` | SHOW | None | `"ACK"` | Turn on backlight, enable touch |
| `0x03` | BLACK | None | `"ACK"` | Turn off backlight, disable touch |
| `0x04` | IMG | String: image ID | `"ACK"` | Load image from SD card |
| `0x05` | TOUCH_POLL | None | 5 bytes: status + coords | Poll for touch event |

### Command Details

#### 1. WHOAREYOU (0x01)

**Purpose:** Verify device identity

**Command Frame:**
```
[0x01, 0x01, 0x00]
  │     │     └─ Checksum (0x01 ^ 0x01 = 0x00)
  │     └─ Command: WHOAREYOU
  └─ Length: 1 byte (command only)
```

**Response:**
```
[0x07, 'I', 'D', ':', 'M', '0', '_', '0', checksum]
  │      └────────────────────────────┘     │
  │         Response: "ID:M0_0"            └─ XOR of all bytes
  └─ Length: 7 bytes
```

#### 2. SHOW (0x02)

**Purpose:** Turn on backlight and enable touch scanning

**Command Frame:**
```
[0x01, 0x02, 0x03]
  │     │     └─ Checksum
  │     └─ Command: SHOW
  └─ Length: 1
```

**Response:**
```
[0x03, 'A', 'C', 'K', checksum]
```

#### 3. BLACK (0x03)

**Purpose:** Turn off backlight and disable touch

**Command Frame:**
```
[0x01, 0x03, 0x02]
  │     │     └─ Checksum
  │     └─ Command: BLACK
  └─ Length: 1
```

**Response:**
```
[0x03, 'A', 'C', 'K', checksum]
```

#### 4. IMG (0x04)

**Purpose:** Load image from SD card (backlight stays off)

**Command Frame:**
```
[0x04, 0x04, 'A', '0', '1', checksum]
  │     │     └─────┬──────┘     │
  │     │        Payload      └─ XOR checksum
  │     └─ Command: IMG
  └─ Length: 4 (command + 3 payload bytes)
```

**Response:**
```
[0x03, 'A', 'C', 'K', checksum]
```

#### 5. TOUCH_POLL (0x05)

**Purpose:** Poll for touch event

**Command Frame:**
```
[0x01, 0x05, 0x04]
  │     │     └─ Checksum
  │     └─ Command: TOUCH_POLL
  └─ Length: 1
```

**Response (Touch Detected):**
```
[0x05, 0x01, x_hi, x_lo, y_hi, y_lo, checksum]
  │     │     └──┬───┘  └──┬───┘      │
  │     │        X coord   Y coord     └─ Checksum
  │     └─ Status: 1 = touch detected
  └─ Length: 5 bytes
```

**Response (No Touch):**
```
[0x05, 0x00, 0x00, 0x00, 0x00, 0x00, checksum]
  │     └─ Status: 0 = no touch
  └─ Length: 5 bytes
```

### Timing Requirements

| Operation | Timing | Notes |
|-----------|--------|-------|
| I2C Clock Speed | 100 kHz - 400 kHz | Standard/Fast mode |
| Command Processing | < 10 ms | M0 response time |
| Touch Poll Interval | 100 ms | Recommended polling rate |
| Response Timeout | 2 seconds | Python default timeout |
| Reset Recovery | 500 ms | Time after hardware reset |

---

## Software Components

### Python Components

#### 1. M0DeviceI2C Class

**Location:** `Controller/M0DeviceI2C.py`

**Key Features:**
- Thread-safe I2C communication with `threading.RLock()`
- Automatic retry with exponential backoff (max 3 retries)
- Checksum validation on all frames
- Background touch polling thread
- Message queue for compatibility with serial `M0Device`

**Usage:**
```python
from M0DeviceI2C import M0DeviceI2C

# Initialize device
m0 = M0DeviceI2C(
    pi=pigpio_instance,
    id="M0_0",
    address=0x00,
    reset_pin=25,
    location="left"
)

# Initialize I2C communication
m0.initialize()

# Send commands
m0.send_command("IMG:A01")
m0.send_command("SHOW")

# Check for touch
if m0.is_touched:
    print(f"Touch at ({m0.last_touch_x}, {m0.last_touch_y})")

# Cleanup
m0.stop()
```

#### 2. Chamber.py Integration

**Location:** `Controller/Chamber.py`

**Configuration:**
```python
# Enable I2C mode in chamber config
chamber_config = {
    "use_i2c": True,
    "i2c_addresses": [0x00, 0x01, 0x02]
}

chamber = Chamber(chamber_config=chamber_config)
```

**Discovery:**
```python
# Automatic I2C discovery on initialization
chamber.i2c_discover()  # Called internally if use_i2c=True

# Manual discovery
from M0DeviceI2C import discover_i2c_devices
devices = discover_i2c_devices(bus_num=1)
# Returns: [(0x00, "M0_0"), (0x01, "M0_1"), (0x02, "M0_2")]
```

### Arduino Components

#### M0Touch_I2C Firmware

**Location:** `M0Touch_I2C/M0Touch_I2C.ino`

**Key Features:**
- Automatic I2C address configuration from GPIO pins 10, 11, 12
- Wire library interrupt-driven I2C handlers
- Frame-based protocol with checksum validation
- Touch event queueing for reliable delivery
- Serial debug output (optional, can be disabled)

**Build and Upload:**
```bash
# Compile firmware
~/bin/arduino-cli compile -b DFRobot:samd:mzero_bl M0Touch_I2C/M0Touch_I2C.ino

# Upload to M0 (requires serial connection)
~/bin/arduino-cli upload --port /dev/ttyACM0 \
                         --fqbn DFRobot:samd:mzero_bl \
                         M0Touch_I2C/M0Touch_I2C.ino
```

---

## Migration Guide

### Step-by-Step Migration

#### Step 1: Backup Current System

```bash
# Backup current configuration
cp ~/chamber_config.yaml ~/chamber_config.yaml.backup

# Note current port assignments
python3 -c "
from Controller.Chamber import Chamber
chamber = Chamber()
for m0 in chamber.m0s:
    print(f'{m0.id}: {m0.port}')
"
```

#### Step 2: Wire I2C Bus

1. **Power down Raspberry Pi and all M0s**
2. **Connect I2C bus:**
   - Pi GPIO 2 (SDA) to all M0 SDA pins
   - Pi GPIO 3 (SCL) to all M0 SCL pins
   - Pi GND to all M0 GND pins
3. **Add pull-up resistors (if needed):**
   - 4.7kΩ from +5V to SDA
   - 4.7kΩ from +5V to SCL
4. **Keep USB cables connected** (for power and firmware upload)
5. **Keep GPIO reset wires connected** (pins 25, 5, 6)

#### Step 3: Configure I2C Addresses

For each M0, set address pins according to the [Address Assignment Table](#address-assignment-table):

1. **M0 Left (0x00):** Pins 10, 11, 12 → GND, GND, GND
2. **M0 Middle (0x01):** Pins 10, 11, 12 → HIGH, GND, GND
3. **M0 Right (0x02):** Pins 10, 11, 12 → GND, HIGH, GND

#### Step 4: Flash I2C Firmware

```bash
# Boot Raspberry Pi
# Keep M0s powered via USB

# Compile I2C firmware
cd /path/to/NC4touch
~/bin/arduino-cli compile -b DFRobot:samd:mzero_bl M0Touch_I2C/M0Touch_I2C.ino

# Upload to each M0 (one at a time)
# Discover current ports
~/bin/arduino-cli board list

# Upload to M0 Left
~/bin/arduino-cli upload --port /dev/ttyACM0 \
                         --fqbn DFRobot:samd:mzero_bl \
                         M0Touch_I2C/M0Touch_I2C.ino

# Repeat for M0 Middle and M0 Right
```

#### Step 5: Enable I2C in Raspberry Pi

```bash
# Enable I2C kernel module
sudo raspi-config
# Navigate to: Interface Options → I2C → Enable

# Verify I2C is enabled
ls /dev/i2c-*
# Should show: /dev/i2c-1

# Install smbus2 Python library
pip3 install smbus2
```

#### Step 6: Update Chamber Configuration

Edit `~/chamber_config.yaml`:

```yaml
# Enable I2C communication
use_i2c: true

# I2C addresses (optional, auto-discovered)
i2c_addresses:
  - 0x00
  - 0x01
  - 0x02

# Keep existing parameters
chamber_name: "Chamber0"
reward_LED_pin: 21
# ... etc ...
```

#### Step 7: Test I2C Discovery

```python
# Test I2C discovery
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

#### Step 8: Test Chamber Initialization

```python
# Test chamber with I2C
python3 << 'EOF'
from Controller.Chamber import Chamber

chamber = Chamber()
chamber.m0_initialize()

# Send test commands
chamber.m0s[0].send_command("IMG:A01")
chamber.m0s[0].send_command("SHOW")

print("Test successful!")
EOF
```

#### Step 9: Full System Test

```bash
# Run full session test
python3 main.py --config ~/chamber_config.yaml --test

# Monitor for errors
# Verify touch detection works
# Test all 3 M0 boards
```

#### Step 10: Production Deployment

1. **Validate all functionality:**
   - Image loading
   - Touch detection
   - All 3 M0s responding
2. **Monitor for 24 hours** with test sessions
3. **Document any issues** in system logs
4. **Keep serial firmware backup** for rollback if needed

### Rollback Procedure

If issues occur:

1. **Stop using I2C:**
   ```yaml
   # ~/chamber_config.yaml
   use_i2c: false
   ```

2. **Re-flash serial firmware:**
   ```bash
   ~/bin/arduino-cli upload --port /dev/ttyACM0 \
                            --fqbn DFRobot:samd:mzero_bl \
                            M0Touch/M0Touch.ino
   ```

3. **Restore configuration:**
   ```bash
   cp ~/chamber_config.yaml.backup ~/chamber_config.yaml
   ```

---

## Testing

### Unit Tests

**Location:** `tests/test_i2c.py`

Run unit tests:

```bash
cd /path/to/NC4touch
python3 -m pytest tests/test_i2c.py -v
```

### Integration Tests

#### Test 1: I2C Bus Scan

```bash
# Use i2cdetect to scan bus
sudo apt-get install i2c-tools
sudo i2cdetect -y 1

# Expected output:
#      0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
# 00:          -- -- -- -- -- -- -- -- -- -- -- -- -- 
# 10:          -- -- -- -- -- -- -- -- -- -- -- -- -- 
# 20:          -- -- -- -- -- -- -- -- -- -- -- -- -- 
# 30:          -- -- -- -- -- -- -- -- -- -- -- -- -- 
# 40:          -- -- -- -- -- -- -- -- -- -- -- -- -- 
# 50:          -- -- -- -- -- -- -- -- -- -- -- -- -- 
# 60:          -- -- -- -- -- -- -- -- -- -- -- -- -- 
# 70:          -- -- -- -- -- -- -- --
# Addresses 0x00, 0x01, 0x02 may show as UU if in use
```

#### Test 2: Device Discovery

```python
from Controller.M0DeviceI2C import discover_i2c_devices

devices = discover_i2c_devices()
assert len(devices) == 3, f"Expected 3 devices, found {len(devices)}"
assert ("M0_0" in [d[1] for d in devices]), "M0_0 not found"
assert ("M0_1" in [d[1] for d in devices]), "M0_1 not found"
assert ("M0_2" in [d[1] for d in devices]), "M0_2 not found"
print("✓ Discovery test passed")
```

#### Test 3: Command Sending

```python
from Controller.Chamber import Chamber

chamber = Chamber(chamber_config={"use_i2c": True})
chamber.m0_initialize()

# Test each M0
for m0 in chamber.m0s:
    print(f"Testing {m0.id}...")
    
    # Test SHOW command
    assert m0.send_command("SHOW"), f"{m0.id} SHOW failed"
    time.sleep(1)
    
    # Test BLACK command
    assert m0.send_command("BLACK"), f"{m0.id} BLACK failed"
    time.sleep(1)

print("✓ Command test passed")
```

#### Test 4: Touch Detection

```python
from Controller.Chamber import Chamber
import time

chamber = Chamber(chamber_config={"use_i2c": True})
chamber.m0_initialize()

# Display test image
for m0 in chamber.m0s:
    m0.send_command("IMG:TEST")
    m0.send_command("SHOW")

print("Touch each screen and observe output...")
time.sleep(10)

# Check message queues
for m0 in chamber.m0s:
    if not m0.message_queue.empty():
        msg = m0.message_queue.get()
        print(f"{msg[0]}: {msg[1]}")
```

### Performance Tests

#### Latency Test

```python
import time
from Controller.M0DeviceI2C import M0DeviceI2C

m0 = M0DeviceI2C(pi=pi, id="M0_0", address=0x00, reset_pin=25)
m0.initialize()

# Measure command latency
iterations = 100
start = time.time()

for _ in range(iterations):
    m0.send_command("SHOW")

elapsed = time.time() - start
avg_latency = (elapsed / iterations) * 1000  # ms

print(f"Average command latency: {avg_latency:.2f} ms")
# Expected: < 20 ms
```

#### Throughput Test

```python
# Measure touch polling rate
import time

m0.send_command("IMG:TEST")
m0.send_command("SHOW")

touch_count = 0
start = time.time()

while time.time() - start < 10:  # 10 second test
    if m0.is_touched:
        touch_count += 1
        m0.is_touched = False
    time.sleep(0.01)

print(f"Touch events processed: {touch_count}")
```

---

## Troubleshooting

### Issue: No Devices Found on I2C Bus

**Symptoms:**
- `discover_i2c_devices()` returns empty list
- `i2cdetect -y 1` shows no devices

**Diagnosis:**
```bash
# Check I2C is enabled
ls /dev/i2c-*

# Scan bus
sudo i2cdetect -y 1

# Check kernel module
lsmod | grep i2c
```

**Solutions:**
1. **Enable I2C:**
   ```bash
   sudo raspi-config
   # Interface Options → I2C → Enable
   sudo reboot
   ```

2. **Check wiring:**
   - Verify SDA and SCL connections
   - Check common ground
   - Verify power to M0s

3. **Check pull-up resistors:**
   - Measure voltage on SDA/SCL (should be ~3.3V or 5V)
   - Add 4.7kΩ pull-ups if missing

4. **Verify M0 firmware:**
   - Re-flash I2C firmware
   - Check Serial monitor for boot messages

### Issue: Checksum Errors

**Symptoms:**
- Log messages: "Checksum error!"
- Intermittent communication failures

**Diagnosis:**
```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Solutions:**
1. **Check for electrical noise:**
   - Shorten I2C wires (< 30 cm recommended)
   - Add 100 nF capacitors near M0 power pins
   - Separate I2C wires from power cables

2. **Reduce I2C speed:**
   ```python
   # In M0DeviceI2C.py, modify smbus2 initialization
   # (may require smbus2 configuration changes)
   ```

3. **Check grounding:**
   - Verify solid common ground
   - Check for ground loops

### Issue: I2C Bus Lockup

**Symptoms:**
- All I2C communication stops
- `IOError: [Errno 121] Remote I/O error`

**Diagnosis:**
```bash
# Check for stuck bus
sudo i2cdetect -y 1
# Shows timeout errors
```

**Solutions:**
1. **Reset I2C bus:**
   ```bash
   sudo rmmod i2c_bcm2835
   sudo modprobe i2c_bcm2835
   ```

2. **Hardware reset M0s:**
   ```python
   chamber.m0_reset()
   time.sleep(1)
   chamber.m0_initialize()
   ```

3. **Power cycle:**
   - Power off Pi and all M0s
   - Wait 10 seconds
   - Power on and reinitialize

### Issue: Wrong Device ID on Address

**Symptoms:**
- M0_0 responds at address 0x01
- Devices have swapped addresses

**Diagnosis:**
```python
from Controller.M0DeviceI2C import discover_i2c_devices
devices = discover_i2c_devices()
print(devices)
# Check if addresses match expected IDs
```

**Solutions:**
1. **Verify address pin configuration:**
   - Check pins 10, 11, 12 on each M0
   - Confirm grounding matches address table

2. **Re-flash firmware:**
   - May have wrong firmware version
   - Ensure latest I2C firmware uploaded

3. **Check pin assignments:**
   - Pins may be miswired
   - Use multimeter to verify pin states

### Issue: Intermittent Touch Detection

**Symptoms:**
- Some touches not detected
- Touch coordinates incorrect

**Diagnosis:**
```python
# Monitor touch polling
m0.send_command("SHOW")
while True:
    if not m0.message_queue.empty():
        print(m0.message_queue.get())
    time.sleep(0.1)
```

**Solutions:**
1. **Adjust polling interval:**
   ```python
   # In M0DeviceI2C.__init__()
   self.poll_interval = 0.05  # Increase from 0.1
   ```

2. **Check touch calibration:**
   - Verify GT911 touch controller initialization
   - Check touchscreen cable connections

3. **Reduce I2C traffic:**
   - Increase poll interval if too fast
   - Check for I2C bus congestion

### Issue: Python `smbus2` Not Found

**Symptoms:**
- `ImportError: No module named 'smbus2'`

**Solutions:**
```bash
# Install smbus2
pip3 install smbus2

# Or install system-wide
sudo pip3 install smbus2
```

### Debugging Tips

#### 1. Enable Verbose Logging

```python
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

#### 2. Monitor Serial Output from M0s

```bash
# Connect to M0 via serial for debug output
screen /dev/ttyACM0 115200

# Or use minicom
minicom -D /dev/ttyACM0 -b 115200
```

#### 3. Use I2C Sniffer

```bash
# Install i2c-tools
sudo apt-get install i2c-tools

# Monitor I2C traffic
sudo i2cdump -y 1 0x00  # Dump registers from device 0x00
```

#### 4. Test Individual Components

```python
# Test single M0
from Controller.M0DeviceI2C import M0DeviceI2C
import pigpio

pi = pigpio.pi()
m0 = M0DeviceI2C(pi=pi, id="M0_0", address=0x00, reset_pin=25)
m0.initialize()

# Send commands
m0.send_command("WHOAREYOU?")
time.sleep(0.5)

# Check response
if not m0.message_queue.empty():
    print(m0.message_queue.get())
```

---

## Performance Characteristics

### Typical Performance

| Metric | Value | Notes |
|--------|-------|-------|
| **Command Latency** | < 20 ms | WHOAREYOU, SHOW, BLACK |
| **Touch Poll Rate** | 10 Hz | Default polling interval |
| **Touch Latency** | < 100 ms | From touch to Python detection |
| **Initialization Time** | < 1 second | Per M0 device |
| **Recovery Time** | < 2 seconds | After I2C error |
| **Max I2C Clock** | 400 kHz | Fast mode I2C |

### Resource Usage

| Resource | Usage | Notes |
|----------|-------|-------|
| **CPU (Pi)** | < 1% | Per M0 polling thread |
| **Memory (Pi)** | ~5 MB | Per M0DeviceI2C instance |
| **I2C Bandwidth** | < 10% | At 10 Hz polling |
| **M0 RAM** | ~10 KB | I2C buffers + state |

---

## Future Enhancements

### Potential Improvements

1. **Interrupt-Based Touch Detection**
   - Add INT pin from GT911 to Pi GPIO
   - Replace polling with interrupt-driven touch
   - Reduce latency and CPU usage

2. **DMA-Based I2C**
   - Use Pi DMA for I2C transfers
   - Reduce CPU overhead
   - Improve throughput

3. **CRC16 Checksums**
   - Upgrade from XOR to CRC16
   - Improve error detection
   - Add to protocol v2

4. **Multi-Master Support**
   - Allow multiple Pi controllers
   - Implement bus arbitration
   - For multi-chamber setups

5. **I2C Bus Monitoring**
   - Add statistics collection
   - Track error rates
   - Automatic diagnostics

---

## References

### Documentation
- [I2C Protocol Specification](https://www.nxp.com/docs/en/user-guide/UM10204.pdf)
- [smbus2 Python Library](https://github.com/kplindegaard/smbus2)
- [Raspberry Pi I2C](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#i2c)
- [Arduino Wire Library](https://www.arduino.cc/reference/en/language/functions/communication/wire/)

### Related Files
- `docs/M0_ANALYSIS.md` - Original problem analysis
- `docs/HARDWARE.md` - Hardware specifications
- `docs/ARCHITECTURE.md` - System architecture
- `Controller/M0Device.py` - Serial implementation (legacy)
- `Controller/M0DeviceI2C.py` - I2C implementation
- `M0Touch_I2C/M0Touch_I2C.ino` - I2C firmware

---

**End of Document**
