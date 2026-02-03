# NC4touch Hardware Documentation

## System Overview

NC4touch is a Raspberry Pi-based touchscreen training system for rodents. The hardware consists of:
- **Controller:** Raspberry Pi 5 (running Raspberry Pi OS 64-bit)
- **Touchscreens:** 3x DFRobot M0 boards with capacitive touchscreen displays
- **Peripherals:** LEDs, reward pump, IR beam break sensor, buzzer, USB camera
- **Communication:** USB serial (M0s), GPIO (pigpio for peripherals)

## Hardware Components List

### Controller
| Component | Model/Description | Interface | Notes |
|-----------|-------------------|-----------|-------|
| Main Controller | Raspberry Pi 5 | - | Runs Raspberry Pi OS (64-bit) |
| Power Supply | 5V, 3A+ | USB-C | Powers Pi and peripherals |

### Touchscreen Displays
| Component | Model/Description | Interface | Quantity | Notes |
|-----------|-------------------|-----------|----------|-------|
| M0 Board | DFRobot SAMD21 M0 (VID:0x2341, PID:0x0244) | USB Serial (115200 baud) | 3 | Left, Middle, Right positions |
| Display | Capacitive touchscreen (exact model TBD) | Connected to M0 SPI | 3 | Images loaded from M0 SD card |
| Reset Control | GPIO-controlled reset per M0 | GPIO pins 25, 5, 6 | 3 | Hardware reset capability |

### Visual Indicators
| Component | Description | Interface | GPIO Pin | Notes |
|-----------|-------------|-----------|----------|-------|
| Reward LED | Indicates reward availability | PWM (pigpio) | 21 | Default brightness: 140/255 |
| Punishment LED | Signals incorrect response | PWM (pigpio) | 17 | Default brightness: 255/255 |
| House LED | General chamber illumination | PWM (pigpio) | 20 | Default brightness: 100/255 |

### Reward System
| Component | Description | Interface | GPIO Pin | Notes |
|-----------|-------------|-----------|----------|-------|
| Reward Pump | Peristaltic pump for liquid reward | PWM (pigpio) | 27 | Activated during reward delivery |
| Beam Break Sensor | IR sensor to detect reward collection | Digital Input (pigpio) | 4 | Pull-up enabled, monitors food/water port |

### Auditory Output
| Component | Description | Interface | GPIO Pin | Notes |
|-----------|-------------|-----------|----------|-------|
| Buzzer | Auditory stimulus/punishment | PWM (pigpio) | 16 | Frequency/duration configurable |

### Video Recording
| Component | Description | Interface | Device | Notes |
|-----------|-------------|-----------|--------|-------|
| USB Camera | Video recording and streaming | USB | /dev/video0 | Streams via ustreamer (port 8080) |

## Pin Assignments

All GPIO pin assignments are defined in `Chamber.py` with configurable defaults via `Config` class.

### Default GPIO Pin Configuration

```python
# From Chamber.py Config defaults:
"reward_LED_pin": 21         # Reward indicator LED
"reward_pump_pin": 27        # Reward pump control
"beambreak_pin": 4           # IR beam break sensor
"punishment_LED_pin": 17     # Punishment/error indicator LED
"house_LED_pin": 20          # House light
"buzzer_pin": 16             # Buzzer/speaker
"reset_pins": [25, 5, 6]     # M0 hardware reset pins (left, middle, right)
"camera_device": "/dev/video0"  # USB camera device
```

### GPIO Pin Summary Table

| GPIO Pin | Component | Type | PWM | Pull-up/down | Notes |
|----------|-----------|------|-----|--------------|-------|
| 4 | Beam Break Sensor | Input | No | Pull-up | Active low (0 = beam broken) |
| 5 | M0 Middle Reset | Output | No | - | Active low reset pulse |
| 6 | M0 Right Reset | Output | No | - | Active low reset pulse |
| 16 | Buzzer | Output | Yes | - | Frequency: 5000 Hz |
| 17 | Punishment LED | Output | Yes | - | PWM range: 0-255 |
| 20 | House LED | Output | Yes | - | PWM range: 0-255 |
| 21 | Reward LED | Output | Yes | - | PWM range: 0-255 |
| 25 | M0 Left Reset | Output | No | - | Active low reset pulse |
| 27 | Reward Pump | Output | Yes | - | PWM range: 0-255 |

### PWM Configuration (pigpio)
- **Frequency:** 5000 Hz (all PWM channels)
- **Range:** 0-255 (8-bit resolution)
- **Duty Cycle:** Controlled via `set_PWM_dutycycle(pin, value)`

### M0 Reset Sequence
```python
# Hardware reset performed via GPIO:
pi.set_mode(reset_pin, pigpio.OUTPUT)
pi.write(reset_pin, 0)   # Pull low
time.sleep(0.01)
pi.write(reset_pin, 1)   # Release
pi.set_mode(reset_pin, pigpio.INPUT)  # Return to high-Z
```

## Communication Protocols

### 1. Serial Communication (M0 Devices)

#### Physical Layer
- **Interface:** USB CDC ACM (Virtual COM Port)
- **Device Path:** `/dev/ttyACM0`, `/dev/ttyACM1`, `/dev/ttyACM2`
- **Baud Rate:** 115200
- **Data Bits:** 8
- **Parity:** None
- **Stop Bits:** 1
- **Flow Control:** None

#### Device Discovery
```bash
# Arduino CLI discovery (preferred method):
~/bin/arduino-cli board list --format json

# Filters for VID:0x2341 and PID:0x0244 (DFRobot M0)
# Returns: Port address (e.g., /dev/ttyACM0)
```

#### Protocol Specification

**Message Format:**
- ASCII text
- Newline-terminated (`\n`)
- Commands case-sensitive

**Python → M0 Commands:**
| Command | Description | Example |
|---------|-------------|---------|
| `WHOAREYOU?` | Request device identification | Response: `ID:M0_0` |
| `IMG:filename` | Load image from SD card | `IMG:A01` |
| `SHOW` | Display loaded image | - |
| `BLACK` | Clear screen to black | - |

**M0 → Python Responses:**
| Response | Description | Example |
|----------|-------------|---------|
| `ID:M0_x` | Device ID string | `ID:M0_1` |
| `TOUCH:x,y` | Touch event with coordinates | `TOUCH:120,80` |
| `IMG:OK` | Image loaded successfully | - |
| `IMG:ERROR` | Image load failed | - |

**Touch Event Format:**
```
TOUCH:x,y
├── x: Horizontal coordinate (0-319 typical)
└── y: Vertical coordinate (0-239 typical)

Example: "TOUCH:120,80\n"
```

#### Serial Connection Management
- **Persistent Connection:** Single serial connection per M0, maintained throughout session
- **Read Thread:** Background thread (`M0Device.read_loop()`) continuously reads incoming data
- **Write Lock:** Thread-safe command transmission via `threading.Lock()`
- **Buffer Management:** Input/output buffers flushed before commands (`ser.reset_input_buffer()`)
- **Error Recovery:** Automatic reconnection on serial errors (`_attempt_reopen()`)

#### Thread-Safe Message Queue
```python
# M0Device.message_queue (queue.Queue)
message_queue.put((device_id, message_text))  # Producer: read_loop thread
message_queue.get()  # Consumer: main thread (if needed)

# Touch detection via polling:
if m0.is_touched():  # Set by read_loop when TOUCH received
    # Handle touch event
```

### 2. GPIO Communication (pigpio)

#### pigpio Daemon
- **Service:** `pigpiod` (must be running before Python script)
- **Socket:** Communicates via local socket (not direct hardware access)
- **Library:** `import pigpio; pi = pigpio.pi()`

#### GPIO Modes
```python
pi.set_mode(pin, pigpio.OUTPUT)   # Configure as output
pi.set_mode(pin, pigpio.INPUT)    # Configure as input
```

#### Digital I/O
```python
# Output (e.g., basic on/off):
pi.write(pin, 1)  # HIGH
pi.write(pin, 0)  # LOW

# Input (e.g., beam break):
state = pi.read(pin)  # Returns 0 or 1
pi.set_pull_up_down(pin, pigpio.PUD_UP)  # Enable pull-up resistor
```

#### PWM Control
```python
# Configuration:
pi.set_PWM_frequency(pin, 5000)    # Set PWM frequency (Hz)
pi.set_PWM_range(pin, 255)         # Set range (0-255 for 8-bit)

# Control:
pi.set_PWM_dutycycle(pin, 140)     # Set duty cycle (brightness/speed)
pi.set_PWM_dutycycle(pin, 0)       # Turn off
```

**PWM Use Cases:**
- **LEDs:** Brightness control (0-255 duty cycle)
- **Reward Pump:** Speed control (typically 0 or 255 for on/off)
- **Buzzer:** Tone generation (frequency set separately)

#### Beam Break Monitoring
```python
# BeamBreak class implements state monitoring:
class BeamBreak:
    def _read_loop(self):
        reading = self.pi.read(self.pin)
        if reading == 0:  # Beam broken (active low)
            self.last_break_time = time.time()
            self.state = 0
        elif time.time() - self.last_break_time > self.beam_break_memory:
            self.state = 1  # Beam restored after memory period

# Memory: 200ms (default) - prevents bouncing
```

### 3. Camera Streaming and Recording

#### Video Streaming (ustreamer)
```bash
# Command executed by Camera class:
ustreamer --device=/dev/video0 \
          --host=<local_ip> \
          --port=8080 \
          --sink=demo::ustreamer::sink \
          --sink-mode=660 \
          --sink-rm

# Access stream via:
http://<raspberry_pi_ip>:8080/
```

**Features:**
- **Low Latency:** Optimized for real-time viewing
- **Format:** MJPEG over HTTP
- **Shared Memory Sink:** Allows concurrent recording while streaming

#### Video Recording (ffmpeg)
```bash
# Command executed by Camera.start_recording():
ustreamer-dump --sink=demo::ustreamer::sink --output - | \
ffmpeg -use_wallclock_as_timestamps 1 -i pipe: -c:v libx264 <output.mp4>

# Output file naming:
# Format: YYYYMMDD_HHMMSS_ChamberName_RodentName.mp4
# Example: 20250203_123045_Chamber0_Rat01.mp4
```

**Recording Management:**
- **Start:** `camera.start_recording(output_file)`
- **Stop:** `camera.stop_recording()` (sends SIGTERM to process group)
- **Concurrent:** Streaming continues during recording

## Hardware Setup and Initialization

### System Startup Sequence

```
1. Power on Raspberry Pi
2. Boot Raspberry Pi OS
3. Start pigpiod daemon (GPIO access)
4. Connect M0 devices via USB
5. Run Python controller script
   ├── Initialize pigpio connection
   ├── Discover M0 boards (arduino-cli)
   ├── Assign serial ports to M0Device instances
   ├── Open serial connections
   ├── Start read threads for each M0
   ├── Initialize GPIO peripherals (LEDs, pump, beam break, buzzer)
   ├── Start camera streaming
   └── Ready for training session
```

### M0 Device Initialization

```python
# From Chamber.__init__():
1. Create M0Device instances with reset pins
2. Run arduino-cli board discovery:
   - Scans USB devices for VID:0x2341, PID:0x0244
   - Returns JSON with port addresses
3. Assign ports to M0s (order: left, middle, right)
4. For each M0:
   - Open serial port (115200 baud)
   - Start background read thread
   - Send "WHOAREYOU?" to verify communication
```

### GPIO Peripheral Initialization

```python
# From Chamber.__init__():
for each peripheral (LED, Reward, BeamBreak, Buzzer):
    - Set GPIO mode (OUTPUT or INPUT)
    - Configure PWM (if applicable)
    - Set initial state (LEDs off, pump off, etc.)
    - Enable pull-up resistors (for inputs)
```

### Camera Initialization

```python
# From Camera.__init__():
1. Kill existing ustreamer/ffmpeg processes
2. Get local IP address
3. Start ustreamer process in background
4. Log stream URL: http://<ip>:8080/
```

## Physical Connections

### M0 Touchscreen Connections
```
[Raspberry Pi USB Ports]
├── USB 1 → M0 Left (ID: M0_0, Reset: GPIO 25)
├── USB 2 → M0 Middle (ID: M0_1, Reset: GPIO 5)
└── USB 3 → M0 Right (ID: M0_2, Reset: GPIO 6)

Each M0 board:
├── Power: 5V via USB
├── Data: USB CDC serial
├── Reset: GPIO wire from Pi to M0 reset pin
└── Display: SPI touchscreen connected to M0
```

### GPIO Peripheral Connections
```
[Raspberry Pi GPIO Header]
├── Pin 4 (GPIO 4) → Beam Break Sensor (IR receiver, active low)
├── Pin 16 (GPIO 16) → Buzzer positive terminal
├── Pin 17 (GPIO 17) → Punishment LED anode (via resistor)
├── Pin 20 (GPIO 20) → House LED anode (via resistor)
├── Pin 21 (GPIO 21) → Reward LED anode (via resistor)
├── Pin 25 (GPIO 25) → M0 Left reset pin
├── Pin 5 (GPIO 5) → M0 Middle reset pin
├── Pin 6 (GPIO 6) → M0 Right reset pin
└── Pin 27 (GPIO 27) → Reward Pump control (via MOSFET/relay)

Common Ground:
└── GND → All LED cathodes, buzzer negative, sensor ground, pump ground
```

### Camera Connection
```
[USB Port] → [USB Webcam]
└── Device appears as: /dev/video0

Streaming accessible at:
http://<raspberry_pi_ip>:8080/
```

## Firmware (M0 Boards)

### Arduino Sketch
- **Location:** `../M0Touch/M0Touch.ino`
- **Board:** DFRobot SAMD21 M0 (FQBN: `DFRobot:samd:mzero_bl`)
- **Compiler:** arduino-cli

### Compilation and Upload
```bash
# Compile sketch:
~/bin/arduino-cli compile -b DFRobot:samd:mzero_bl ../M0Touch/M0Touch.ino

# Upload to M0 (requires port discovery first):
~/bin/arduino-cli upload --port /dev/ttyACM0 \
                         --fqbn DFRobot:samd:mzero_bl \
                         ../M0Touch/M0Touch.ino
```

### Image Synchronization
M0 boards store images on an internal SD card. To update images:

```python
# From M0Device.sync_image_folder():
1. Double-reset M0 to enter USB mass storage mode (UD mode)
2. Wait for /dev/sd* device to appear
3. Mount device (appears in /media)
4. rsync images from ../data/images/ to mounted drive
5. Unmount and reset M0 to return to serial mode
```

## Power Requirements

### Estimated Power Draw
| Component | Voltage | Current (typical) | Notes |
|-----------|---------|-------------------|-------|
| Raspberry Pi 5 | 5V | 1-2A | Base consumption |
| M0 Board (each) | 5V | ~200mA | 3 boards = ~600mA |
| LEDs (all on) | 3.3V/5V | ~100mA | PWM-controlled |
| Reward Pump | 12V* | ~500mA | May require separate supply |
| USB Camera | 5V | ~150mA | USB-powered |
| **Total (5V)** | **5V** | **~3A** | Minimum recommendation |

*Note: Reward pump voltage/current depends on specific model; may require external power supply with MOSFET/relay control from GPIO.

### Power Supply Recommendations
- **Raspberry Pi:** Official 5V 3A USB-C power supply
- **Peripherals:** If total draw exceeds 3A, use external 5V supply with common ground
- **Pump:** If 12V pump, use separate 12V supply with MOSFET/relay control

## Troubleshooting

### M0 Device Not Detected
1. Check USB cable connection
2. Run discovery: `~/bin/arduino-cli board list --format json`
3. Verify VID:PID (should be 0x2341:0x0244)
4. Try hardware reset via GPIO pin
5. Check dmesg for USB errors: `dmesg | tail`

### Serial Communication Errors
1. Check port permissions: `ls -l /dev/ttyACM*` (should be readable/writable)
2. Verify baud rate: 115200
3. Test with: `screen /dev/ttyACM0 115200` (type "WHOAREYOU?" and check response)
4. Check for other processes using port: `lsof /dev/ttyACM0`

### GPIO Not Responding
1. Verify pigpiod is running: `sudo systemctl status pigpiod`
2. Start if needed: `sudo systemctl start pigpiod`
3. Check pigpio connection: `python3 -c "import pigpio; pi = pigpio.pi(); print(pi.connected)"`
4. Test pin with: `pigs modes <pin> w; pigs w <pin> 1` (command-line GPIO control)

### Camera Issues
1. Check device exists: `ls /dev/video*`
2. Test with: `v4l2-ctl --list-devices`
3. Kill existing processes: `pkill ustreamer; pkill ffmpeg`
4. Check camera stream: `curl http://localhost:8080/` (should return HTTP headers)

## Hardware Modifications

### Changing Pin Assignments

**Recommended Method (New Config System):**

Edit `~/chamber_config.yaml`:
```yaml
gpio_pins:
  reward_led_pin: 22  # Changed from default 21
  punishment_led_pin: 18
  # ... other pins
```

Or in Python:
```python
from config import get_default_config, GPIOPinConfig

hw_config = get_default_config()
hw_config.gpio_pins.reward_led_pin = 22
chamber = Chamber(hw_config=hw_config)
```

**Legacy Method (Still Supported):**

Edit `Chamber.py`:
```python
self.config.ensure_param("reward_LED_pin", 22)  # Changed default
```

Or override via legacy YAML:
```yaml
reward_LED_pin: 22
```

See [CONFIG.md](CONFIG.md) for complete configuration documentation.

### Adding New Peripherals
1. Create new class (e.g., `NewPeripheral.py`) inheriting from base pattern
2. Initialize in `Chamber.__init__()`:
   ```python
   self.new_peripheral = NewPeripheral(pi=self.pi, pin=<pin>)
   ```
3. Control in trainer: `self.chamber.new_peripheral.activate()`

### Supporting Additional M0 Devices
1. Add reset pin to `reset_pins` list in config
2. Create new M0Device instance in `Chamber.__init__()`
3. Add to `self.m0s` list for batch operations
4. Update discovery logic to handle >3 devices
