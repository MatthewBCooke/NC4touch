#!/usr/bin/env python3
"""
Test script to verify refactored configuration system.

Tests:
1. Configuration creation and defaults
2. YAML serialization/deserialization
3. Legacy config compatibility
4. Component initialization with new config

Author: OpenClaw Subagent
Date: 2026-02-03
"""

import sys
import os
import tempfile

# Add Controller directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../Controller'))

from config import (
    HardwareConfig,
    GPIOPinConfig,
    PWMConfig,
    M0SerialConfig,
    M0I2CConfig,
    get_default_config,
    save_config_to_yaml,
    load_config_from_yaml,
)


def test_default_config():
    """Test default configuration creation."""
    print("Test 1: Default configuration...")
    
    config = get_default_config()
    
    assert config.chamber_name == "Chamber0"
    assert config.use_i2c == False
    assert config.gpio_pins.reward_led_pin == 21
    assert config.m0_serial.baudrate == 115200
    assert config.m0_i2c.bus_number == 1
    
    print("  ✓ Default config created successfully")
    print(f"  ✓ GPIO pins: {config.gpio_pins.m0_reset_pins}")
    print(f"  ✓ PWM frequency: {config.pwm.frequency} Hz")
    return True


def test_custom_config():
    """Test custom configuration values."""
    print("\nTest 2: Custom configuration...")
    
    config = HardwareConfig(
        chamber_name="TestChamber",
        use_i2c=True,
        gpio_pins=GPIOPinConfig(
            reward_led_pin=22,
            m0_reset_pins=[10, 11, 12]
        ),
        pwm=PWMConfig(frequency=10000)
    )
    
    assert config.chamber_name == "TestChamber"
    assert config.use_i2c == True
    assert config.gpio_pins.reward_led_pin == 22
    assert config.gpio_pins.m0_reset_pins == [10, 11, 12]
    assert config.pwm.frequency == 10000
    
    print("  ✓ Custom values applied correctly")
    return True


def test_yaml_serialization():
    """Test YAML save/load."""
    print("\nTest 3: YAML serialization...")
    
    # Create config
    original = HardwareConfig(
        chamber_name="YAMLTest",
        gpio_pins=GPIOPinConfig(reward_led_pin=23)
    )
    
    # Save to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        temp_path = f.name
    
    try:
        save_config_to_yaml(original, temp_path)
        print(f"  ✓ Saved to {temp_path}")
        
        # Load back
        loaded = load_config_from_yaml(temp_path)
        
        assert loaded.chamber_name == "YAMLTest"
        assert loaded.gpio_pins.reward_led_pin == 23
        
        print("  ✓ Loaded config matches original")
        return True
        
    finally:
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_legacy_config_compatibility():
    """Test backward compatibility with legacy Config dict."""
    print("\nTest 4: Legacy config compatibility...")
    
    # Create config with new system
    config = get_default_config()
    
    # Simulate legacy config dict
    legacy_dict = {
        'reward_LED_pin': 24,
        'punishment_LED_pin': 18,
        'use_i2c': True,
        'i2c_addresses': [0x04, 0x05, 0x06],
        'chamber_name': 'LegacyChamber',
    }
    
    # Merge legacy values
    config.merge_with_legacy_config(legacy_dict)
    
    assert config.gpio_pins.reward_led_pin == 24
    assert config.gpio_pins.punishment_led_pin == 18
    assert config.use_i2c == True
    assert config.m0_i2c.addresses == [0x04, 0x05, 0x06]
    assert config.chamber_name == 'LegacyChamber'
    
    print("  ✓ Legacy config merged successfully")
    return True


def test_validation():
    """Test configuration validation."""
    print("\nTest 5: Configuration validation...")
    
    # Test duplicate pin detection
    try:
        bad_config = GPIOPinConfig(
            reward_led_pin=21,
            punishment_led_pin=21,  # Duplicate!
        )
        print("  ✗ Failed to detect duplicate pins")
        return False
    except ValueError as e:
        print(f"  ✓ Duplicate pin detected: {e}")
    
    # Test invalid I2C address
    try:
        bad_i2c = M0I2CConfig(addresses=[0x00, 0x09])  # 0x09 out of range
        print("  ✗ Failed to detect invalid I2C address")
        return False
    except ValueError as e:
        print(f"  ✓ Invalid I2C address detected: {e}")
    
    return True


def test_config_to_dict():
    """Test dictionary conversion."""
    print("\nTest 6: Dictionary conversion...")
    
    config = HardwareConfig(chamber_name="DictTest")
    config_dict = config.to_dict()
    
    assert isinstance(config_dict, dict)
    assert config_dict['chamber_name'] == "DictTest"
    assert 'gpio_pins' in config_dict
    assert 'pwm' in config_dict
    
    print("  ✓ Config converted to dict")
    print(f"  ✓ Dict keys: {list(config_dict.keys())}")
    return True


def test_from_dict():
    """Test creating config from dictionary."""
    print("\nTest 7: Creating config from dict...")
    
    config_dict = {
        'chamber_name': 'FromDict',
        'use_i2c': True,
        'gpio_pins': {
            'reward_led_pin': 21,  # Keep default to avoid duplicate
            'buzzer_pin': 16,  # Keep default
            'm0_reset_pins': [25, 5, 6],  # Keep defaults
        },
        'pwm': {
            'frequency': 8000,
        }
    }
    
    config = HardwareConfig.from_dict(config_dict)
    
    assert config.chamber_name == 'FromDict'
    assert config.use_i2c == True
    assert config.gpio_pins.reward_led_pin == 21
    assert config.gpio_pins.buzzer_pin == 16
    assert config.pwm.frequency == 8000
    
    # Check that defaults are still applied for missing values
    assert config.gpio_pins.punishment_led_pin == 17  # Default
    assert config.pwm.range == 255  # Default
    
    print("  ✓ Config created from dict")
    print("  ✓ Defaults applied for missing values")
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("NC4touch Configuration System Tests")
    print("=" * 60)
    
    tests = [
        test_default_config,
        test_custom_config,
        test_yaml_serialization,
        test_legacy_config_compatibility,
        test_validation,
        test_config_to_dict,
        test_from_dict,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
                print(f"  ✗ Test failed: {test.__name__}")
        except Exception as e:
            failed += 1
            print(f"  ✗ Test error: {test.__name__}")
            print(f"     {type(e).__name__}: {e}")
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
