"""
Main Application Module
Integrates all components and starts the curtain control system
"""

import logging
from logging.handlers import RotatingFileHandler
import sys
import os
import threading
import time
from datetime import datetime

# Add parent directory to path to import server modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, jsonify, request
from flask_cors import CORS

from config import get_config_manager
from models import *
from serial_manager import SerialManager
from mqtt_client import MQTTClient
from database import Database

# Initialize Flask app
app = Flask(__name__)

# Global components
config_manager = None
config = None
serial_mgr = None
mqtt_client = None
db = None
system_status = None
latest_light_value = 0


def setup_logging():
    """Configure logging system"""
    global config
    
    log_config = config.get('logging', {})
    level_name = log_config.get('level', 'INFO')
    level = getattr(logging, level_name, logging.INFO)
    format_str = log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Basic config
    logging.basicConfig(level=level, format=format_str)
    
    # File handler
    if 'file' in log_config:
        try:
            log_file = log_config['file']
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            
            handler = RotatingFileHandler(
                log_file,
                maxBytes=log_config.get('max_bytes', 10485760),
                backupCount=log_config.get('backup_count', 5)
            )
            handler.setFormatter(logging.Formatter(format_str))
            logging.getLogger().addHandler(handler)
            
            logging.info(f"Logging to file: {log_file}")
        except Exception as e:
            logging.error(f"Failed to setup file logging: {e}")


def setup_components():
    """Initialize all system components"""
    global serial_mgr, mqtt_client, db, system_status, config
    
    logger = logging.getLogger(__name__)
    logger.info("Initializing system components...")
    
    # Initialize system status
    system_status = SystemStatus()
    
    # Setup database
    try:
        db_path = config['database']['path']
        db = Database(db_path)
        logger.info(f"Database initialized: {db_path}")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        db = None
    
    # Setup serial communication
    try:
        serial_config = config['serial']
        serial_mgr = SerialManager(
            port=serial_config['port'],
            baudrate=serial_config['baudrate'],
            timeout=serial_config['timeout']
        )
        
        # Register callbacks
        serial_mgr.register_callback('LIGHT', on_light_reading)
        serial_mgr.register_callback('POSITION', on_position_update)
        serial_mgr.register_callback('MOTOR', on_motor_status)
        serial_mgr.register_callback('MODE', on_mode_update)
        serial_mgr.register_callback('ERROR', on_arduino_error)
        
        # Attempt connection
        if serial_mgr.connect():
            system_status.arduino = serial_mgr.get_arduino_status()
            logger.info("Arduino connected successfully")
            
            # Initialize Arduino to manual mode to sync with server default
            # Wait longer to ensure Arduino has fully booted and processed initial messages
            time.sleep(1.5)  # Increased delay for Arduino initialization
            serial_mgr.send_command("MANUAL_MODE")
            time.sleep(0.3)  # Wait for response
            logger.info("Initialized Arduino to MANUAL mode")
        else:
            logger.warning("Arduino connection failed - running without hardware")
            
    except Exception as e:
        logger.error(f"Serial manager initialization failed: {e}")
        serial_mgr = None
    
    # Setup MQTT client
    try:
        mqtt_config = config['mqtt']
        mqtt_client = MQTTClient(
            broker=mqtt_config['broker'],
            port=mqtt_config['port'],
            client_id=mqtt_config['client_id'],
            topics=mqtt_config['topics'],
            username=mqtt_config.get('username'),
            password=mqtt_config.get('password')
        )
        
        if mqtt_client.connect():
            mqtt_client.subscribe_control_commands(on_mqtt_command)
            system_status.mqtt = mqtt_client.get_status()
            logger.info("MQTT connected successfully")
        else:
            logger.warning("MQTT connection failed")
            
    except Exception as e:
        logger.error(f"MQTT client initialization failed: {e}")
        mqtt_client = None
    
    # Start background threads
    threading.Thread(target=mqtt_publish_loop, daemon=True, name="MQTT-Publisher").start()
    threading.Thread(target=auto_mode_loop, daemon=True, name="Auto-Mode").start()
    threading.Thread(target=heartbeat_loop, daemon=True, name="Heartbeat").start()
    
    logger.info("All components initialized")


# Callback handlers

def on_light_reading(value: int):
    """Handle light sensor reading from Arduino"""
    global latest_light_value, system_status, db
    
    latest_light_value = value
    
    # Update system status
    if system_status:
        system_status.latest_light = LightReading(
            timestamp=datetime.now(),
            raw_value=value
        )
    
    # Save to database
    if db:
        try:
            db.insert_light_reading(value)
        except Exception as e:
            logging.error(f"Failed to save light reading: {e}")


def on_position_update(position: str):
    """Handle curtain position update"""
    global system_status, mqtt_client
    
    try:
        if system_status:
            system_status.curtain.position = CurtainPosition(position)
            
        # Publish to MQTT
        if mqtt_client and mqtt_client.is_connected():
            mqtt_client.publish_position_status(position)
            
        logging.info(f"Curtain position updated: {position}")
    except Exception as e:
        logging.error(f"Error handling position update: {e}")


def on_motor_status(status: str):
    """Handle motor status update"""
    global system_status
    
    try:
        if system_status:
            system_status.curtain.motor_state = MotorState(status)
        logging.info(f"Motor status updated: {status}")
    except Exception as e:
        logging.error(f"Error handling motor status: {e}")


def on_mode_update(mode: str):
    """Handle mode update from Arduino"""
    global system_status
    
    try:
        mode_lower = mode.lower()
        logging.info(f"Received MODE update from Arduino: '{mode_lower}'")
        
        if system_status:
            # Update both the settings and curtain mode
            system_status.settings.auto_mode_enabled = (mode_lower == 'auto')
            system_status.curtain.mode = SystemMode(mode_lower)
            logging.info(f"✓ System status updated: mode={mode_lower}, auto_enabled={system_status.settings.auto_mode_enabled}")
        else:
            logging.warning("System status not initialized, cannot update mode")
            
    except Exception as e:
        logging.error(f"Error handling mode update: {e}", exc_info=True)


def on_arduino_error(error_msg: str):
    """Handle error from Arduino"""
    logging.error(f"Arduino error: {error_msg}")
    
    if db:
        try:
            db.log_error('arduino_error', error_msg, 'arduino')
        except Exception as e:
            logging.error(f"Failed to log Arduino error: {e}")
    
    if mqtt_client and mqtt_client.is_connected():
        mqtt_client.publish_error(error_msg, 'arduino')


def on_mqtt_command(payload: dict):
    """Handle MQTT control command"""
    global serial_mgr, db, latest_light_value
    
    command = payload.get('command', '').lower()
    logging.info(f"Received MQTT command: {command}")
    
    if not serial_mgr or not serial_mgr.is_connected():
        logging.warning("Cannot execute command: Arduino not connected")
        return
    
    try:
        if command == 'open':
            serial_mgr.open_curtain()
            if db:
                db.log_operation('open', 'mqtt', latest_light_value)
        elif command == 'close':
            serial_mgr.close_curtain()
            if db:
                db.log_operation('close', 'mqtt', latest_light_value)
        elif command == 'stop':
            serial_mgr.stop_motor()
        elif command == 'calibrate':
            serial_mgr.calibrate_light()
        else:
            logging.warning(f"Unknown MQTT command: {command}")
    except Exception as e:
        logging.error(f"Error executing MQTT command: {e}")


# Background loops

def mqtt_publish_loop():
    """Background thread to publish data to MQTT"""
    global mqtt_client, latest_light_value, config
    
    logger = logging.getLogger('mqtt_publisher')
    interval = config['mqtt']['publish_interval']['light']
    
    while True:
        try:
            time.sleep(interval)
            
            if mqtt_client and mqtt_client.is_connected() and latest_light_value > 0:
                mqtt_client.publish_light_reading({
                    'value': latest_light_value,
                    'timestamp': datetime.now().isoformat()
                })
        except Exception as e:
            logger.error(f"MQTT publish error: {e}")


def auto_mode_loop():
    """Background thread for automatic curtain control"""
    global system_status, serial_mgr, config, db, latest_light_value
    
    logger = logging.getLogger('auto_mode')
    last_action_time = 0
    min_interval = 60  # Minimum 60 seconds between actions
    
    while True:
        try:
            time.sleep(5)
            
            if not system_status or not system_status.settings.auto_mode_enabled:
                continue
            
            if not serial_mgr or not serial_mgr.is_connected():
                continue
            
            # Check if enough time has passed since last action
            if time.time() - last_action_time < min_interval:
                continue
            
            thresholds = config['curtain']['thresholds']
            open_threshold = thresholds['dark']
            close_threshold = thresholds['bright']
            
            current_position = system_status.curtain.position
            
            # In auto mode, Arduino handles the continuous motor control
            # Server just logs the activity
            if latest_light_value < open_threshold:
                if current_position != CurtainPosition.OPEN:
                    logger.info(f"Auto mode: Curtain opening (light: {latest_light_value})")
                    if db:
                        db.log_operation('auto_opening', 'auto_dark', latest_light_value)
                    last_action_time = time.time()
            
            elif latest_light_value > close_threshold:
                if current_position != CurtainPosition.CLOSED:
                    logger.info(f"Auto mode: Curtain closing (light: {latest_light_value})")
                    if db:
                        db.log_operation('auto_closing', 'auto_bright', latest_light_value)
                    last_action_time = time.time()
                    
        except Exception as e:
            logger.error(f"Auto mode error: {e}")


def heartbeat_loop():
    """Background thread to send heartbeat messages"""
    global mqtt_client, config
    
    interval = config['mqtt']['publish_interval']['heartbeat']
    
    while True:
        try:
            time.sleep(interval)
            
            if mqtt_client and mqtt_client.is_connected():
                mqtt_client.publish_heartbeat()
        except Exception as e:
            logging.error(f"Heartbeat error: {e}")


# REST API Endpoints

@app.route('/')
def index():
    """Serve the web interface"""
    from flask import render_template
    return render_template('index.html')


@app.route('/api/v1/light/current')
def get_current_light():
    """Get current light reading"""
    return jsonify({
        'value': latest_light_value,
        'timestamp': datetime.now().isoformat(),
        'unit': 'analog (0-1023)'
    })


@app.route('/api/v1/light/history')
def get_light_history():
    """Get historical light readings"""
    hours = request.args.get('hours', default=24, type=int)
    
    if db:
        readings = db.get_recent_light_readings(hours=hours)
        return jsonify({'readings': readings, 'count': len(readings)})
    else:
        return jsonify({'error': 'Database not available'}), 503


@app.route('/api/v1/curtain/control', methods=['POST'])
def control_curtain():
    """Control curtain (open/close/stop)"""
    data = request.json
    action = data.get('action', '').lower()
    
    if not serial_mgr or not serial_mgr.is_connected():
        return jsonify({'error': 'Arduino not connected'}), 503
    
    try:
        if action == 'open':
            serial_mgr.open_curtain()
            if db:
                db.log_operation('open', 'api', latest_light_value)
            return jsonify({'status': 'success', 'action': 'open'})
        
        elif action == 'close':
            serial_mgr.close_curtain()
            if db:
                db.log_operation('close', 'api', latest_light_value)
            return jsonify({'status': 'success', 'action': 'close'})
        
        elif action == 'stop':
            serial_mgr.stop_motor()
            return jsonify({'status': 'success', 'action': 'stop'})
        
        else:
            return jsonify({'error': 'Invalid action'}), 400
            
    except Exception as e:
        logging.error(f"Control error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/curtain/status')
def get_curtain_status():
    """Get curtain status"""
    if system_status:
        return jsonify(system_status.curtain.to_dict())
    else:
        return jsonify({'error': 'Status not available'}), 503


@app.route('/api/v1/curtain/mode', methods=['POST'])
def set_mode():
    """Set curtain mode (auto/manual)"""
    data = request.json
    mode = data.get('mode', '').lower()
    
    if mode not in ['auto', 'manual']:
        return jsonify({'error': 'Invalid mode'}), 400
    
    if not serial_mgr or not serial_mgr.is_connected():
        return jsonify({'error': 'Arduino not connected'}), 503
    
    try:
        # Send command to Arduino
        if mode == 'auto':
            serial_mgr.send_command("AUTO_MODE")
        else:
            serial_mgr.send_command("MANUAL_MODE")
        
        # Wait briefly for Arduino to process and respond
        time.sleep(0.2)
        
        # System status will be updated by the on_mode_update callback
        # when Arduino responds with MODE:AUTO or MODE:MANUAL
        
        # Verify the mode was set correctly by checking system status
        if system_status:
            actual_mode = system_status.curtain.mode.value
            if actual_mode == mode:
                logger.info(f"Mode successfully changed to {mode}")
                return jsonify({'status': 'success', 'mode': mode})
            else:
                logger.warning(f"Mode change requested to {mode} but Arduino is in {actual_mode}")
                return jsonify({'status': 'warning', 'requested': mode, 'actual': actual_mode})
        
        return jsonify({'status': 'success', 'mode': mode})
        
    except Exception as e:
        logging.error(f"Error setting mode: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/system/status')
def get_system_status():
    """Get complete system status"""
    if system_status:
        return jsonify(system_status.to_dict())
    else:
        return jsonify({'error': 'Status not available'}), 503


@app.route('/api/v1/system/calibrate', methods=['POST'])
def calibrate():
    """Start light sensor calibration"""
    if not serial_mgr or not serial_mgr.is_connected():
        return jsonify({'error': 'Arduino not connected'}), 503
    
    try:
        serial_mgr.calibrate_light()
        return jsonify({'status': 'Calibration started', 'duration': '10 seconds'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/curtain/thresholds', methods=['GET'])
def get_thresholds():
    """Get current light thresholds"""
    return jsonify({
        'dark_threshold': config['curtain']['thresholds']['dark'],
        'bright_threshold': config['curtain']['thresholds']['bright']
    })


@app.route('/api/v1/curtain/thresholds', methods=['POST'])
def set_thresholds():
    """Set light thresholds"""
    data = request.json
    
    try:
        arduino_connected = serial_mgr and serial_mgr.is_connected()
        
        if 'dark_threshold' in data:
            dark_threshold = int(data['dark_threshold'])
            if 0 <= dark_threshold <= 1023:
                config['curtain']['thresholds']['dark'] = dark_threshold
                # Send to Arduino if connected
                if arduino_connected:
                    serial_mgr.send_command("SET_OPEN_THRESHOLD", str(dark_threshold))
        
        if 'bright_threshold' in data:
            bright_threshold = int(data['bright_threshold'])
            if 0 <= bright_threshold <= 1023:
                config['curtain']['thresholds']['bright'] = bright_threshold
                # Send to Arduino if connected
                if arduino_connected:
                    serial_mgr.send_command("SET_CLOSE_THRESHOLD", str(bright_threshold))
        
        response_data = {
            'status': 'success',
            'dark_threshold': config['curtain']['thresholds']['dark'],
            'bright_threshold': config['curtain']['thresholds']['bright']
        }
        
        if not arduino_connected:
            response_data['warning'] = 'Thresholds saved locally but not sent to Arduino (disconnected)'
        
        return jsonify(response_data)
        
    except (ValueError, KeyError) as e:
        return jsonify({'error': 'Invalid threshold values'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Main entry point

def main():
    """Main application entry point"""
    global config_manager, config
    
    print("=" * 60)
    print("IoT Curtain Control System v2.0")
    print("=" * 60)
    
    # Load configuration
    config_manager = get_config_manager()
    config = config_manager.config
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting IoT Curtain Control System")
    
    # Initialize components
    setup_components()
    
    # Enable CORS if configured
    if config['server'].get('cors_enabled', True):
        CORS(app)
        logger.info("CORS enabled")
    
    # Start Flask server
    host = config['server']['host']
    port = config['server']['port']
    debug = config['server']['debug']
    
    logger.info(f"Starting web server on {host}:{port}")
    print(f"\n🚀 Server starting on http://{host}:{port}")
    print(f"📡 MQTT: {config['mqtt']['broker']}:{config['mqtt']['port']}")
    print(f"🔌 Arduino: {config['serial']['port']}")
    print("=" * 60)
    
    try:
        app.run(host=host, port=port, debug=debug)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        if serial_mgr:
            serial_mgr.disconnect()
        if mqtt_client:
            mqtt_client.disconnect()
        print("\n👋 Goodbye!")


if __name__ == '__main__':
    main() 