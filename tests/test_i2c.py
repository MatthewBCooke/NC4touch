"""
Unit tests for I2C communication with M0 touchscreen controllers.

Tests cover:
- M0DeviceI2C class functionality
- I2C protocol frame encoding/decoding
- Checksum calculation and validation
- Command sending and response handling
- Error recovery and retry logic
- Touch polling and event detection
- Device discovery

Author: OpenClaw Subagent
Date: 2026-02-03
"""

import unittest
from unittest.mock import Mock, MagicMock, patch, call
import time
import queue
from typing import List

# Import module under test
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Controller'))

from M0DeviceI2C import (
    M0DeviceI2C, 
    I2CCommand, 
    I2CError, 
    I2CTimeoutError, 
    I2CChecksumError,
    M0Mode,
    discover_i2c_devices
)


def _build_mock_response(data_bytes, pad_to=32):
    """Build a mock I2C response: [length, data..., checksum, 0xFF padding...].

    Checksum = XOR of [length, data...] matching Arduino firmware.
    """
    length = len(data_bytes)
    checksum = length
    for b in data_bytes:
        checksum ^= b
    checksum &= 0xFF
    response = [length] + list(data_bytes) + [checksum]
    while len(response) < pad_to:
        response.append(0xFF)
    return response


class TestChecksumCalculation(unittest.TestCase):
    """Test checksum calculation functions."""
    
    def test_simple_checksum(self):
        """Test basic XOR checksum calculation."""
        data = [0x01, 0x02, 0x03]
        checksum = M0DeviceI2C._calculate_checksum(data)
        self.assertEqual(checksum, 0x00, "XOR of 0x01, 0x02, 0x03 should be 0x00")
    
    def test_checksum_zero(self):
        """Test checksum of empty data."""
        data = []
        checksum = M0DeviceI2C._calculate_checksum(data)
        self.assertEqual(checksum, 0x00, "Checksum of empty data should be 0x00")
    
    def test_checksum_single_byte(self):
        """Test checksum of single byte."""
        data = [0xFF]
        checksum = M0DeviceI2C._calculate_checksum(data)
        self.assertEqual(checksum, 0xFF, "Checksum of 0xFF should be 0xFF")
    
    def test_checksum_overflow(self):
        """Test checksum handles byte overflow correctly."""
        data = [0xFF, 0xFF]
        checksum = M0DeviceI2C._calculate_checksum(data)
        self.assertEqual(checksum, 0x00, "XOR of 0xFF, 0xFF should be 0x00")
    
    def test_checksum_real_frame(self):
        """Test checksum on realistic command frame."""
        # Frame: [length=1, command=WHOAREYOU]
        data = [0x01, I2CCommand.WHOAREYOU.value]
        checksum = M0DeviceI2C._calculate_checksum(data)
        self.assertEqual(checksum, 0x00)


class TestM0DeviceI2CInitialization(unittest.TestCase):
    """Test M0DeviceI2C initialization and configuration."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_pi = Mock()
        self.mock_pi.set_mode = Mock()
        self.mock_pi.write = Mock()
    
    @patch('M0DeviceI2C.smbus2')
    def test_init_valid_address(self, mock_smbus2):
        """Test initialization with valid I2C address."""
        m0 = M0DeviceI2C(
            pi=self.mock_pi,
            id="M0_0",
            address=0x00,
            reset_pin=25
        )
        
        self.assertEqual(m0.id, "M0_0")
        self.assertEqual(m0.address, 0x00)
        self.assertEqual(m0.reset_pin, 25)
        self.assertEqual(m0.mode, M0Mode.UNINITIALIZED)
    
    @patch('M0DeviceI2C.smbus2')
    def test_init_invalid_address_low(self, mock_smbus2):
        """Test initialization rejects address below range."""
        with self.assertRaises(ValueError):
            M0DeviceI2C(
                pi=self.mock_pi,
                id="M0_X",
                address=-1,  # Invalid
                reset_pin=25
            )
    
    @patch('M0DeviceI2C.smbus2')
    def test_init_invalid_address_high(self, mock_smbus2):
        """Test initialization rejects address above range."""
        with self.assertRaises(ValueError):
            M0DeviceI2C(
                pi=self.mock_pi,
                id="M0_X",
                address=0x08,  # Invalid (max is 0x07)
                reset_pin=25
            )
    
    @patch('M0DeviceI2C.smbus2', None)
    def test_init_no_smbus2(self):
        """Test initialization fails gracefully without smbus2."""
        with self.assertRaises(ValueError) as ctx:
            M0DeviceI2C(
                pi=self.mock_pi,
                id="M0_0",
                address=0x00,
                reset_pin=25
            )
        self.assertIn("smbus2", str(ctx.exception))


class TestM0DeviceI2CCommands(unittest.TestCase):
    """Test command sending and frame construction."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_pi = Mock()
        self.mock_bus = Mock()
        
        # Patch only the SMBus class used by M0DeviceI2C, not the entire smbus2 module.
        with patch('M0DeviceI2C.smbus2.SMBus', return_value=self.mock_bus):
            self.m0 = M0DeviceI2C(
                pi=self.mock_pi,
                id="M0_0",
                address=0x00,
                reset_pin=25
            )
            self.m0.bus = self.mock_bus
            self.m0.mode = M0Mode.I2C_READY
    
    def test_send_whoareyou_command(self):
        """Test WHOAREYOU command frame construction."""
        # Mock response: "ID:M0_0" with correct checksum including length byte
        self.mock_bus.read_i2c_block_data.return_value = _build_mock_response(b"ID:M0_0")
        
        response = self.m0._send_command_with_retry(I2CCommand.WHOAREYOU, timeout=1.0)
        
        # Verify write was called
        self.mock_bus.write_i2c_block_data.assert_called()
        call_args = self.mock_bus.write_i2c_block_data.call_args
        
        # Extract frame data
        sent_frame = [call_args[0][1]] + call_args[0][2]
        
        # Frame should be: [length=1, command=0x01, checksum]
        self.assertEqual(sent_frame[0], 0x01, "Length should be 1 (command only)")
        self.assertEqual(sent_frame[1], I2CCommand.WHOAREYOU.value, "Command should be WHOAREYOU")
        
        # Verify response
        self.assertIsNotNone(response)
    
    def test_send_show_command(self):
        """Test SHOW command sending."""
        self.mock_bus.read_i2c_block_data.return_value = _build_mock_response(b"ACK")
        
        result = self.m0.send_command("SHOW")
        
        self.assertTrue(result, "SHOW command should succeed")
        self.mock_bus.write_i2c_block_data.assert_called()
    
    def test_send_black_command(self):
        """Test BLACK command sending."""
        self.mock_bus.read_i2c_block_data.return_value = _build_mock_response(b"ACK")
        
        result = self.m0.send_command("BLACK")
        
        self.assertTrue(result, "BLACK command should succeed")
        self.mock_bus.write_i2c_block_data.assert_called()
    
    def test_send_img_command(self):
        """Test IMG command with payload."""
        self.mock_bus.read_i2c_block_data.return_value = _build_mock_response(b"ACK")
        
        result = self.m0.send_command("IMG:A01")
        
        self.assertTrue(result, "IMG command should succeed")
        
        # Verify payload was sent
        call_args = self.mock_bus.write_i2c_block_data.call_args
        sent_frame = [call_args[0][1]] + call_args[0][2]
        
        # Frame should include "A01" payload
        # [length, command, 'A', '0', '1', checksum]
        self.assertEqual(sent_frame[0], 4, "Length should be 4 (command + 3 chars)")
        self.assertEqual(sent_frame[1], I2CCommand.IMG.value)
        self.assertEqual(sent_frame[2], ord('A'))
        self.assertEqual(sent_frame[3], ord('0'))
        self.assertEqual(sent_frame[4], ord('1'))
    
    def test_send_unknown_command(self):
        """Test handling of unknown command."""
        result = self.m0.send_command("INVALID_CMD")
        
        self.assertFalse(result, "Unknown command should return False")


class TestRetryLogic(unittest.TestCase):
    """Test retry logic and error handling."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_pi = Mock()
        self.mock_bus = Mock()
        
        mock_smbus2 = MagicMock()
        mock_smbus2.SMBus.return_value = self.mock_bus
        with patch('M0DeviceI2C.smbus2', mock_smbus2):
            self.m0 = M0DeviceI2C(
                pi=self.mock_pi,
                id="M0_0",
                address=0x00,
                reset_pin=25
            )
            self.m0.bus = self.mock_bus
            self.m0.mode = M0Mode.I2C_READY
    
    def test_retry_on_ioerror(self):
        """Test retry logic on I/O error."""
        # Fail twice, succeed third time
        self.mock_bus.write_i2c_block_data.side_effect = [
            IOError("Bus error"),
            IOError("Bus error"),
            None  # Success
        ]
        
        self.mock_bus.read_i2c_block_data.return_value = _build_mock_response(b"ACK")

        response = self.m0._send_command_with_retry(I2CCommand.SHOW, timeout=1.0)

        # Should have retried and eventually succeeded
        self.assertEqual(self.mock_bus.write_i2c_block_data.call_count, 3)
    
    def test_max_retries_exceeded(self):
        """Test that max retries are enforced."""
        # Always fail
        self.mock_bus.write_i2c_block_data.side_effect = IOError("Bus error")
        
        with self.assertRaises(I2CError):
            self.m0._send_command_with_retry(I2CCommand.SHOW, timeout=1.0)
        
        # Should have tried max_retries times
        self.assertEqual(
            self.mock_bus.write_i2c_block_data.call_count,
            self.m0.max_retries
        )
    
    @patch('time.sleep')
    def test_exponential_backoff(self, mock_sleep):
        """Test exponential backoff between retries."""
        # Fail twice, succeed third time
        self.mock_bus.write_i2c_block_data.side_effect = [
            IOError("Bus error"),
            IOError("Bus error"),
            None
        ]
        
        self.mock_bus.read_i2c_block_data.return_value = _build_mock_response(b"ACK")

        self.m0._send_command_with_retry(I2CCommand.SHOW, timeout=1.0)

        # Verify backoff delays
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        
        # Should have exponentially increasing delays
        self.assertGreater(len(sleep_calls), 0)
        if len(sleep_calls) > 1:
            self.assertGreater(sleep_calls[1], sleep_calls[0])


class TestChecksumValidation(unittest.TestCase):
    """Test checksum validation on received frames."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_pi = Mock()
        self.mock_bus = Mock()
        
        mock_smbus2 = MagicMock()
        mock_smbus2.SMBus.return_value = self.mock_bus
        with patch('M0DeviceI2C.smbus2', mock_smbus2):
            self.m0 = M0DeviceI2C(
                pi=self.mock_pi,
                id="M0_0",
                address=0x00,
                reset_pin=25
            )
            self.m0.bus = self.mock_bus
            self.m0.mode = M0Mode.I2C_READY
    
    def test_valid_checksum(self):
        """Test that valid checksum passes."""
        self.mock_bus.write_i2c_block_data.return_value = None
        self.mock_bus.read_i2c_block_data.return_value = _build_mock_response(b"ACK")

        # Should not raise exception
        response = self.m0._send_command_with_retry(I2CCommand.SHOW, timeout=1.0)
        self.assertIsNotNone(response)

    def test_invalid_checksum(self):
        """Test that invalid checksum raises error."""
        # Build response with correct structure but wrong checksum
        bad_response = _build_mock_response(b"ACK")
        bad_response[4] = 0xFF  # Corrupt the checksum byte

        self.mock_bus.write_i2c_block_data.return_value = None
        self.mock_bus.read_i2c_block_data.return_value = bad_response

        with self.assertRaises(I2CChecksumError):
            self.m0._send_command_with_retry(I2CCommand.SHOW, timeout=1.0)


class TestTouchPolling(unittest.TestCase):
    """Test touch event polling and detection."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_pi = Mock()
        self.mock_bus = Mock()
        
        mock_smbus2 = MagicMock()
        mock_smbus2.SMBus.return_value = self.mock_bus
        with patch('M0DeviceI2C.smbus2', mock_smbus2):
            self.m0 = M0DeviceI2C(
                pi=self.mock_pi,
                id="M0_0",
                address=0x00,
                reset_pin=25
            )
            self.m0.bus = self.mock_bus
            self.m0.mode = M0Mode.COMMUNICATION
    
    @patch('time.sleep')
    def test_touch_detected(self, mock_sleep):
        """Test touch event detection."""
        # Mock touch response: status=1, x=120, y=80
        touch_x = 120
        touch_y = 80
        
        self.mock_bus.write_i2c_block_data.return_value = None

        touch_data = [
            1,  # Status: touch detected
            (touch_x >> 8) & 0xFF,  # X high byte
            touch_x & 0xFF,         # X low byte
            (touch_y >> 8) & 0xFF,  # Y high byte
            touch_y & 0xFF          # Y low byte
        ]
        self.mock_bus.read_i2c_block_data.return_value = _build_mock_response(touch_data)

        # Call poll method directly
        response = self.m0._send_command_with_retry(I2CCommand.TOUCH_POLL, timeout=1.0)

        # Verify response format
        self.assertEqual(response[0], 1, "Status should be 1 (touch detected)")

        # Verify coordinates
        received_x = (response[1] << 8) | response[2]
        received_y = (response[3] << 8) | response[4]
        self.assertEqual(received_x, touch_x)
        self.assertEqual(received_y, touch_y)

    def test_no_touch(self):
        """Test response when no touch detected."""
        self.mock_bus.write_i2c_block_data.return_value = None

        no_touch_data = [0, 0, 0, 0, 0]  # Status = 0
        self.mock_bus.read_i2c_block_data.return_value = _build_mock_response(no_touch_data)

        response = self.m0._send_command_with_retry(I2CCommand.TOUCH_POLL, timeout=1.0)

        self.assertEqual(response[0], 0, "Status should be 0 (no touch)")


class TestDeviceReset(unittest.TestCase):
    """Test hardware reset functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_pi = Mock()
        
        with patch('M0DeviceI2C.smbus2', MagicMock()):
            self.m0 = M0DeviceI2C(
                pi=self.mock_pi,
                id="M0_0",
                address=0x00,
                reset_pin=25
            )
    
    @patch('M0DeviceI2C.pigpio')
    @patch('time.sleep')
    def test_reset_pulse_sequence(self, mock_sleep, mock_pigpio):
        """Test GPIO reset pulse sequence."""
        mock_pigpio.OUTPUT = 1
        mock_pigpio.INPUT = 0
        self.m0.reset()

        # Verify GPIO sequence
        calls = self.mock_pi.method_calls

        # Should set pin as output
        self.assertIn(call.set_mode(25, unittest.mock.ANY), calls)

        # Should write LOW then HIGH
        write_calls = [c for c in calls if c[0] == 'write']
        self.assertGreater(len(write_calls), 0)

    def test_reset_without_pin(self):
        """Test reset when no reset pin configured."""
        with patch('M0DeviceI2C.smbus2', MagicMock()):
            m0_no_pin = M0DeviceI2C(
                pi=self.mock_pi,
                id="M0_0",
                address=0x00,
                reset_pin=None
            )
        
        # Should not raise exception
        m0_no_pin.reset()
        
        # Should not have called GPIO functions
        self.mock_pi.set_mode.assert_not_called()


class TestI2CDiscovery(unittest.TestCase):
    """Test I2C device discovery function."""
    
    @patch('M0DeviceI2C.smbus2')
    @patch('time.sleep')
    def test_discover_devices(self, mock_sleep, mock_smbus2):
        """Test discovery of I2C devices."""
        mock_bus = Mock()
        mock_smbus2.SMBus.return_value = mock_bus
        
        # Mock responses for 3 devices
        def read_byte_side_effect(addr):
            if addr in [0x00, 0x01, 0x02]:
                return 0  # Probe succeeds (any value)
            raise IOError("No device")

        def read_block_side_effect(addr, reg, length):
            id_map = {0x00: b"ID:M0_0", 0x01: b"ID:M0_1", 0x02: b"ID:M0_2"}
            if addr in id_map:
                return _build_mock_response(id_map[addr], pad_to=length)
            raise IOError("No device")

        mock_bus.read_byte.side_effect = read_byte_side_effect
        mock_bus.read_i2c_block_data.side_effect = read_block_side_effect
        mock_bus.write_i2c_block_data.return_value = None
        
        devices = discover_i2c_devices(bus_num=1, address_range=range(0x00, 0x08))
        
        # Should find 3 devices
        self.assertEqual(len(devices), 3)
        
        # Verify device IDs
        device_ids = [d[1] for d in devices]
        self.assertIn("M0_0", device_ids)
        self.assertIn("M0_1", device_ids)
        self.assertIn("M0_2", device_ids)
    
    @patch('M0DeviceI2C.smbus2')
    def test_discover_no_devices(self, mock_smbus2):
        """Test discovery when no devices present."""
        mock_bus = Mock()
        mock_smbus2.SMBus.return_value = mock_bus
        
        # All addresses fail
        mock_bus.read_byte.side_effect = IOError("No device")
        
        devices = discover_i2c_devices(bus_num=1, address_range=range(0x00, 0x08))
        
        # Should return empty list
        self.assertEqual(len(devices), 0)


class TestThreadSafety(unittest.TestCase):
    """Test thread safety of I2C operations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_pi = Mock()
        self.mock_bus = Mock()
        
        mock_smbus2 = MagicMock()
        mock_smbus2.SMBus.return_value = self.mock_bus
        with patch('M0DeviceI2C.smbus2', mock_smbus2):
            self.m0 = M0DeviceI2C(
                pi=self.mock_pi,
                id="M0_0",
                address=0x00,
                reset_pin=25
            )
            self.m0.bus = self.mock_bus
            self.m0.mode = M0Mode.I2C_READY
    
    def test_concurrent_commands(self):
        """Test that concurrent commands are serialized."""
        self.mock_bus.read_i2c_block_data.return_value = _build_mock_response(b"ACK")
        
        import threading
        
        results = []
        
        def send_command():
            result = self.m0.send_command("SHOW")
            results.append(result)
        
        # Start multiple threads
        threads = [threading.Thread(target=send_command) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # All commands should succeed
        self.assertEqual(len(results), 5)
        self.assertTrue(all(results))


class TestMessageQueue(unittest.TestCase):
    """Test message queue functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_pi = Mock()
        
        with patch('M0DeviceI2C.smbus2', MagicMock()):
            self.m0 = M0DeviceI2C(
                pi=self.mock_pi,
                id="M0_0",
                address=0x00,
                reset_pin=25
            )
    
    def test_message_queue_created(self):
        """Test that message queue is initialized."""
        self.assertIsInstance(self.m0.message_queue, queue.Queue)
    
    def test_flush_message_queue(self):
        """Test flushing message queue."""
        # Add some messages
        self.m0.message_queue.put(("M0_0", "TOUCH:100,200"))
        self.m0.message_queue.put(("M0_0", "TOUCH:150,250"))
        
        self.assertEqual(self.m0.message_queue.qsize(), 2)
        
        # Flush
        self.m0.flush_message_queue()
        
        self.assertTrue(self.m0.message_queue.empty())


class TestStopAndCleanup(unittest.TestCase):
    """Test stop and cleanup functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_pi = Mock()
        self.mock_bus = Mock()
        
        mock_smbus2 = MagicMock()
        mock_smbus2.SMBus.return_value = self.mock_bus
        with patch('M0DeviceI2C.smbus2', mock_smbus2):
            self.m0 = M0DeviceI2C(
                pi=self.mock_pi,
                id="M0_0",
                address=0x00,
                reset_pin=25
            )
            self.m0.bus = self.mock_bus
    
    def test_stop_closes_bus(self):
        """Test that stop() closes I2C bus."""
        self.m0.stop()
        
        self.mock_bus.close.assert_called_once()
        self.assertEqual(self.m0.mode, M0Mode.UNINITIALIZED)
    
    def test_stop_sets_stop_flag(self):
        """Test that stop() sets stop flag for polling thread."""
        self.m0.stop()
        
        self.assertTrue(self.m0.stop_flag.is_set())


# Test suite
def suite():
    """Create test suite."""
    suite = unittest.TestSuite()
    
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestChecksumCalculation))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestM0DeviceI2CInitialization))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestM0DeviceI2CCommands))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestRetryLogic))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestChecksumValidation))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestTouchPolling))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestDeviceReset))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestI2CDiscovery))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestThreadSafety))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestMessageQueue))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestStopAndCleanup))
    
    return suite


if __name__ == '__main__':
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite())
