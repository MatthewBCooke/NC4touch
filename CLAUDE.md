# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

NC4Touch is a Raspberry Pi 5–based system for running touchscreen behavioral experiments with rodents. It coordinates M0 microcontroller touchscreen displays, GPIO peripherals (LEDs, reward pump, IR beam break, buzzer), and a USB camera through configurable training protocols. The target deployment is Raspberry Pi OS (64-bit); development can happen on any platform using virtual mode.

## Build & Run Commands

**Package management uses `uv`** (not pip directly). The project is defined in `pyproject.toml` as `touchscreenapparatus`.

```bash
# Install dependencies
uv sync

# Run the WebUI (production, on Pi)
export UV_PROJECT_ENVIRONMENT=~/.nc4touch_uv_env
sudo pigpiod                          # required for GPIO access
uv run Controller/WebUI.py

# Or use the convenience script
bash scripts/start_webUI.sh
```

**Running tests** (tests are standalone scripts, not pytest):
```bash
# All config tests
uv run python tests/test_config.py

# Single test file
uv run python tests/test_i2c.py

# Tests that need Controller on sys.path add it themselves via:
#   sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../Controller'))
```

**No linter or formatter is currently configured.** Python >=3.11 is required.

## Architecture

### Core Hierarchy

```
Session  (top-level orchestrator)
├── Chamber / VirtualChamber  (hardware abstraction)
│   ├── 3× M0Device or M0DeviceI2C  (touchscreens)
│   ├── LED × 3  (reward, punishment, house)
│   ├── Reward  (pump)
│   ├── BeamBreak  (IR sensor)
│   ├── Buzzer
│   └── Camera  (ustreamer + ffmpeg)
└── Trainer subclass  (state-machine training protocol)
```

- **Session** (`Controller/Session.py`) — loads config, creates Chamber, dynamically imports the chosen Trainer via `importlib`, runs a 0.1s timer loop calling `Trainer.run_training()`.
- **Chamber** (`Controller/Chamber.py`) — initializes all hardware, discovers M0 boards, provides `default_state()` reset. Accepts either the new `HardwareConfig` dataclass or legacy dict config.
- **Trainer** (`Controller/Trainer.py`) — abstract base class. Each trainer is an enum-based state machine (e.g., `IDLE → START_TRAINING → START_TRIAL → WAIT_FOR_TOUCH → CORRECT → ITI → END_TRIAL`). Logs events as JSON lines to data files.

### Configuration System (dual)

- **New (recommended):** `config/hardware_config.py` — Python dataclasses (`HardwareConfig`, `GPIOPinConfig`, `PWMConfig`, `M0SerialConfig`, `M0I2CConfig`, etc.) with YAML serialization and validation. Use `from config import get_default_config`.
- **Legacy:** `Controller/Config.py` — dict-based with `ensure_param()` pattern and YAML persistence. Still used by `Session` and `Trainer` for session-level params; being gradually replaced.

When modifying hardware parameters, prefer the dataclass config. The Chamber constructor bridges both systems for backward compatibility.

### M0 Communication

Two paths exist for talking to M0 touchscreen boards:

- **Serial** (`Controller/M0Device.py`): USB CDC at 115200 baud, ASCII newline-terminated commands. Background `read_loop` thread queues incoming messages. Uses `arduino-cli` for device discovery.
- **I2C** (`Controller/M0DeviceI2C.py`): Binary frame protocol with XOR checksum. Touch events polled in background thread. Addresses 0x00–0x07, set by M0 GPIO pins.

Both expose the same interface: `send_command()`, `is_touched`, `message_queue`, `reset()`, `stop()`.

### Training Protocols

Each trainer in `Controller/` subclasses `Trainer` and implements `start_training()`, `run_training()`, `stop_training()`. The progression order is:

1. `Habituation` — free rewards, no touch required
2. `InitialTouch` — any touch gets reward
3. `MustTouch` — must touch correct stimulus
4. `Punish_Incorrect` — adds punishment for wrong touches
5. `Simple_Discrimination` — two-choice with correction trials
6. `Complex_Discrimination` — multi-stimulus discrimination
7. `PRL` — probabilistic reversal learning

`DoNothingTrainer` and `SoundTest` are for testing/debugging.

### Virtual Mode

Set `virtual_mode=True` in session config to run without hardware. `Controller/Virtual/` provides `VirtualChamber`, `VirtualM0Device`, etc. that mirror the real APIs. Useful for protocol development and testing.

### UI Layer

- **WebUI** (`Controller/WebUI.py`) — NiceGUI-based web interface (primary UI for production). Runs on port 8081, streams camera on 8080.
- **GUI** (`Controller/GUI.py`) — PyQt5 desktop GUI.
- **TUI** (`Controller/TUI.py`) — terminal interface.

`Controller/Main.py` contains legacy `MultiPhaseTraining` with hardcoded training phases (older approach, largely superseded by the Trainer subclass pattern).

### Logging

All modules use `logging.getLogger(f"session_logger.{__name__}")`. The root `session_logger` is configured in `Session.py` with console + file handlers. Training events are logged as JSON lines to data files via `Trainer.write_event()`.

## Key Directories

- `Controller/` — all Python source (not a package with proper imports; files import each other directly)
- `Controller/Virtual/` — virtual hardware implementations for testing
- `config/` — centralized hardware config package
- `tests/` — test scripts
- `scripts/` — shell scripts and example configs
- `M0Touch/` — Arduino serial firmware for M0 boards
- `M0Touch_I2C/` — Arduino I2C firmware for M0 boards
- `docs/` — architecture, hardware, config, and I2C documentation
- `archive/` — old driver code and debug notes (do not modify)
- `data/` — images and experimental data

## Important Patterns

- **GPIO requires `pigpiod`** daemon running (`sudo pigpiod`). All GPIO is done through the `pigpio` library's socket interface, not RPi.GPIO.
- **M0 device discovery** uses `arduino-cli board list --format json` to find USB serial ports by VID/PID.
- **Thread safety**: M0Device uses `write_lock` for serial writes and `queue.Queue` for message passing. M0DeviceI2C uses `threading.RLock()`.
- **Controller imports are path-based**, not package-based. Test files manually add `Controller/` to `sys.path`. The WebUI startup script sets the working directory to the repo root.
- **Data output**: JSON lines format, one event per line, with a header object containing session metadata.

## Hardware Quick Reference

| Component | GPIO Pin | Notes |
|-----------|----------|-------|
| Reward LED | 21 | PWM brightness 140/255 |
| Punishment LED | 17 | PWM brightness 255/255 |
| House LED | 20 | PWM brightness 100/255 |
| Reward Pump | 27 | PWM duty cycle 255 |
| Beam Break | 4 | Input with pull-up |
| Buzzer | 16 | PWM |
| M0 Reset Pins | 25, 5, 6 | Left, Middle, Right |
