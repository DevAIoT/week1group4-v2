"""
Configuration Manager Module
Loads and validates system configuration from YAML file
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional
from pathlib import Path


class ConfigManager:
    """Manages application configuration with validation"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize configuration manager
        
        Args:
            config_path: Path to YAML configuration file
        """
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self.logger = logging.getLogger(__name__)
        
    def load(self) -> Dict[str, Any]:
        """
        Load configuration from YAML file
        
        Returns:
            Dictionary containing configuration
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config file is invalid
        """
        if not os.path.exists(self.config_path):
            self.logger.warning(f"Config file {self.config_path} not found, using defaults")
            return self._get_default_config()
        
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
                self.logger.info(f"Configuration loaded from {self.config_path}")
                
            # Validate configuration
            self._validate_config()
            
            # Create necessary directories
            self._create_directories()
            
            return self.config
            
        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing config file: {e}")
            return self._get_default_config()
        except Exception as e:
            self.logger.error(f"Unexpected error loading config: {e}")
            return self._get_default_config()
    
    def _validate_config(self):
        """Validate configuration structure and values"""
        required_sections = ['serial', 'mqtt', 'database', 'server', 'curtain']
        
        for section in required_sections:
            if section not in self.config:
                raise ValueError(f"Missing required config section: {section}")
        
        # Validate serial configuration
        if 'port' not in self.config['serial']:
            raise ValueError("Serial port not specified in configuration")
        
        # Validate MQTT configuration
        if 'broker' not in self.config['mqtt']:
            raise ValueError("MQTT broker not specified in configuration")
        
        self.logger.info("Configuration validation passed")
    
    def _create_directories(self):
        """Create necessary directories for logs and data"""
        directories = []
        
        # Logging directory
        if 'logging' in self.config and 'file' in self.config['logging']:
            log_dir = Path(self.config['logging']['file']).parent
            directories.append(log_dir)
        
        # Data directory
        if 'system' in self.config and 'data_directory' in self.config['system']:
            data_dir = Path(self.config['system']['data_directory'])
            directories.append(data_dir)
        
        # Database directory
        if 'database' in self.config and 'path' in self.config['database']:
            db_dir = Path(self.config['database']['path']).parent
            if db_dir != Path('.'):
                directories.append(db_dir)
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Created directory: {directory}")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration"""
        return {
            'serial': {
                'port': '/dev/ttyACM0',
                'baudrate': 115200,
                'timeout': 2,
                'reconnect_interval': 5
            },
            'mqtt': {
                'broker': 'localhost',
                'port': 1883,
                'keepalive': 60,
                'client_id': 'curtain_control_rpi',
                'topics': {
                    'light_reading': 'curtain/light/reading',
                    'position_status': 'curtain/position/status',
                    'control_command': 'curtain/control/command',
                    'system_status': 'curtain/system/status',
                    'alerts': 'curtain/alerts/errors',
                    'heartbeat': 'curtain/system/heartbeat'
                },
                'publish_interval': {
                    'light': 5,
                    'status': 10,
                    'heartbeat': 30
                }
            },
            'database': {
                'path': 'curtain_control.db',
                'retention_days': 30
            },
            'server': {
                'host': '0.0.0.0',
                'port': 5000,
                'debug': False,
                'cors_enabled': True
            },
            'curtain': {
                'auto_mode': False,
                'thresholds': {
                    'dark': 300,
                    'bright': 700,
                    'hysteresis': 50
                },
                'motor': {
                    'default_speed': 100,
                    'timeout': 30
                },
                'position': {
                    'default': 'unknown'
                }
            },
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'file': 'logs/curtain_control.log',
                'max_bytes': 10485760,
                'backup_count': 5
            },
            'system': {
                'timezone': 'UTC',
                'data_directory': 'data',
                'enable_simulation': True
            }
        }
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation
        
        Args:
            key_path: Configuration key path (e.g., 'mqtt.broker')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key_path.split('.')
        value = self.config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key_path: str, value: Any):
        """
        Set configuration value using dot notation
        
        Args:
            key_path: Configuration key path (e.g., 'mqtt.broker')
            value: Value to set
        """
        keys = key_path.split('.')
        config = self.config
        
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        config[keys[-1]] = value
        self.logger.debug(f"Configuration updated: {key_path} = {value}")
    
    def save(self, path: Optional[str] = None):
        """
        Save current configuration to file
        
        Args:
            path: Optional path to save config (defaults to original path)
        """
        save_path = path or self.config_path
        
        try:
            with open(save_path, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False, indent=2)
            self.logger.info(f"Configuration saved to {save_path}")
        except Exception as e:
            self.logger.error(f"Error saving configuration: {e}")
            raise


# Global configuration instance
_config_manager = None


def get_config_manager(config_path: str = "config.yaml") -> ConfigManager:
    """Get or create global configuration manager instance"""
    global _config_manager
    
    if _config_manager is None:
        _config_manager = ConfigManager(config_path)
        _config_manager.load()
    
    return _config_manager


def get_config() -> Dict[str, Any]:
    """Get loaded configuration dictionary"""
    return get_config_manager().config 