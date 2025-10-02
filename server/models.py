"""
Data Models Module
Defines data structures for system entities
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class CurtainPosition(Enum):
    """Enumeration for curtain positions"""
    UNKNOWN = "unknown"
    OPEN = "open"
    CLOSED = "closed"
    PARTIAL = "partial"
    OPENING = "opening"
    CLOSING = "closing"


class MotorState(Enum):
    """Enumeration for motor states"""
    STOPPED = "stopped"
    OPENING = "opening"
    CLOSING = "closing"


class SystemMode(Enum):
    """Enumeration for system operating modes"""
    MANUAL = "manual"
    AUTO = "auto"


@dataclass
class LightReading:
    """Light sensor reading data model"""
    timestamp: datetime
    raw_value: int  # 0-1023 from Arduino ADC
    calibrated_value: Optional[float] = None  # Percentage or lux
    sensor_id: str = "main_photoresistor"
    location: str = "living_room"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'raw_value': self.raw_value,
            'calibrated_value': self.calibrated_value,
            'sensor_id': self.sensor_id,
            'location': self.location
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LightReading':
        """Create instance from dictionary"""
        if isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass
class CurtainState:
    """Current state of curtain system"""
    position: CurtainPosition = CurtainPosition.UNKNOWN
    motor_state: MotorState = MotorState.STOPPED
    mode: SystemMode = SystemMode.MANUAL
    motor_speed: int = 100  # Percentage
    last_updated: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'position': self.position.value,
            'motor_state': self.motor_state.value,
            'mode': self.mode.value,
            'motor_speed': self.motor_speed,
            'last_updated': self.last_updated.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CurtainState':
        """Create instance from dictionary"""
        return cls(
            position=CurtainPosition(data.get('position', 'unknown')),
            motor_state=MotorState(data.get('motor_state', 'stopped')),
            mode=SystemMode(data.get('mode', 'manual')),
            motor_speed=data.get('motor_speed', 100),
            last_updated=datetime.fromisoformat(data['last_updated']) 
                if 'last_updated' in data else datetime.now()
        )


@dataclass
class SystemSettings:
    """System configuration settings"""
    auto_mode_enabled: bool = False
    threshold_dark: int = 300
    threshold_bright: int = 700
    hysteresis: int = 50
    motor_speed: int = 100
    motor_timeout: int = 30
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SystemSettings':
        """Create instance from dictionary"""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


@dataclass
class ArduinoStatus:
    """Arduino connection and status information"""
    connected: bool = False
    port: str = ""
    last_seen: Optional[datetime] = None
    firmware_version: str = "unknown"
    calibrated: bool = False
    light_min: int = 0
    light_max: int = 1023
    uptime_ms: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'connected': self.connected,
            'port': self.port,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'firmware_version': self.firmware_version,
            'calibrated': self.calibrated,
            'light_min': self.light_min,
            'light_max': self.light_max,
            'uptime_ms': self.uptime_ms
        }


@dataclass
class MQTTStatus:
    """MQTT connection status"""
    connected: bool = False
    broker: str = ""
    last_publish: Optional[datetime] = None
    last_message: Optional[datetime] = None
    messages_sent: int = 0
    messages_received: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'connected': self.connected,
            'broker': self.broker,
            'last_publish': self.last_publish.isoformat() if self.last_publish else None,
            'last_message': self.last_message.isoformat() if self.last_message else None,
            'messages_sent': self.messages_sent,
            'messages_received': self.messages_received
        }


@dataclass
class SystemStatus:
    """Overall system status"""
    arduino: ArduinoStatus = field(default_factory=ArduinoStatus)
    mqtt: MQTTStatus = field(default_factory=MQTTStatus)
    curtain: CurtainState = field(default_factory=CurtainState)
    settings: SystemSettings = field(default_factory=SystemSettings)
    latest_light: Optional[LightReading] = None
    startup_time: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'arduino': self.arduino.to_dict(),
            'mqtt': self.mqtt.to_dict(),
            'curtain': self.curtain.to_dict(),
            'settings': self.settings.to_dict(),
            'latest_light': self.latest_light.to_dict() if self.latest_light else None,
            'startup_time': self.startup_time.isoformat(),
            'uptime_seconds': (datetime.now() - self.startup_time).total_seconds()
        }


@dataclass
class CurtainOperation:
    """Record of curtain operation"""
    timestamp: datetime
    operation: str  # 'open', 'close', 'stop', 'auto_open', 'auto_close'
    trigger: str  # 'manual', 'auto_dark', 'auto_bright', 'mqtt', 'api'
    light_level_before: Optional[int] = None
    light_level_after: Optional[int] = None
    duration_ms: Optional[int] = None
    success: bool = True
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'operation': self.operation,
            'trigger': self.trigger,
            'light_level_before': self.light_level_before,
            'light_level_after': self.light_level_after,
            'duration_ms': self.duration_ms,
            'success': self.success,
            'error_message': self.error_message
        }


@dataclass
class ErrorEvent:
    """System error event"""
    timestamp: datetime
    error_type: str
    error_message: str
    component: str  # 'arduino', 'mqtt', 'database', 'api'
    severity: str = "error"  # 'warning', 'error', 'critical'
    resolved: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'error_type': self.error_type,
            'error_message': self.error_message,
            'component': self.component,
            'severity': self.severity,
            'resolved': self.resolved
        } 