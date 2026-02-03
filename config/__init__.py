"""
NC4touch Configuration Package

Centralized configuration management for hardware pins, communication settings,
and device parameters.
"""

from .hardware_config import (
    HardwareConfig,
    GPIOPinConfig,
    M0SerialConfig,
    M0I2CConfig,
    CameraConfig,
    DirectoryConfig,
    PWMConfig,
    get_default_config,
)

__all__ = [
    'HardwareConfig',
    'GPIOPinConfig',
    'M0SerialConfig',
    'M0I2CConfig',
    'CameraConfig',
    'DirectoryConfig',
    'PWMConfig',
    'get_default_config',
]
