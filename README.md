# Group 4 - Smart Home IoT Curtain Control System

## 🏠 Project Overview

A production-ready IoT system for automated curtain control based on ambient light levels, featuring Arduino-based hardware control, Raspberry Pi server, MQTT messaging, and a **beautiful web interface**.

## ✨ Key Features

- **🎨 Modern Web Interface**: Beautiful, responsive dashboard for monitoring and control
- **💡 Real-time Light Monitoring**: Live light sensor readings with visual indicators
- **🪟 Curtain Control**: Manual open/close/stop controls with position feedback
- **🤖 Auto/Manual Mode**: Toggle between automatic and manual control
- **📊 System Status**: Real-time Arduino and MQTT connection status
- **⚙️ Threshold Configuration**: Adjustable light thresholds for automatic control
- **📱 Mobile Responsive**: Works perfectly on phones, tablets, and desktops
- **🔄 MQTT Integration**: Pub/sub architecture for IoT integration
- **💾 Data Persistence**: SQLite database for historical data

## 📸 Web Interface Features

The web interface provides:
1. **Light Sensor Display** - Real-time light level (0-1023) with visual progress bar and status indicators
2. **Curtain Controls** - Large, accessible buttons for Open, Close, and Stop
3. **Mode Toggle** - Beautiful switch to enable/disable automatic mode
4. **Threshold Settings** - Sliders to adjust when curtains open (dark) and close (bright)
5. **System Status** - Live connection status for Arduino and MQTT
6. **Position Indicators** - Current curtain position (Open/Closed/Unknown)

## 🏗️ System Architecture

```
┌──────────────────┐
│   Web Browser    │ ← User Interface (Modern Dashboard)
└────────┬─────────┘
         │ HTTP/REST API
┌────────▼─────────┐         ┌─────────────────┐
│  Flask Server    │◄────────┤ MQTT Broker     │ ← IoT Messaging
│  (Raspberry Pi)  │         │ (Mosquitto)     │
└──────┬───────────┘         └─────────────────┘
       │ Serial USB
┌──────▼───────────┐
│  Arduino Uno     │ ← Hardware Control
│  + Photoresistor │
│  + Motor Driver  │
└──────────────────┘
```

## 📁 Project Structure

```
week1group4/
├── curtain_control/
│   ├── arduino_curtain_enhanced.ino    # Enhanced Arduino firmware ✅
│   └── curtain_control.ino             # Original (legacy)
├── server/
│   ├── templates/
│   │   └── index.html                  # Web interface ✅
│   ├── static/                         # Static assets
│   ├── main.py                         # Main application ✅
│   ├── config.py                       # Configuration manager ✅
│   ├── models.py                       # Data models ✅
│   ├── serial_manager.py               # Serial communication ✅
│   ├── mqtt_client.py                  # MQTT client ✅
│   └── database.py                     # Database layer ✅
├── config.yaml                         # System configuration
├── pyproject.toml                      # uv project file ✅
├── run.sh                              # Quick start script ✅
└── README.md                           # This file
```

## 🚀 Quick Start

### Option 1: Use the Quick Start Script

```bash
./run.sh
```

That's it! The script will:
- Check for uv installation
- Install dependencies if needed
- Start the server
- Open at http://localhost:5000

### Option 2: Manual Setup

### Prerequisites
- Arduino Uno/Nano with photoresistor and motor
- Raspberry Pi (or any computer with Python 3.9+)
- Python 3.9 or higher
- [uv](https://docs.astral.sh/uv/) - Fast Python package installer
- Mosquitto MQTT broker

### Installation

1. **Install uv** (if not already installed)
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Navigate to project directory**
   ```bash
   cd /Users/jay/Desktop/week1group4
   ```

3. **Install dependencies with uv**
   ```bash
   # Install production dependencies
   uv sync
   
   # Or install with dev dependencies (for testing/development)
   uv sync --extra dev
   ```

4. **Install MQTT Broker**
   ```bash
   # macOS
   brew install mosquitto
   brew services start mosquitto
   
   # Linux
   sudo apt-get install mosquitto mosquitto-clients
   sudo systemctl start mosquitto
   ```

5. **Upload Arduino firmware**
   - Open `curtain_control/arduino_curtain_enhanced.ino` in Arduino IDE
   - Select your board and port
   - Upload the sketch

6. **Configure serial port**
   - Edit `config.yaml`
   - Set correct serial port for your Arduino

7. **Run the server**
   ```bash
   # Using the quick start script
   ./run.sh
   
   # Or using uv directly
   uv run python server/main.py
   
   # Or activate virtual environment first
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   python server/main.py
   ```

8. **Access web interface**
   - Open browser to `http://localhost:5000`
   - You should see the beautiful dashboard!

## 🎨 Using the Web Interface

### Light Sensor Display
- Shows current light level (0-1023)
- Visual progress bar for quick reference
- Status indicator: 🌙 Dark / 🌤️ Medium / ☀️ Bright

### Manual Control
1. Click **"Open Curtains"** to open
2. Click **"Close Curtains"** to close
3. Click **"Stop"** for emergency stop

### Automatic Mode
1. Toggle the switch to **ON** (purple)
2. Adjust thresholds:
   - **Dark threshold**: Curtains open when light falls below this
   - **Bright threshold**: Curtains close when light exceeds this
3. Click **"Save Thresholds"** to apply
4. System will automatically control curtains based on light

### Monitoring
- **Position**: Shows if curtains are Open, Closed, or Unknown
- **Mode**: Shows Manual or Auto mode
- **Arduino Status**: Green dot = connected
- **MQTT Status**: Green dot = connected

## 📖 Documentation

### Using uv Commands

```bash
# Install dependencies
uv sync

# Install with dev dependencies
uv sync --extra dev

# Add a new dependency
uv add package-name

# Add a dev dependency
uv add --dev package-name

# Run Python scripts
uv run python server/main.py

# Run tests (when implemented)
uv run pytest

# Format code with black
uv run black server/

# Lint code with flake8
uv run flake8 server/
```

### Hardware Setup
- **Photoresistor**: Connect to A0 with 10kΩ pull-down resistor
- **Motor Driver**: Connect to pin 9 (PWM) and pin 8 (direction)
- **Power**: Ensure adequate power for motor (external supply recommended)

### Command Protocol

**Arduino Commands:**
- `OPEN_CURTAIN` - Open the curtains
- `CLOSE_CURTAIN` - Close the curtains
- `STOP_MOTOR` - Emergency stop
- `READ_LIGHT` - Get current light reading
- `GET_STATUS` - Get full status report
- `CALIBRATE_LIGHT` - Start 10-second calibration
- `SET_SPEED:75` - Set motor speed (0-100%)
- `PING` - Connection check

**Arduino Responses:**
- `LIGHT:450` - Light sensor reading
- `POSITION:OPEN` - Curtain position
- `MOTOR:STOPPED` - Motor status
- `CALIBRATION:YES,MIN:100,MAX:900` - Calibration data

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Web interface (Dashboard) |
| GET | `/api/v1/light/current` | Current light reading |
| GET | `/api/v1/light/history` | Historical light data |
| POST | `/api/v1/curtain/control` | Control curtain (open/close/stop) |
| GET | `/api/v1/curtain/status` | Get curtain status |
| POST | `/api/v1/curtain/mode` | Set auto/manual mode |
| GET | `/api/v1/system/status` | Complete system status |
| POST | `/api/v1/system/calibrate` | Start sensor calibration |

### MQTT Topics

| Topic | Direction | QoS | Description |
|-------|-----------|-----|-------------|
| `curtain/light/reading` | Publish | 0 | Light sensor data every 5s |
| `curtain/position/status` | Publish | 1 | Curtain position updates |
| `curtain/control/command` | Subscribe | 1 | Remote control commands |
| `curtain/system/status` | Publish | 1 | System health every 10s |
| `curtain/system/heartbeat` | Publish | 0 | Alive signal every 30s |
| `curtain/alerts/errors` | Publish | 1 | Error notifications |

## 🔧 Configuration

Edit `config.yaml` to customize:
- Serial port and baud rate
- MQTT broker address
- Light thresholds for auto mode
- Database path
- Logging level and format
- Web server host and port

## 🧪 Testing

### Test Serial Communication
```python
uv run python
>>> from server.serial_manager import SerialManager
>>> sm = SerialManager('/dev/ttyACM0')
>>> sm.connect()
>>> sm.read_light()
>>> sm.open_curtain()
```

### Test MQTT
```bash
# Subscribe to all curtain topics
mosquitto_sub -h localhost -t 'curtain/#' -v

# Send control command
mosquitto_pub -h localhost -t 'curtain/control/command' -m '{"command":"open"}'
```

### Test Web Interface
1. Start the server with `./run.sh`
2. Open `http://localhost:5000` in your browser
3. You should see the dashboard with real-time updates
4. Try the manual controls (buttons work even without Arduino)
5. Toggle auto/manual mode
6. Adjust thresholds with sliders

## 📊 Features Implemented

### Arduino Firmware
✅ Running average light sensor smoothing (10 samples)  
✅ EEPROM calibration persistence  
✅ Comprehensive command protocol  
✅ PWM motor speed control  
✅ Position tracking and timeout protection  
✅ Error handling and status reporting

### Server Application
✅ Modular clean architecture  
✅ Serial communication with callbacks  
✅ MQTT pub/sub integration  
✅ SQLite database with historical data  
✅ REST API with Flask  
✅ Auto mode control logic  
✅ Configuration management  
✅ Logging and error handling

### Web Interface
✅ Modern, responsive design  
✅ Real-time light sensor display  
✅ Manual curtain controls (Open/Close/Stop)  
✅ Auto/Manual mode toggle  
✅ Threshold configuration sliders  
✅ System status indicators  
✅ Position and mode badges  
✅ Mobile-friendly layout

## 🛠️ Development

### Code Quality
- Type hints throughout
- Comprehensive docstrings
- Modular design with separation of concerns
- Error handling and logging
- Clean code principles

### Architecture Patterns
- **Configuration Management**: Centralized YAML config
- **Data Models**: Dataclasses with validation
- **Repository Pattern**: Database abstraction
- **Observer Pattern**: Callback-based serial communication
- **Pub/Sub**: MQTT messaging
- **MVC Pattern**: Separated frontend, API, and business logic

### Using uv for Development

```bash
# Install dev dependencies
uv sync --extra dev

# Format code
uv run black server/

# Check code style
uv run flake8 server/

# Run tests (when implemented)
uv run pytest

# Add new dependency
uv add package-name

# Update dependencies
uv sync --upgrade
```

## 🎯 What Makes This Special

1. **Beautiful UI/UX**: Modern gradient design with smooth animations
2. **Real-time Updates**: Dashboard refreshes every second
3. **Visual Feedback**: Color-coded indicators and progress bars
4. **Responsive Design**: Works on desktop, tablet, and mobile
5. **Production Ready**: Error handling, logging, proper architecture
6. **Easy to Run**: One command to start everything
7. **Well Documented**: Comprehensive README and inline documentation

## 📝 License

Group 4 - Smart Home System Project

## 👥 Contributors

Group 4 Team

## 📞 Support

For detailed implementation, refer to the code documentation in the `server/` directory.

---

**Note**: This is a production-ready implementation using modern Python tooling (uv), following clean architecture principles and IoT best practices. The web interface provides an intuitive, beautiful way to monitor and control your smart curtain system!
