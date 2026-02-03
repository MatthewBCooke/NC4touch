#!/usr/bin/env python3
"""
Test I2C discovery and Chamber initialization with I2C mode.

This script tests the I2C implementation without requiring actual hardware
by using mock I2C devices.

Author: OpenClaw Subagent
Date: 2026-02-03
"""

import sys
import os
from unittest.mock import MagicMock, patch

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Controller'))

from M0DeviceI2C import discover_i2c_devices, I2CCommand


def test_discovery_mock():
    """Test I2C discovery with mock devices."""
    print("=" * 60)
    print("Testing I2C Discovery (Mock)")
    print("=" * 60)
    
    # Mock smbus2 module first
    import M0DeviceI2C
    mock_smbus2 = MagicMock()
    M0DeviceI2C.smbus2 = mock_smbus2
    
    # Mock smbus2
    with patch.object(mock_smbus2, 'SMBus') as mock_bus_class:
        mock_bus = MagicMock()
        mock_bus_class.return_value = mock_bus
        
        # Simulate 3 M0 devices responding
        def mock_read_byte(addr):
            if addr in [0x01, 0x02, 0x03]:
                return 8  # Length of "ID:M0_X"
            else:
                raise IOError("No device at address")
        
        def mock_read_block(addr, reg, length):
            if addr == 0x01:
                return list(b"ID:M0_0\x00") + [0]
            elif addr == 0x02:
                return list(b"ID:M0_1\x00") + [0]
            elif addr == 0x03:
                return list(b"ID:M0_2\x00") + [0]
            else:
                raise IOError("No device at address")
        
        mock_bus.read_byte.side_effect = mock_read_byte
        mock_bus.read_i2c_block_data.side_effect = mock_read_block
        mock_bus.write_i2c_block_data.return_value = None
        
        # Run discovery
        devices = discover_i2c_devices(bus_num=1, address_range=range(0x00, 0x08))
        
        print(f"\nFound {len(devices)} devices:")
        for addr, device_id in devices:
            print(f"  {addr:#04x}: {device_id}")
        
        # Verify results
        assert len(devices) == 3, f"Expected 3 devices, found {len(devices)}"
        
        device_ids = [dev_id for addr, dev_id in devices]
        assert "M0_0" in device_ids, "M0_0 not found"
        assert "M0_1" in device_ids, "M0_1 not found"
        assert "M0_2" in device_ids, "M0_2 not found"
        
        print("\n✓ I2C discovery test passed")
        return True


def test_chamber_i2c_mock():
    """Test Chamber initialization with I2C mode (mock)."""
    print("\n" + "=" * 60)
    print("Testing Chamber I2C Initialization (Mock)")
    print("=" * 60)
    
    # Mock module dependencies
    import M0DeviceI2C
    import Chamber
    mock_smbus2 = MagicMock()
    mock_pigpio = MagicMock()
    M0DeviceI2C.smbus2 = mock_smbus2
    M0DeviceI2C.pigpio = mock_pigpio
    Chamber.pigpio = mock_pigpio
    
    # Mock all dependencies
    with patch.object(mock_smbus2, 'SMBus'), \
         patch.object(mock_pigpio, 'pi') as mock_pi_class, \
         patch('Chamber.LED'), \
         patch('Chamber.Reward'), \
         patch('Chamber.BeamBreak'), \
         patch('Chamber.Buzzer'), \
         patch('Chamber.Camera'):
        
        # Mock pigpio
        mock_pi = MagicMock()
        mock_pi_class.return_value = mock_pi
        
        # Mock I2C discovery
        with patch('Chamber.discover_i2c_devices') as mock_discover:
            mock_discover.return_value = [
                (0x01, "M0_0"),
                (0x02, "M0_1"),
                (0x03, "M0_2")
            ]
            
            # Import Chamber after mocking
            from Chamber import Chamber
            
            # Create chamber with I2C mode
            chamber = Chamber(chamber_config={"use_i2c": True})
            
            print(f"\n✓ Chamber initialized with {len(chamber.m0s)} M0 devices")
            
            # Verify M0s were created
            assert len(chamber.m0s) == 3, f"Expected 3 M0s, got {len(chamber.m0s)}"
            
            for m0 in chamber.m0s:
                print(f"  - {m0.id} at I2C address {m0.address:#04x}")
            
            # Verify device IDs
            ids = [m0.id for m0 in chamber.m0s]
            assert "M0_0" in ids, "M0_0 not initialized"
            assert "M0_1" in ids, "M0_1 not initialized"
            assert "M0_2" in ids, "M0_2 not initialized"
            
            print("\n✓ Chamber I2C initialization test passed")
            return True


def test_command_sending_mock():
    """Test sending commands via I2C (mock)."""
    print("\n" + "=" * 60)
    print("Testing I2C Command Sending (Mock)")
    print("=" * 60)
    
    # Mock module dependencies
    import M0DeviceI2C
    mock_smbus2 = MagicMock()
    mock_pigpio = MagicMock()
    M0DeviceI2C.smbus2 = mock_smbus2
    M0DeviceI2C.pigpio = mock_pigpio
    
    with patch.object(mock_pigpio, 'pi'), \
         patch.object(mock_smbus2, 'SMBus') as mock_bus_class:
        
        from M0DeviceI2C import M0DeviceI2C
        
        # Create mock bus
        mock_bus = MagicMock()
        mock_bus_class.return_value = mock_bus
        
        # Mock responses
        mock_bus.read_byte.return_value = 1
        mock_bus.read_i2c_block_data.return_value = [I2CCommand.ACK.value, 0x06]
        
        # Create device
        mock_pi = MagicMock()
        m0 = M0DeviceI2C(
            pi=mock_pi,
            id="M0_0",
            address=0x01,
            reset_pin=25
        )
        
        # Initialize
        m0.bus = mock_bus
        m0.mode = m0.mode.COMMUNICATION
        
        # Test commands
        commands = ["SHOW", "BLACK", "IMG:A01"]
        
        for cmd in commands:
            result = m0.send_command(cmd)
            print(f"  Command '{cmd}': {'✓ Sent' if result else '✗ Failed'}")
            assert result, f"Command '{cmd}' failed"
        
        print("\n✓ Command sending test passed")
        return True


def test_touch_polling_mock():
    """Test touch event polling (mock)."""
    print("\n" + "=" * 60)
    print("Testing Touch Polling (Mock)")
    print("=" * 60)
    
    # Mock module dependencies
    import M0DeviceI2C
    mock_smbus2 = MagicMock()
    mock_pigpio = MagicMock()
    M0DeviceI2C.smbus2 = mock_smbus2
    M0DeviceI2C.pigpio = mock_pigpio
    
    with patch.object(mock_pigpio, 'pi'), \
         patch.object(mock_smbus2, 'SMBus') as mock_bus_class:
        
        from M0DeviceI2C import M0DeviceI2C
        
        # Create mock bus
        mock_bus = MagicMock()
        mock_bus_class.return_value = mock_bus
        
        # Mock touch response: [status=1, x_high, x_low, y_high, y_low]
        touch_x = 120
        touch_y = 80
        touch_data = [
            1,  # Touch detected
            (touch_x >> 8) & 0xFF,
            touch_x & 0xFF,
            (touch_y >> 8) & 0xFF,
            touch_y & 0xFF
        ]
        # Calculate correct checksum
        from M0DeviceI2C import M0DeviceI2C
        checksum = M0DeviceI2C._calculate_checksum(touch_data)
        touch_response = touch_data + [checksum]
        
        mock_bus.read_byte.return_value = 5
        mock_bus.read_i2c_block_data.return_value = touch_response
        
        # Create device
        mock_pi = MagicMock()
        m0 = M0DeviceI2C(
            pi=mock_pi,
            id="M0_0",
            address=0x01,
            reset_pin=25
        )
        
        m0.bus = mock_bus
        m0.mode = m0.mode.COMMUNICATION
        
        # Manually poll for touch (instead of using thread)
        with patch('time.sleep'):  # Speed up test
            response = m0._send_command_with_retry(I2CCommand.TOUCH_POLL, timeout=0.5)
        
        # Parse response
        if response and len(response) >= 5:
            status = response[0]
            x = (response[1] << 8) | response[2]
            y = (response[3] << 8) | response[4]
            
            print(f"\n  Touch detected: ({x}, {y})")
            
            assert status == 1, "Touch status should be 1"
            assert x == touch_x, f"X coordinate mismatch: expected {touch_x}, got {x}"
            assert y == touch_y, f"Y coordinate mismatch: expected {touch_y}, got {y}"
            
            print("✓ Touch polling test passed")
            return True
        else:
            print("✗ No touch response received")
            return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("NC4touch I2C Implementation Tests")
    print("=" * 60)
    print("\nRunning tests with mock I2C devices (no hardware required)...\n")
    
    tests = [
        ("I2C Discovery", test_discovery_mock),
        ("Chamber I2C Init", test_chamber_i2c_mock),
        ("Command Sending", test_command_sending_mock),
        ("Touch Polling", test_touch_polling_mock),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n✗ Test '{name}' failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(success for _, success in results)
    
    if all_passed:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
