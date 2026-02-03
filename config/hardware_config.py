"""
NC4touch Hardware Configuration

Centralized configuration system for all hardware parameters using Python dataclasses.
This module provides type-safe configuration with sensible defaults that can be
overridden via constructor parameters or YAML files.

Author: OpenClaw Subagent
Date: 2026-02-03
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
import os


@dataclass
class GPIOPinConfig:
    """GPIO pin assignments for peripherals."""
    
    # LED pins (PWM-enabled)
    reward_led_pin: int = 21
    punishment_led_pin: int = 17
    house_led_pin: int = 20
    
    # Reward system
    reward_pump_pin: int = 27
    beambreak_pin: int = 4
    
    # Auditory
    buzzer_pin: int = 16
    
    # M0 reset pins (left, middle, right)
    m0_reset_pins: List[int] = field(default_factory=lambda: [25, 5, 6])
    
    def __post_init__(self):
        """Validate pin assignments."""
        all_pins = [
            self.reward_led_pin,
            self.punishment_led_pin,
            self.house_led_pin,
            self.reward_pump_pin,
            self.beambreak_pin,
            self.buzzer_pin,
        ] + self.m0_reset_pins
        
        # Check for duplicate pin assignments
        if len(all_pins) != len(set(all_pins)):
            raise ValueError("Duplicate GPIO pin assignments detected")


@dataclass
class PWMConfig:
    """PWM configuration for LEDs and pumps."""
    
    # PWM frequency (Hz)
    frequency: int = 5000
    
    # PWM range (0-255 for 8-bit resolution)
    range: int = 255
    
    # LED brightness defaults (0-255)
    reward_led_brightness: int = 140
    punishment_led_brightness: int = 255
    house_led_brightness: int = 100
    
    # Pump PWM duty cycle (typically 0 or 255)
    pump_duty_cycle: int = 255


@dataclass
class M0SerialConfig:
    """Serial communication configuration for M0 devices."""
    
    # Serial port settings
    baudrate: int = 115200
    timeout: float = 5.0  # seconds
    
    # Device identification
    vendor_id: str = "0x2341"
    product_id: str = "0x0244"
    
    # Retry and timing
    max_retries: int = 3
    retry_backoff_base: float = 0.1  # seconds
    read_loop_interval: float = 0.1  # seconds
    
    # Reset timing
    reset_pulse_duration: float = 0.01  # seconds
    reset_recovery_time: float = 0.5  # seconds
    
    # Discovery settings
    discovery_wait_time: float = 3.0  # seconds after reset
    
    # Buffer management
    flush_on_send: bool = True


@dataclass
class M0I2CConfig:
    """I2C communication configuration for M0 devices."""
    
    # I2C bus settings
    bus_number: int = 1  # Raspberry Pi I2C bus 1
    
    # Device addresses (0x00-0x07)
    addresses: List[int] = field(default_factory=lambda: [0x00, 0x01, 0x02])
    
    # Communication timing
    timeout: float = 2.0  # seconds
    poll_interval: float = 0.1  # seconds for touch polling
    
    # Retry settings
    max_retries: int = 3
    retry_backoff_base: float = 0.1  # seconds
    
    # Reset timing (same as serial for consistency)
    reset_pulse_duration: float = 0.01  # seconds
    reset_recovery_time: float = 0.5  # seconds
    
    def __post_init__(self):
        """Validate I2C addresses."""
        for addr in self.addresses:
            if not (0x00 <= addr <= 0x07):
                raise ValueError(f"I2C address {addr:#04x} out of valid range 0x00-0x07")


@dataclass
class CameraConfig:
    """Camera and video recording configuration."""
    
    # Device path
    device_path: str = "/dev/video0"
    
    # Streaming settings
    stream_port: int = 8080
    stream_format: str = "MJPEG"
    
    # Recording settings
    video_codec: str = "libx264"
    
    # Process management
    kill_existing_on_start: bool = True


@dataclass
class DirectoryConfig:
    """Directory paths for data storage."""
    
    # Base directories
    code_dir: str = field(default_factory=lambda: os.path.dirname(os.path.abspath(__file__)))
    data_dir: str = "/mnt/shared/data"
    
    # Subdirectories
    video_dir: Optional[str] = None  # If None, uses data_dir
    image_dir: str = field(default_factory=lambda: "../data/images")
    log_dir: Optional[str] = None  # If None, uses data_dir
    
    # M0 sketch paths
    m0_sketch_dir: str = field(default_factory=lambda: "../M0Touch")
    m0_sketch_i2c_dir: str = field(default_factory=lambda: "../M0Touch_I2C")
    
    def get_video_dir(self) -> str:
        """Get video directory, falling back to data_dir."""
        return self.video_dir or self.data_dir
    
    def get_log_dir(self) -> str:
        """Get log directory, falling back to data_dir."""
        return self.log_dir or self.data_dir
    
    def get_m0_sketch_path(self, use_i2c: bool = False) -> str:
        """Get path to M0 sketch file."""
        sketch_dir = self.m0_sketch_i2c_dir if use_i2c else self.m0_sketch_dir
        return os.path.join(sketch_dir, f"{os.path.basename(sketch_dir)}.ino")


@dataclass
class BeamBreakConfig:
    """Beam break sensor configuration."""
    
    # Memory duration (seconds) - prevents bouncing
    memory_duration: float = 0.2
    
    # Read interval (seconds)
    read_interval: float = 0.05


@dataclass
class HardwareConfig:
    """
    Complete hardware configuration for NC4touch system.
    
    This dataclass aggregates all hardware-related configuration settings.
    Can be initialized with default values or customized via constructor.
    
    Example:
        # Use defaults
        config = HardwareConfig()
        
        # Override specific values
        config = HardwareConfig(
            gpio_pins=GPIOPinConfig(reward_led_pin=22),
            use_i2c=True
        )
        
        # Create from dict
        config = HardwareConfig.from_dict(config_dict)
    """
    
    # Component configurations
    gpio_pins: GPIOPinConfig = field(default_factory=GPIOPinConfig)
    pwm: PWMConfig = field(default_factory=PWMConfig)
    m0_serial: M0SerialConfig = field(default_factory=M0SerialConfig)
    m0_i2c: M0I2CConfig = field(default_factory=M0I2CConfig)
    camera: CameraConfig = field(default_factory=CameraConfig)
    directories: DirectoryConfig = field(default_factory=DirectoryConfig)
    beambreak: BeamBreakConfig = field(default_factory=BeamBreakConfig)
    
    # Chamber settings
    chamber_name: str = "Chamber0"
    use_i2c: bool = False  # Use I2C instead of serial for M0s
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'HardwareConfig':
        """
        Create HardwareConfig from dictionary.
        
        Args:
            config_dict: Dictionary with configuration values
            
        Returns:
            HardwareConfig instance
        """
        # Extract nested configs
        gpio_pins = GPIOPinConfig(**config_dict.get('gpio_pins', {}))
        pwm = PWMConfig(**config_dict.get('pwm', {}))
        m0_serial = M0SerialConfig(**config_dict.get('m0_serial', {}))
        m0_i2c = M0I2CConfig(**config_dict.get('m0_i2c', {}))
        camera = CameraConfig(**config_dict.get('camera', {}))
        directories = DirectoryConfig(**config_dict.get('directories', {}))
        beambreak = BeamBreakConfig(**config_dict.get('beambreak', {}))
        
        # Top-level settings
        chamber_name = config_dict.get('chamber_name', 'Chamber0')
        use_i2c = config_dict.get('use_i2c', False)
        
        return cls(
            gpio_pins=gpio_pins,
            pwm=pwm,
            m0_serial=m0_serial,
            m0_i2c=m0_i2c,
            camera=camera,
            directories=directories,
            beambreak=beambreak,
            chamber_name=chamber_name,
            use_i2c=use_i2c,
        )
    
    def merge_with_legacy_config(self, legacy_config: Dict[str, Any]) -> None:
        """
        Merge with legacy Config dict for backward compatibility.
        
        Maps old flat config keys to new structured config.
        
        Args:
            legacy_config: Dictionary from old Config class
        """
        # Map legacy keys to new structure
        if 'reward_LED_pin' in legacy_config:
            self.gpio_pins.reward_led_pin = legacy_config['reward_LED_pin']
        if 'punishment_LED_pin' in legacy_config:
            self.gpio_pins.punishment_led_pin = legacy_config['punishment_LED_pin']
        if 'house_LED_pin' in legacy_config:
            self.gpio_pins.house_led_pin = legacy_config['house_LED_pin']
        if 'reward_pump_pin' in legacy_config:
            self.gpio_pins.reward_pump_pin = legacy_config['reward_pump_pin']
        if 'beambreak_pin' in legacy_config:
            self.gpio_pins.beambreak_pin = legacy_config['beambreak_pin']
        if 'buzzer_pin' in legacy_config:
            self.gpio_pins.buzzer_pin = legacy_config['buzzer_pin']
        if 'reset_pins' in legacy_config:
            self.gpio_pins.m0_reset_pins = legacy_config['reset_pins']
        
        if 'camera_device' in legacy_config:
            self.camera.device_path = legacy_config['camera_device']
        
        if 'use_i2c' in legacy_config:
            self.use_i2c = legacy_config['use_i2c']
        if 'i2c_addresses' in legacy_config:
            self.m0_i2c.addresses = legacy_config['i2c_addresses']
        
        if 'chamber_name' in legacy_config:
            self.chamber_name = legacy_config['chamber_name']


def get_default_config() -> HardwareConfig:
    """
    Get default hardware configuration.
    
    Returns:
        HardwareConfig with all default values
    """
    return HardwareConfig()


def load_config_from_yaml(yaml_path: str) -> HardwareConfig:
    """
    Load hardware configuration from YAML file.
    
    Args:
        yaml_path: Path to YAML configuration file
        
    Returns:
        HardwareConfig instance
    """
    import yaml
    from os.path import expanduser
    
    yaml_path = expanduser(yaml_path)
    
    if not os.path.isfile(yaml_path):
        raise FileNotFoundError(f"Config file not found: {yaml_path}")
    
    with open(yaml_path, 'r') as f:
        config_dict = yaml.safe_load(f)
    
    return HardwareConfig.from_dict(config_dict)


def save_config_to_yaml(config: HardwareConfig, yaml_path: str) -> None:
    """
    Save hardware configuration to YAML file.
    
    Args:
        config: HardwareConfig instance
        yaml_path: Path to save YAML file
    """
    import yaml
    from os.path import expanduser
    
    yaml_path = expanduser(yaml_path)
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(yaml_path), exist_ok=True)
    
    with open(yaml_path, 'w') as f:
        yaml.dump(config.to_dict(), f, default_flow_style=False)


if __name__ == "__main__":
    # Example usage
    config = get_default_config()
    print("Default configuration:")
    print(f"  Reward LED pin: {config.gpio_pins.reward_led_pin}")
    print(f"  M0 baudrate: {config.m0_serial.baudrate}")
    print(f"  I2C bus: {config.m0_i2c.bus_number}")
    print(f"  Camera device: {config.camera.device_path}")
    print(f"  Data directory: {config.directories.data_dir}")
