"""
Unit tests for M0DeviceI2C - I2C communication with M0 touchscreen controllers

Tests protocol framing, checksums, retry logic, and error handling using mock I2C devices.

Author: OpenClaw Subagent
Date: 2026-02-03
"""

import unittest
from unittest.mock import MagicMock, patch, call
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Controller'))

from M0DeviceI2C import (
    M0DeviceI2C, 
    I2CCommand, 
    I2CError, 
    I2CTimeoutError, 
    I2CChecksumError,
    M0Mode
)


class TestChecksumCalculation(unittest.TestCase):
    """Test checksum calculation and validation."""
    
    def test_simple_checksum(self):
        """Test XOR checksum with simple data."""
        data = [0x01, 0x02]
        checksum = M0DeviceI2C._calculate_checksum(data)
        self.assertEqual(checksum, 0x03)
    
    def test_zero_checksum(self):
        """Test checksum of identical bytes cancels out."""
        data = [0x42, 0x42]
        checksum = M0DeviceI2C._calculate_checksum(data)
        self.assertEqual(checksum, 0x00)
    
    def test_complex_checksum(self):
        """Test checksum with realistic command data."""
        # WHOAREYOU command: [0x01]
        data = [0x01]
        checksum = M0DeviceI2C._calculate_checksum(data)
        self.assertEqual(checksum, 0x01)
        
        # IMG command with payload: [0x04, 'A', '0', '1']
        data = [0x04, ord('A'), ord('0'), ord('1')]
        checksum = M0DeviceI2C._calculate_checksum(data)
        expected = 0x04 ^ ord('A') ^ ord('0') ^ ord('1')
        self.assertEqual(checksum, expected)


class TestCommandFraming(unittest.TestCase):
    """Test I2C command frame construction."""
    
    def setUp(self):
        """Set up mock pigpio and smbus."""
        with patch('M0DeviceI2C.pigpio'), patch('M0DeviceI2C.smbus2'):
            self.mock_pi = MagicMock()
            self.mock_bus = MagicMock()
            
            self.device = M0DeviceI2C(
                pi=self.mock_pi,
                id="M0_0",
                address=0x01,
                reset_pin=25
            )
            self.device.bus = self.mock_bus
    
    def test_whoareyou_frame(self):
        """Test WHOAREYOU command frame construction."""
        # Mock response
        self.mock_bus.read_byte.return_value = 8
        response_data = list(b"ID:M0_0\x00") + [0]  # +checksum placeholder
        self.mock_bus.read_i2c_block_data.return_value = response_data
        
        # Send command
        try:
            self.device._send_command_raw(I2CCommand.WHOAREYOU, timeout=1.0)
        except:
            pass  # Ignore timeout for this test
        
        # Verify frame sent: [length=1, command=0x01, checksum]
        self.mock_bus.write_i2c_block_data.assert_called()
        args = self.mock_bus.write_i2c_block_data.call_args[0]
        
        address = args[0]
        register = args[1]
        data = args[2]
        
        self.assertEqual(address, 0x01)
        self.assertEqual(register, 0x01)  # Length byte
        self.assertIn(I2CCommand.WHOAREYOU.value, data)
    
    def test_img_frame_with_payload(self):
        """Test IMG command frame with image ID payload."""
        image_id = "A01"
        payload = image_id.encode('utf-8')
        
        # Mock response
        self.mock_bus.read_byte.return_value = 1
        self.mock_bus.read_i2c_block_data.return_value = [I2CCommand.ACK.value, 0]
        
        try:
            self.device._send_command_raw(I2CCommand.IMG, payload=payload, timeout=1.0)
        except:
            pass
        
        # Verify payload included in frame
        self.mock_bus.write_i2c_block_data.assert_called()
        args = self.mock_bus.write_i2c_block_data.call_args[0]
        data = args[2]
        
        # Data should contain: [command, 'A', '0', '1', checksum]
        self.assertIn(I2CCommand.IMG.value, data)
        self.assertIn(ord('A'), data)
        self.assertIn(ord('0'), data)
        self.assertIn(ord('1'), data)


class TestRetryLogic(unittest.TestCase):
    """Test automatic retry with exponential backoff."""
    
    def setUp(self):
        """Set up mock device."""
        with patch('M0DeviceI2C.pigpio'), patch('M0DeviceI2C.smbus2'):
            self.mock_pi = MagicMock()
            self.mock_bus = MagicMock()
            
            self.device = M0DeviceI2C(
                pi=self.mock_pi,
                id="M0_0",
                address=0x01,
                reset_pin=25
            )
            self.device.bus = self.mock_bus
    
    def test_retry_on_io_error(self):
        """Test retry when I2C write fails."""
        # First attempt fails, second succeeds
        self.mock_bus.write_i2c_block_data.side_effect = [IOError("Bus error"), None]
        
        # Mock successful response
        self.mock_bus.read_byte.return_value = 1
        self.mock_bus.read_i2c_block_data.return_value = [I2CCommand.ACK.value, 0x06]
        
        # Should retry and succeed
        with patch('time.sleep'):  # Speed up test
            result = self.device._send_command_with_retry(I2CCommand.SHOW)
        
        # Verify 2 attempts
        self.assertEqual(self.mock_bus.write_i2c_block_data.call_count, 2)
    
    def test_max_retries_exceeded(self):
        """Test that max retries raises error."""
        # All attempts fail
        self.mock_bus.write_i2c_block_data.side_effect = IOError("Bus error")
        
        # Should raise I2CError after 3 attempts
        with self.assertRaises(I2CError):
            with patch('time.sleep'):  # Speed up test
                self.device._send_command_with_retry(I2CCommand.SHOW)
        
        # Verify 3 attempts
        self.assertEqual(self.mock_bus.write_i2c_block_data.call_count, 3)
    
    def test_exponential_backoff(self):
        """Test that retry delays increase exponentially."""
        self.mock_bus.write_i2c_block_data.side_effect = [IOError(), IOError(), None]
        self.mock_bus.read_byte.return_value = 1
        self.mock_bus.read_i2c_block_data.return_value = [I2CCommand.ACK.value, 0x06]
        
        # Capture sleep calls
        with patch('time.sleep') as mock_sleep:
            self.device._send_command_with_retry(I2CCommand.SHOW)
            
            # Verify exponential backoff: 0.1s, 0.2s
            calls = [c[0][0] for c in mock_sleep.call_args_list if c[0][0] > 0.01]
            self.assertTrue(len(calls) >= 2)
            self.assertAlmostEqual(calls[0], 0.1, places=2)
            self.assertAlmostEqual(calls[1], 0.2, places=2)


class TestChecksumValidation(unittest.TestCase):
    """Test checksum validation on received data."""
    
    def setUp(self):
        """Set up mock device."""
        with patch('M0DeviceI2C.pigpio'), patch('M0DeviceI2C.smbus2'):
            self.mock_pi = MagicMock()
            self.mock_bus = MagicMock()
            
            self.device = M0DeviceI2C(
                pi=self.mock_pi,
                id="M0_0",
                address=0x01,
                reset_pin=25
            )
            self.device.bus = self.mock_bus
            self.device.mode = M0Mode.COMMUNICATION
    
    def test_valid_checksum_accepted(self):
        """Test that valid checksum is accepted."""
        # Prepare valid response: "ACK" with correct checksum
        response_data = [I2CCommand.ACK.value]
        checksum = M0DeviceI2C._calculate_checksum(response_data)
        
        self.mock_bus.read_byte.return_value = len(response_data)
        self.mock_bus.read_i2c_block_data.return_value = response_data + [checksum]
        
        # Should succeed without exception
        result = self.device._read_response(timeout=1.0)
        self.assertIsNotNone(result)
    
    def test_invalid_checksum_rejected(self):
        """Test that invalid checksum raises error."""
        # Prepare response with wrong checksum
        response_data = [I2CCommand.ACK.value]
        wrong_checksum = 0xFF
        
        self.mock_bus.read_byte.return_value = len(response_data)
        self.mock_bus.read_i2c_block_data.return_value = response_data + [wrong_checksum]
        
        # Should raise I2CChecksumError
        with self.assertRaises(I2CChecksumError):
            self.device._read_response(timeout=1.0)


class TestTimeout(unittest.TestCase):
    """Test timeout handling."""
    
    def setUp(self):
        """Set up mock device."""
        with patch('M0DeviceI2C.pigpio'), patch('M0DeviceI2C.smbus2'):
            self.mock_pi = MagicMock()
            self.mock_bus = MagicMock()
            
            self.device = M0DeviceI2C(
                pi=self.mock_pi,
                id="M0_0",
                address=0x01,
                reset_pin=25
            )
            self.device.bus = self.mock_bus
            self.device.mode = M0Mode.COMMUNICATION
    
    def test_timeout_on_no_response(self):
        """Test that timeout occurs when M0 doesn't respond."""
        # M0 never responds (length always 0)
        self.mock_bus.read_byte.return_value = 0
        
        # Should raise I2CTimeoutError
        with patch('time.sleep'):  # Speed up test
            with patch('time.time', side_effect=[0, 0.5, 1.0, 1.5, 2.0, 2.5]):
                with self.assertRaises(I2CTimeoutError):
                    self.device._read_response(timeout=2.0)


class TestHighLevelCommands(unittest.TestCase):
    """Test high-level command interface."""
    
    def setUp(self):
        """Set up mock device."""
        with patch('M0DeviceI2C.pigpio'), patch('M0DeviceI2C.smbus2'):
            self.mock_pi = MagicMock()
            self.mock_bus = MagicMock()
            
            self.device = M0DeviceI2C(
                pi=self.mock_pi,
                id="M0_0",
                address=0x01,
                reset_pin=25
            )
            self.device.bus = self.mock_bus
            self.device.mode = M0Mode.COMMUNICATION
            
            # Default mock response: ACK
            self.mock_bus.read_byte.return_value = 1
            self.mock_bus.read_i2c_block_data.return_value = [I2CCommand.ACK.value, 0x06]
    
    def test_show_command(self):
        """Test SHOW command."""
        result = self.device.send_command("SHOW")
        self.assertTrue(result)
        
        # Verify SHOW command sent
        self.mock_bus.write_i2c_block_data.assert_called()
    
    def test_black_command(self):
        """Test BLACK command."""
        result = self.device.send_command("BLACK")
        self.assertTrue(result)
    
    def test_img_command(self):
        """Test IMG command with image ID."""
        result = self.device.send_command("IMG:A01")
        self.assertTrue(result)
        
        # Verify payload contains "A01"
        args = self.mock_bus.write_i2c_block_data.call_args[0]
        data = args[2]
        
        # Should contain image ID characters
        self.assertIn(ord('A'), data)
        self.assertIn(ord('0'), data)
        self.assertIn(ord('1'), data)
    
    def test_unknown_command(self):
        """Test unknown command returns False."""
        result = self.device.send_command("INVALID")
        self.assertFalse(result)


class TestThreadSafety(unittest.TestCase):
    """Test thread-safe operations."""
    
    def setUp(self):
        """Set up mock device."""
        with patch('M0DeviceI2C.pigpio'), patch('M0DeviceI2C.smbus2'):
            self.mock_pi = MagicMock()
            self.mock_bus = MagicMock()
            
            self.device = M0DeviceI2C(
                pi=self.mock_pi,
                id="M0_0",
                address=0x01,
                reset_pin=25
            )
            self.device.bus = self.mock_bus
    
    def test_bus_lock_acquired(self):
        """Test that bus lock is acquired during operations."""
        self.mock_bus.read_byte.return_value = 1
        self.mock_bus.read_i2c_block_data.return_value = [I2CCommand.ACK.value, 0x06]
        
        # Mock lock to track acquire/release
        with patch.object(self.device.bus_lock, 'acquire', wraps=self.device.bus_lock.acquire) as mock_acquire:
            with patch.object(self.device.bus_lock, 'release', wraps=self.device.bus_lock.release) as mock_release:
                try:
                    self.device._send_command_raw(I2CCommand.SHOW, timeout=1.0)
                except:
                    pass
                
                # Verify lock was acquired and released
                self.assertTrue(mock_acquire.called)
                self.assertTrue(mock_release.called)


def run_tests():
    """Run all tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestChecksumCalculation))
    suite.addTests(loader.loadTestsFromTestCase(TestCommandFraming))
    suite.addTests(loader.loadTestsFromTestCase(TestRetryLogic))
    suite.addTests(loader.loadTestsFromTestCase(TestChecksumValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestTimeout))
    suite.addTests(loader.loadTestsFromTestCase(TestHighLevelCommands))
    suite.addTests(loader.loadTestsFromTestCase(TestThreadSafety))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
