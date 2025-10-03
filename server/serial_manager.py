"""
Serial Manager Module
Handles communication with Arduino via serial connection
"""

import serial
import threading
import time
import logging
import queue
from typing import Optional, Callable, Dict, Any
from datetime import datetime

from models import ArduinoStatus, LightReading


class SerialManager:
    """Manages serial communication with Arduino"""
    
    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 2.0):
        """
        Initialize serial manager
        
        Args:
            port: Serial port path
            baudrate: Communication baudrate
            timeout: Read timeout in seconds
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_conn: Optional[serial.Serial] = None
        self.connected = False
        self.logger = logging.getLogger(__name__)
        
        # Threading
        self.read_thread: Optional[threading.Thread] = None
        self.should_run = False
        self.lock = threading.Lock()
        
        # Command queue
        self.command_queue = queue.Queue()
        
        # Callbacks for different message types
        self.callbacks: Dict[str, Callable] = {}
        
        # Arduino status
        self.status = ArduinoStatus(port=port)
        
    def connect(self) -> bool:
        """
        Establish serial connection to Arduino
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.logger.info(f"Attempting to connect to {self.port} at {self.baudrate} baud")
            
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                write_timeout=1.0
            )
            
            # Wait for Arduino to reset
            time.sleep(2)
            
            # Clear any startup messages
            self.serial_conn.reset_input_buffer()
            self.serial_conn.reset_output_buffer()
            
            self.connected = True
            self.status.connected = True
            self.status.last_seen = datetime.now()
            
            self.logger.info(f"Connected to Arduino on {self.port}")
            
            # Start read thread
            self.start_reading()
            
            # Set initial mode to MANUAL to match server expectation
            time.sleep(0.5)
            self.send_command("MANUAL_MODE")
            time.sleep(0.2)
            
            # Request initial status
            self.send_command("GET_STATUS")
            
            return True
            
        except serial.SerialException as e:
            self.logger.error(f"Failed to connect to {self.port}: {e}")
            self.connected = False
            self.status.connected = False
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error during connection: {e}")
            self.connected = False
            self.status.connected = False
            return False
    
    def disconnect(self):
        """Close serial connection"""
        self.should_run = False
        
        if self.read_thread and self.read_thread.is_alive():
            self.read_thread.join(timeout=2.0)
        
        if self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.close()
                self.logger.info("Serial connection closed")
            except Exception as e:
                self.logger.error(f"Error closing serial connection: {e}")
        
        self.connected = False
        self.status.connected = False
    
    def start_reading(self):
        """Start background thread to read serial data"""
        if self.read_thread and self.read_thread.is_alive():
            self.logger.warning("Read thread already running")
            return
        
        self.should_run = True
        self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
        self.read_thread.start()
        self.logger.info("Serial read thread started")
    
    def _read_loop(self):
        """Background thread loop for reading serial data"""
        while self.should_run and self.connected:
            try:
                if self.serial_conn and self.serial_conn.in_waiting > 0:
                    line = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                    
                    if line:
                        self.logger.debug(f"Received: {line}")
                        self._process_message(line)
                        self.status.last_seen = datetime.now()
                
                time.sleep(0.01)  # Small delay to prevent CPU spinning
                
            except serial.SerialException as e:
                self.logger.error(f"Serial read error: {e}")
                self.connected = False
                self.status.connected = False
                break
            except Exception as e:
                self.logger.error(f"Unexpected error in read loop: {e}")
    
    def _process_message(self, message: str):
        """
        Process received message from Arduino
        
        Args:
            message: Raw message string
        """
        try:
            # Parse message format: "TYPE:VALUE" or "TYPE:KEY1:VAL1,KEY2:VAL2"
            if ':' not in message:
                return
            
            parts = message.split(':', 1)
            msg_type = parts[0].upper()
            msg_data = parts[1] if len(parts) > 1 else ""
            
            # Route message to appropriate handler
            if msg_type == "LIGHT":
                self._handle_light_reading(msg_data)
            elif msg_type == "POSITION":
                self._handle_position_update(msg_data)
            elif msg_type == "MOTOR":
                self._handle_motor_status(msg_data)
            elif msg_type == "MODE":
                self._handle_mode_update(msg_data)
            elif msg_type == "CALIBRATION":
                self._handle_calibration_data(msg_data)
            elif msg_type == "ERROR":
                self._handle_error(msg_data)
            elif msg_type == "STATUS":
                self._handle_status_message(msg_data)
            elif msg_type == "READY":
                self._handle_ready_message(msg_data)
            elif msg_type == "VERSION":
                self.status.firmware_version = msg_data
            elif msg_type == "UPTIME":
                self.status.uptime_ms = int(msg_data)
            elif msg_type == "PONG":
                self.logger.debug("Received PONG")
            
            # Call registered callbacks
            if msg_type in self.callbacks:
                self.callbacks[msg_type](msg_data)
                
        except Exception as e:
            self.logger.error(f"Error processing message '{message}': {e}")
    
    def _handle_light_reading(self, data: str):
        """Handle light sensor reading"""
        try:
            value = int(data)
            self.logger.debug(f"Light reading: {value}")
            
            if "LIGHT" in self.callbacks:
                self.callbacks["LIGHT"](value)
                
        except ValueError:
            self.logger.error(f"Invalid light value: {data}")
    
    def _handle_position_update(self, data: str):
        """Handle curtain position update"""
        self.logger.info(f"Position update: {data}")
        
        if "POSITION" in self.callbacks:
            self.callbacks["POSITION"](data.lower())
    
    def _handle_motor_status(self, data: str):
        """Handle motor status update"""
        self.logger.info(f"Motor status: {data}")
        
        if "MOTOR" in self.callbacks:
            self.callbacks["MOTOR"](data.lower())
    
    def _handle_mode_update(self, data: str):
        """Handle mode update from Arduino"""
        mode = data.strip().upper()
        self.logger.info(f"📡 Arduino MODE update: '{mode}' -> passing '{mode.lower()}' to callback")
        
        if "MODE" in self.callbacks:
            self.callbacks["MODE"](mode.lower())
        else:
            self.logger.warning("No MODE callback registered!")
    
    def _handle_calibration_data(self, data: str):
        """Handle calibration information"""
        try:
            # Parse: "YES,MIN:100,MAX:900" or "LOADED"
            parts = data.split(',')
            
            for part in parts:
                if part == "YES":
                    self.status.calibrated = True
                elif part.startswith("MIN:"):
                    self.status.light_min = int(part.split(':')[1])
                elif part.startswith("MAX:"):
                    self.status.light_max = int(part.split(':')[1])
                    
            self.logger.info(f"Calibration: {self.status.calibrated}, "
                           f"Range: {self.status.light_min}-{self.status.light_max}")
            
        except Exception as e:
            self.logger.error(f"Error parsing calibration data: {e}")
    
    def _handle_error(self, data: str):
        """Handle error message from Arduino"""
        self.logger.error(f"Arduino error: {data}")
        
        if "ERROR" in self.callbacks:
            self.callbacks["ERROR"](data)
    
    def _handle_status_message(self, data: str):
        """Handle status message"""
        self.logger.debug(f"Status: {data}")
    
    def _handle_ready_message(self, data: str):
        """Handle ready message from Arduino"""
        self.logger.info(f"Arduino ready: {data}")
        self.status.firmware_version = data if data else "unknown"
    
    def send_command(self, command: str, params: Optional[str] = None) -> bool:
        """
        Send command to Arduino
        
        Args:
            command: Command string
            params: Optional parameters
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.connected or not self.serial_conn:
            self.logger.warning(f"Cannot send command '{command}': Not connected")
            return False
        
        try:
            with self.lock:
                # Format command
                cmd = f"{command}:{params}" if params else command
                cmd += "\n"
                
                # Send command
                self.serial_conn.write(cmd.encode('utf-8'))
                self.serial_conn.flush()
                
                self.logger.debug(f"Sent command: {cmd.strip()}")
                return True
                
        except serial.SerialException as e:
            self.logger.error(f"Error sending command: {e}")
            self.connected = False
            self.status.connected = False
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error sending command: {e}")
            return False
    
    def register_callback(self, message_type: str, callback: Callable):
        """
        Register callback for specific message type
        
        Args:
            message_type: Type of message to listen for
            callback: Function to call when message received
        """
        self.callbacks[message_type] = callback
        self.logger.debug(f"Registered callback for {message_type}")
    
    def open_curtain(self) -> bool:
        """Send command to open curtain"""
        return self.send_command("OPEN_CURTAIN")
    
    def close_curtain(self) -> bool:
        """Send command to close curtain"""
        return self.send_command("CLOSE_CURTAIN")
    
    def set_open_threshold(self, threshold: int) -> bool:
        """
        Set light threshold for opening curtain
        
        Args:
            threshold: Light level below which curtain opens (0-1023)
        """
        return self.send_command("SET_OPEN_THRESHOLD", str(threshold))
    
    def set_close_threshold(self, threshold: int) -> bool:
        """
        Set light threshold for closing curtain
        
        Args:
            threshold: Light level above which curtain closes (0-1023)
        """
        return self.send_command("SET_CLOSE_THRESHOLD", str(threshold))
    
    def stop_motor(self) -> bool:
        """Send command to stop motor"""
        return self.send_command("STOP_MOTOR")
    
    def read_light(self) -> bool:
        """Request light reading"""
        return self.send_command("READ_LIGHT")
    
    def get_status(self) -> bool:
        """Request full status"""
        return self.send_command("GET_STATUS")
    
    def calibrate_light(self) -> bool:
        """Start light sensor calibration"""
        return self.send_command("CALIBRATE_LIGHT")
    
    def set_motor_speed(self, speed: int) -> bool:
        """
        Set motor speed
        
        Args:
            speed: Speed percentage (0-100)
        """
        return self.send_command("SET_SPEED", str(speed))
    
    def ping(self) -> bool:
        """Send ping to check connection"""
        return self.send_command("PING")
    
    def get_arduino_status(self) -> ArduinoStatus:
        """Get current Arduino status"""
        return self.status
    
    def is_connected(self) -> bool:
        """Check if connected to Arduino"""
        return self.connected and self.serial_conn is not None and self.serial_conn.is_open 