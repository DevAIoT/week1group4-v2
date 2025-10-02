"""
MQTT Client Module
Handles pub/sub messaging with MQTT broker
"""

import paho.mqtt.client as mqtt
import json
import logging
import threading
from datetime import datetime
from typing import Dict, Callable, Optional

from models import MQTTStatus


class MQTTClient:
    """MQTT client for publishing sensor data and receiving commands"""
    
    def __init__(self, broker: str, port: int, client_id: str, topics: Dict[str, str],
                 username: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize MQTT client
        
        Args:
            broker: MQTT broker address
            port: MQTT broker port
            client_id: Unique client identifier
            topics: Dictionary of topic names
            username: Optional MQTT username
            password: Optional MQTT password
        """
        self.broker = broker
        self.port = port
        self.client_id = client_id
        self.topics = topics
        self.logger = logging.getLogger(__name__)
        
        # Create MQTT client
        self.client = mqtt.Client(client_id=client_id)
        self.status = MQTTStatus(broker=f"{broker}:{port}")
        self.callbacks: Dict[str, Callable] = {}
        
        # Set credentials if provided
        if username and password:
            self.client.username_pw_set(username, password)
        
        # Set callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        
    def connect(self) -> bool:
        """
        Connect to MQTT broker
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.logger.info(f"Connecting to MQTT broker at {self.broker}:{self.port}")
            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_start()
            return True
        except Exception as e:
            self.logger.error(f"MQTT connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from MQTT broker"""
        self.client.loop_stop()
        self.client.disconnect()
        self.status.connected = False
        self.logger.info("Disconnected from MQTT broker")
    
    def publish_light_reading(self, light_data: dict):
        """Publish light sensor reading"""
        topic = self.topics.get('light_reading', 'curtain/light/reading')
        payload = json.dumps(light_data)
        self.client.publish(topic, payload, qos=0)
        self.status.messages_sent += 1
        self.status.last_publish = datetime.now()
        self.logger.debug(f"Published light reading: {light_data}")
    
    def publish_position_status(self, position: str):
        """Publish curtain position update"""
        topic = self.topics.get('position_status', 'curtain/position/status')
        payload = json.dumps({
            'position': position,
            'timestamp': datetime.now().isoformat()
        })
        self.client.publish(topic, payload, qos=1)
        self.status.messages_sent += 1
        self.status.last_publish = datetime.now()
        self.logger.info(f"Published position: {position}")
    
    def publish_system_status(self, status_data: dict):
        """Publish system status"""
        topic = self.topics.get('system_status', 'curtain/system/status')
        payload = json.dumps(status_data)
        self.client.publish(topic, payload, qos=1)
        self.status.messages_sent += 1
        self.status.last_publish = datetime.now()
    
    def publish_heartbeat(self):
        """Publish heartbeat message"""
        topic = self.topics.get('heartbeat', 'curtain/system/heartbeat')
        payload = json.dumps({
            'timestamp': datetime.now().isoformat(),
            'status': 'alive'
        })
        self.client.publish(topic, payload, qos=0)
        self.logger.debug("Published heartbeat")
    
    def publish_error(self, error_message: str, error_type: str = "error"):
        """Publish error notification"""
        topic = self.topics.get('alerts', 'curtain/alerts/errors')
        payload = json.dumps({
            'timestamp': datetime.now().isoformat(),
            'error_type': error_type,
            'message': error_message
        })
        self.client.publish(topic, payload, qos=1)
        self.logger.warning(f"Published error: {error_message}")
    
    def subscribe_control_commands(self, callback: Callable):
        """
        Subscribe to control command topic
        
        Args:
            callback: Function to call when command received
        """
        topic = self.topics.get('control_command', 'curtain/control/command')
        self.callbacks[topic] = callback
        self.client.subscribe(topic, qos=1)
        self.logger.info(f"Subscribed to control commands on {topic}")
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback when connected to broker"""
        if rc == 0:
            self.logger.info("Connected to MQTT broker successfully")
            self.status.connected = True
            
            # Resubscribe to topics after reconnect
            for topic in self.callbacks.keys():
                self.client.subscribe(topic, qos=1)
                self.logger.info(f"Resubscribed to {topic}")
        else:
            self.logger.error(f"MQTT connection failed with code {rc}")
            self.status.connected = False
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback when disconnected from broker"""
        self.status.connected = False
        if rc != 0:
            self.logger.warning(f"Unexpected MQTT disconnect (code {rc})")
        else:
            self.logger.info("MQTT disconnected normally")
    
    def _on_message(self, client, userdata, msg):
        """Callback when message received"""
        try:
            payload = json.loads(msg.payload.decode())
            self.logger.debug(f"Received message on {msg.topic}: {payload}")
            
            if msg.topic in self.callbacks:
                self.callbacks[msg.topic](payload)
            
            self.status.messages_received += 1
            self.status.last_message = datetime.now()
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in MQTT message: {e}")
        except Exception as e:
            self.logger.error(f"Error processing MQTT message: {e}")
    
    def get_status(self) -> MQTTStatus:
        """Get current MQTT connection status"""
        return self.status
    
    def is_connected(self) -> bool:
        """Check if connected to broker"""
        return self.status.connected 