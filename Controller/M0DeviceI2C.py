"""
M0DeviceI2C - I2C-based communication with M0 touchscreen controllers.

This module provides I2C communication with DFRobot M0 boards as an alternative
to the unreliable USB serial interface. I2C provides deterministic hardware
addressing and eliminates USB enumeration race conditions.

Author: OpenClaw Subagent
Date: 2026-02-03
"""

try:
    import smbus2
except ImportError:
    smbus2 = None
try:
    import pigpio
except ImportError:
    pigpio = None

import time
import threading
import queue
from enum import Enum
from typing import Optional, Tuple, List
import logging

logger = logging.getLogger(f"session_logger.{__name__}")


class I2CError(Exception):
    """Base exception for I2C communication errors."""
    pass


class I2CTimeoutError(I2CError):
    """Raised when I2C operation times out."""
    pass


class I2CChecksumError(I2CError):
    """Raised when checksum validation fails."""
    pass


class M0Mode(Enum):
    """M0 device operational modes."""
    UNINITIALIZED = 0
    I2C_READY = 1
    COMMUNICATION = 2
    ERROR = 3


class I2CCommand(Enum):
    """I2C command codes for M0 communication."""
    WHOAREYOU = 0x01
    SHOW = 0x02
    BLACK = 0x03
    IMG = 0x04
    TOUCH_POLL = 0x05
    ACK = 0x06
    NACK = 0x07


class M0DeviceI2C:
    """
    I2C-based M0 touchscreen controller interface.
    
    Provides robust I2C communication with retry logic, checksums, and
    timeout handling. Designed as a drop-in replacement for the serial-based
    M0Device class.
    
    Attributes:
        pi: pigpio instance for GPIO control (reset pin)
        id: Device identifier (e.g., "M0_0")
        address: I2C address (0x00-0x07, determined by GPIO pins on M0)
        reset_pin: GPIO pin number for hardware reset
        bus_num: I2C bus number (default 1 for Raspberry Pi)
        location: Physical location identifier (e.g., "left", "middle", "right")
    """
    
    # Protocol constants
    MAX_RETRIES = 3
    DEFAULT_TIMEOUT = 2.0  # seconds
    I2C_BUS = 1  # Raspberry Pi I2C bus 1
    RETRY_BACKOFF_BASE = 0.1  # seconds
    
    def __init__(self, 
                 pi, 
                 id: Optional[str] = None,
                 address: int = 0x00,
                 reset_pin: Optional[int] = None,
                 bus_num: int = 1,
                 location: Optional[str] = None):
        """
        Initialize I2C M0 device.
        
        Args:
            pi: pigpio.pi instance for GPIO control
            id: Device identifier string
            address: I2C address (0x00-0x07)
            reset_pin: GPIO pin for hardware reset
            bus_num: I2C bus number (default 1)
            location: Physical location identifier
            
        Raises:
            ValueError: If smbus2 is not available or address is invalid
        """
        if smbus2 is None:
            raise ValueError("smbus2 library not available. Install with: pip install smbus2")
        
        if pigpio is not None:
            try:
                if not isinstance(pi, pigpio.pi):
                    raise ValueError("pi must be an instance of pigpio.pi")
            except TypeError:
                # pigpio.pi is not a valid type (e.g., during mocking)
                pass
        
        if not (0x00 <= address <= 0x07):
            raise ValueError(f"I2C address must be 0x00-0x07, got {address:#04x}")
        
        self.pi = pi
        self.id = id
        self.address = address
        self.reset_pin = reset_pin
        self.bus_num = bus_num
        self.location = location
        
        # I2C bus connection
        self.bus: Optional[smbus2.SMBus] = None
        self.bus_lock = threading.RLock()  # Recursive lock for nested calls
        
        # State management
        self.mode = M0Mode.UNINITIALIZED
        self.is_touched = False
        self.last_touch_x = 0
        self.last_touch_y = 0
        
        # Message queue for compatibility with serial M0Device
        self.message_queue = queue.Queue()
        
        # Touch polling thread
        self.stop_flag = threading.Event()
        self.poll_thread: Optional[threading.Thread] = None
        self.poll_interval = 0.1  # seconds
        
        logger.info(f"[{self.id}] Initialized I2C device at address {self.address:#04x}")
    
    def __del__(self):
        """Clean up resources."""
        try:
            if hasattr(self, 'id'):
                logger.info(f"[{self.id}] Cleaning up I2C device...")
            self.stop()
        except:
            pass  # Ignore cleanup errors
    
    def initialize(self) -> bool:
        """
        Initialize I2C communication and verify device identity.
        
        Returns:
            bool: True if initialization successful
            
        Raises:
            I2CError: If initialization fails
        """
        logger.info(f"[{self.id}] Initializing I2C device at {self.address:#04x}...")
        
        try:
            # Open I2C bus
            self.bus = smbus2.SMBus(self.bus_num)
            self.mode = M0Mode.I2C_READY
            logger.info(f"[{self.id}] Opened I2C bus {self.bus_num}")
            
            # Verify device identity
            if not self._verify_identity():
                raise I2CError(f"Identity verification failed for {self.id}")
            
            # Start touch polling thread
            self._start_poll_thread()
            self.mode = M0Mode.COMMUNICATION
            
            logger.info(f"[{self.id}] I2C initialization complete")
            return True
            
        except Exception as e:
            logger.error(f"[{self.id}] Initialization failed: {e}")
            self.mode = M0Mode.ERROR
            raise I2CError(f"Failed to initialize {self.id}: {e}") from e
    
    def _verify_identity(self, timeout: float = 2.0) -> bool:
        """
        Verify device identity using WHOAREYOU command.
        
        Args:
            timeout: Maximum time to wait for response
            
        Returns:
            bool: True if identity matches expected ID
        """
        try:
            response = self._send_command_with_retry(I2CCommand.WHOAREYOU, timeout=timeout)
            
            if response:
                # Response format: "ID:M0_X"
                response_str = bytes(response).decode('utf-8', errors='ignore').strip('\x00')
                logger.info(f"[{self.id}] Identity response: {response_str}")
                
                if response_str == f"ID:{self.id}":
                    logger.info(f"[{self.id}] Identity verified")
                    return True
                else:
                    logger.error(f"[{self.id}] Identity mismatch: expected {self.id}, got {response_str}")
                    return False
            else:
                logger.error(f"[{self.id}] No response to WHOAREYOU")
                return False
                
        except Exception as e:
            logger.error(f"[{self.id}] Identity verification error: {e}")
            return False
    
    def reset(self):
        """
        Perform hardware reset using GPIO pin.
        
        Sends a low pulse on the reset pin to trigger M0 hardware reset.
        """
        if self.reset_pin is None:
            logger.warning(f"[{self.id}] No reset pin configured, skipping reset")
            return
        
        logger.info(f"[{self.id}] Resetting M0 via GPIO pin {self.reset_pin}")
        
        try:
            # Stop polling thread during reset
            if self.poll_thread and self.poll_thread.is_alive():
                self._stop_poll_thread()
            
            # Send reset pulse
            self.pi.set_mode(self.reset_pin, pigpio.OUTPUT)
            time.sleep(0.01)
            self.pi.write(self.reset_pin, 0)  # Pull low
            time.sleep(0.1)  # Hold for 100ms
            self.pi.write(self.reset_pin, 1)  # Release
            time.sleep(0.01)
            self.pi.set_mode(self.reset_pin, pigpio.INPUT)  # High-Z
            
            # Wait for M0 to boot
            time.sleep(0.5)
            
            logger.info(f"[{self.id}] Reset complete")
            
        except Exception as e:
            logger.error(f"[{self.id}] Reset failed: {e}")
    
    def send_command(self, cmd: str) -> bool:
        """
        Send a text command to the M0 (compatibility wrapper).
        
        Args:
            cmd: Command string (e.g., "SHOW", "BLACK", "IMG:A01")
            
        Returns:
            bool: True if command sent successfully
        """
        try:
            # Parse command
            if cmd == "WHOAREYOU?":
                self._send_command_with_retry(I2CCommand.WHOAREYOU)
            elif cmd == "SHOW":
                self._send_command_with_retry(I2CCommand.SHOW)
            elif cmd == "BLACK":
                self._send_command_with_retry(I2CCommand.BLACK)
            elif cmd.startswith("IMG:"):
                image_id = cmd[4:]
                self._send_image_command(image_id)
            else:
                logger.warning(f"[{self.id}] Unknown command: {cmd}")
                return False
            
            logger.info(f"[{self.id}] -> {cmd}")
            return True
            
        except Exception as e:
            logger.error(f"[{self.id}] Failed to send command '{cmd}': {e}")
            return False
    
    def _send_image_command(self, image_id: str) -> bytes:
        """
        Send IMG command with image ID payload.
        
        Args:
            image_id: Image identifier string
            
        Returns:
            bytes: Response from M0
        """
        payload = image_id.encode('utf-8')
        return self._send_command_with_retry(I2CCommand.IMG, payload=payload)
    
    def _send_command_with_retry(self, 
                                  command: I2CCommand, 
                                  payload: Optional[bytes] = None,
                                  timeout: float = DEFAULT_TIMEOUT) -> Optional[bytes]:
        """
        Send I2C command with automatic retry and exponential backoff.
        
        Args:
            command: Command code
            payload: Optional payload bytes
            timeout: Response timeout in seconds
            
        Returns:
            Optional[bytes]: Response data or None if failed
            
        Raises:
            I2CError: If all retries fail
        """
        for attempt in range(self.MAX_RETRIES):
            try:
                response = self._send_command_raw(command, payload, timeout)
                return response
                
            except (OSError, IOError) as e:
                if attempt < self.MAX_RETRIES - 1:
                    backoff = self.RETRY_BACKOFF_BASE * (2 ** attempt)
                    logger.warning(f"[{self.id}] I2C error (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}, "
                                 f"retrying in {backoff:.2f}s...")
                    time.sleep(backoff)
                else:
                    logger.error(f"[{self.id}] All {self.MAX_RETRIES} retries failed")
                    raise I2CError(f"I2C communication failed after {self.MAX_RETRIES} retries") from e
        
        return None
    
    def _send_command_raw(self, 
                          command: I2CCommand, 
                          payload: Optional[bytes] = None,
                          timeout: float = DEFAULT_TIMEOUT) -> Optional[bytes]:
        """
        Send raw I2C command with framing and checksum.
        
        Protocol frame format:
        [length_byte, command_byte, payload..., checksum_byte]
        
        Args:
            command: Command code
            payload: Optional payload data
            timeout: Response timeout
            
        Returns:
            Optional[bytes]: Response data
            
        Raises:
            I2CChecksumError: If checksum validation fails
            I2CTimeoutError: If response times out
        """
        with self.bus_lock:
            try:
                # Build command frame
                if payload is None:
                    payload = b''
                
                frame_length = 1 + len(payload)  # command byte + payload
                frame_data = [command.value] + list(payload)
                checksum = self._calculate_checksum(frame_data)
                
                # Complete frame: [length, command, payload..., checksum]
                frame = [frame_length] + frame_data + [checksum]
                
                # Send command
                self.bus.write_i2c_block_data(self.address, frame[0], frame[1:])
                logger.debug(f"[{self.id}] Sent I2C frame: {[f'{b:#04x}' for b in frame]}")
                
                # Wait for M0 to process
                time.sleep(0.01)
                
                # Read response
                response = self._read_response(timeout)
                return response
                
            except Exception as e:
                logger.error(f"[{self.id}] I2C send error: {e}")
                raise
    
    def _read_response(self, timeout: float = DEFAULT_TIMEOUT) -> Optional[bytes]:
        """
        Read response from I2C device with timeout.
        
        Args:
            timeout: Maximum time to wait for response
            
        Returns:
            Optional[bytes]: Response data or None
            
        Raises:
            I2CTimeoutError: If no response within timeout
            I2CChecksumError: If checksum validation fails
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Read length byte
                length = self.bus.read_byte(self.address)
                
                if length == 0:
                    time.sleep(0.01)
                    continue
                
                # Read response data + checksum
                data = self.bus.read_i2c_block_data(self.address, 0, length + 1)
                
                # Validate checksum
                received_checksum = data[-1]
                calculated_checksum = self._calculate_checksum(data[:-1])
                
                if received_checksum != calculated_checksum:
                    raise I2CChecksumError(
                        f"Checksum mismatch: received {received_checksum:#04x}, "
                        f"calculated {calculated_checksum:#04x}"
                    )
                
                logger.debug(f"[{self.id}] Received I2C response: {[f'{b:#04x}' for b in data]}")
                return bytes(data[:-1])  # Return data without checksum
                
            except (OSError, IOError):
                # No data available yet
                time.sleep(0.01)
                continue
        
        raise I2CTimeoutError(f"No response from {self.id} within {timeout}s")
    
    @staticmethod
    def _calculate_checksum(data: List[int]) -> int:
        """
        Calculate simple XOR checksum.
        
        Args:
            data: List of byte values
            
        Returns:
            int: Checksum byte (0-255)
        """
        checksum = 0
        for byte in data:
            checksum ^= byte
        return checksum & 0xFF
    
    def _start_poll_thread(self):
        """Start background thread for polling touch events."""
        if self.poll_thread and self.poll_thread.is_alive():
            logger.warning(f"[{self.id}] Poll thread already running")
            return
        
        self.stop_flag.clear()
        self.poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.poll_thread.start()
        logger.info(f"[{self.id}] Started touch polling thread")
    
    def _stop_poll_thread(self):
        """Stop background polling thread."""
        self.stop_flag.set()
        if self.poll_thread:
            self.poll_thread.join(timeout=2.0)
        logger.info(f"[{self.id}] Stopped touch polling thread")
    
    def _poll_loop(self):
        """
        Background thread loop for polling touch events.
        
        Continuously polls the M0 for TOUCH events and updates state.
        """
        logger.info(f"[{self.id}] Starting touch poll loop")
        
        while not self.stop_flag.is_set():
            try:
                # Poll for touch
                response = self._send_command_with_retry(
                    I2CCommand.TOUCH_POLL,
                    timeout=0.5  # Shorter timeout for polling
                )
                
                if response and len(response) >= 4:
                    # Parse touch response: [status_byte, x_high, x_low, y_high, y_low]
                    status = response[0]
                    
                    if status == 1:  # Touch detected
                        x = (response[1] << 8) | response[2]
                        y = (response[3] << 8) | response[4]
                        
                        self.is_touched = True
                        self.last_touch_x = x
                        self.last_touch_y = y
                        
                        # Add to message queue for compatibility
                        touch_msg = f"TOUCH:{x},{y}"
                        self.message_queue.put((self.id, touch_msg))
                        logger.debug(f"[{self.id}] {touch_msg}")
                    else:
                        self.is_touched = False
                
                time.sleep(self.poll_interval)
                
            except I2CTimeoutError:
                # Expected - M0 may not have touch data
                pass
            except Exception as e:
                logger.error(f"[{self.id}] Poll loop error: {e}")
                time.sleep(self.poll_interval)
        
        logger.info(f"[{self.id}] Touch poll loop stopped")
    
    def flush_message_queue(self):
        """Clear all messages from the queue."""
        while not self.message_queue.empty():
            try:
                self.message_queue.get_nowait()
            except queue.Empty:
                break
    
    def stop(self):
        """
        Stop polling and close I2C bus.
        """
        logger.info(f"[{self.id}] Stopping I2C device...")
        
        # Stop polling thread
        if self.poll_thread and self.poll_thread.is_alive():
            self._stop_poll_thread()
        
        # Close I2C bus
        with self.bus_lock:
            if self.bus:
                try:
                    self.bus.close()
                    logger.info(f"[{self.id}] Closed I2C bus")
                except Exception as e:
                    logger.error(f"[{self.id}] Error closing I2C bus: {e}")
                finally:
                    self.bus = None
        
        self.mode = M0Mode.UNINITIALIZED
        logger.info(f"[{self.id}] Stopped")


def discover_i2c_devices(bus_num: int = 1, 
                         address_range: range = range(0x00, 0x08)) -> List[Tuple[int, str]]:
    """
    Discover I2C M0 devices on the bus.
    
    Args:
        bus_num: I2C bus number
        address_range: Range of addresses to scan
        
    Returns:
        List of tuples (address, device_id)
    """
    if smbus2 is None:
        raise ValueError("smbus2 library not available")
    
    devices = []
    bus = smbus2.SMBus(bus_num)
    
    try:
        for addr in address_range:
            try:
                # Try to read from device
                bus.read_byte(addr)
                
                # Device responded - query identity
                # Send WHOAREYOU command
                frame = [1, I2CCommand.WHOAREYOU.value, I2CCommand.WHOAREYOU.value]
                bus.write_i2c_block_data(addr, frame[0], frame[1:])
                time.sleep(0.05)
                
                # Read response
                length = bus.read_byte(addr)
                if length > 0:
                    data = bus.read_i2c_block_data(addr, 0, length + 1)
                    device_id = bytes(data[:-1]).decode('utf-8', errors='ignore').strip('\x00')
                    
                    if device_id.startswith("ID:"):
                        devices.append((addr, device_id[3:]))  # Strip "ID:" prefix
                        logger.info(f"Found device at {addr:#04x}: {device_id}")
                
            except (OSError, IOError):
                # No device at this address
                pass
    
    finally:
        bus.close()
    
    return devices


if __name__ == "__main__":
    # Test I2C discovery
    logging.basicConfig(level=logging.DEBUG)
    
    print("Scanning I2C bus for M0 devices...")
    devices = discover_i2c_devices()
    
    if devices:
        print(f"Found {len(devices)} devices:")
        for addr, device_id in devices:
            print(f"  {addr:#04x}: {device_id}")
    else:
        print("No devices found")
