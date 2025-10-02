# 🏗️ IoT Curtain Control System - Complete Setup Guide

## 📋 Overview

This guide provides step-by-step instructions to set up your IoT Curtain Control System from hardware assembly to software configuration. The system consists of:

- **Arduino Uno/Nano** (Hardware controller)
- **Photoresistor** (Light sensor)
- **DC Motor + Motor Driver** (Curtain control)
- **Raspberry Pi** (Server)
- **MQTT Broker** (Messaging)
- **Web Interface** (User control)

## 🛒 Hardware Requirements

### Required Components

| Component | Description | Estimated Cost | Where to Buy |
|-----------|-------------|----------------|-------------|
| Arduino Uno | Microcontroller board | $20-25 | Amazon, AliExpress |
| Photoresistor | Light-dependent resistor (LDR) | $2-5 | Amazon, Electronics stores |
| 10kΩ Resistor | Pull-down resistor for photoresistor | $1 | Electronics stores |
| L293D Motor Driver | Dual H-bridge motor driver IC | $2-4 | Amazon, AliExpress |
| DC Motor | Small 5-12V DC motor for curtains | $5-10 | Amazon, Robotics stores |
| Jumper Wires | Male-to-male, male-to-female | $5-8 | Amazon, Electronics stores |
| Breadboard | For prototyping | $5 | Amazon, Electronics stores |
| USB Cable | Type B for Arduino | Included with Arduino | - |

### Optional/Recommended

| Component | Description | Why |
|-----------|-------------|-----|
| Raspberry Pi 4 | 4GB RAM model recommended | Server hosting |
| SD Card | 32GB minimum, Class 10 | Raspberry Pi OS |
| Power Supply | 5V/3A for Raspberry Pi | Stable power |
| Ethernet Cable | For Raspberry Pi networking | Reliable connection |
| Heat Sinks | For Raspberry Pi | Prevent overheating |

## 🔧 Arduino Setup

### Step 1: Install Arduino IDE

1. **Download Arduino IDE**
   - Visit: https://www.arduino.cc/en/software
   - Download for your operating system (Windows/Mac/Linux)

2. **Install Arduino IDE**
   - Run the installer
   - Follow setup wizard

### Step 2: Upload Firmware

1. **Open Arduino IDE**
2. **Load the firmware**
   ```bash
   # Navigate to project directory
   cd /Users/jay/Desktop/week1group4
   
   # Open the Arduino code in IDE
   # File > Open > curtain_control/arduino_curtain_enhanced.ino
   ```

3. **Configure Board**
   - **Tools > Board > Arduino AVR Boards > Arduino Uno**
   - **Tools > Port > Select your Arduino's port**

4. **Upload Code**
   - Click the **Upload** button (→ arrow)
   - Wait for "Done uploading" message
   - Arduino will restart with new firmware

### Step 3: Test Arduino Connection

1. **Open Serial Monitor**
   - **Tools > Serial Monitor**
   - Set baud rate to **115200**

2. **Verify Output**
   You should see:
   ```
   READY:Arduino Curtain Control v2.0
   CALIBRATION:NO,MIN:50,MAX:950
   LIGHT:450
   LIGHT:448
   LIGHT:451
   ...
   ```

## 🖥️ Raspberry Pi Setup

### Step 1: Install Raspberry Pi OS

1. **Download Raspberry Pi Imager**
   - Visit: https://www.raspberrypi.com/software/
   - Download for your OS

2. **Prepare SD Card**
   - Insert SD card into computer
   - Open Raspberry Pi Imager
   - Choose OS: **Raspberry Pi OS (64-bit)**
   - Choose Storage: Your SD card
   - Click **Write**

3. **First Boot**
   - Insert SD card into Raspberry Pi
   - Connect HDMI monitor, keyboard, mouse
   - Connect power cable
   - Follow setup wizard

4. **Update System**
   ```bash
   sudo apt update
   sudo apt upgrade -y
   ```

### Step 2: Install uv (Python Package Manager)

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add to PATH (if needed)
echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Verify installation
uv --version
```

### Step 3: Install MQTT Broker (Mosquitto)

```bash
# Install Mosquitto
sudo apt install mosquitto mosquitto-clients -y

# Start and enable service
sudo systemctl start mosquitto
sudo systemctl enable mosquitto

# Test MQTT
mosquitto -v  # Should show version
```

### Step 4: Install Project Dependencies

```bash
# Navigate to project directory
cd /Users/jay/Desktop/week1group4

# Install dependencies with uv
uv sync

# Verify installation
uv run python --version
```

### Step 5: Configure Serial Port

1. **Find Arduino port**
   ```bash
   # List connected devices
   ls /dev/tty*
   
   # Common Arduino ports:
   # - /dev/ttyACM0 (Linux)
   # - /dev/ttyUSB0 (Linux, some boards)
   # - /dev/tty.usbmodem* (macOS)
   # - COM3 (Windows)
   ```

2. **Update config.yaml**
   ```yaml
   serial:
     port: "/dev/ttyACM0"  # Change to your actual port
   ```

3. **Set permissions (if needed)**
   ```bash
   sudo usermod -a -G dialout $USER
   sudo usermod -a -G tty $USER
   ```

## 🔌 Hardware Wiring

### Arduino Pinout Reference

```
Arduino Uno Pin Layout:
┌─────────────────┐
│       USB       │ ← Connect to Raspberry Pi
│                 │
│   13 12 11 10  │ ← Digital pins
│   9  8  7  6   │ ← Motor control pins
│   5  4  3  2   │
│   A0 A1 A2 A3  │ ← Analog pins (A0 = light sensor)
│   A4 A5         │
│   GND 5V        │ ← Power pins
└─────────────────┘
```

### Photoresistor Circuit (Light Sensor)

**Components Needed:**
- Photoresistor (LDR)
- 10kΩ resistor
- Jumper wires

**Wiring Diagram:**
```
Arduino A0 ───┬─── Photoresistor ───┬─── GND
              │                     │
              └─── 10kΩ Resistor ───┘
```

**Step-by-step:**
1. Connect Arduino **GND** to breadboard ground rail
2. Connect Arduino **5V** to breadboard power rail
3. Connect **10kΩ resistor** between ground rail and one leg of photoresistor
4. Connect **A0 pin** to the junction between resistor and photoresistor
5. Connect other leg of photoresistor to **5V rail**

### Motor Control Circuit (L293D Motor Driver)

**Components Needed:**
- L293D motor driver IC
- DC motor (5-12V)
- External power supply (for motor)

**L293D Pinout:**
```
┌─────────────────┐
│ 1  2  3  4  5  │ ← Enable and Input pins
│ 6  7  8  9 10  │
│11 12 13 14 15  │ ← Motor outputs
│16     GND      │
└─────────────────┘
```

**Wiring Diagram:**
```
Arduino:
- Pin 9 (PWM) ─── L293D Pin 1 (Enable 1,2)
- Pin 8 ───────── L293D Pin 2 (Input 1)
- GND ─────────── L293D Pin 4,5 (GND)
- 5V ──────────── L293D Pin 16 (VCC)

L293D Motor Outputs:
- Pin 3 ─── DC Motor Wire 1
- Pin 6 ─── DC Motor Wire 2

Power:
- External 12V ── L293D Pin 8 (Motor Power)
- External GND ── L293D Pin 4,5 (GND)
```

**Important Notes:**
- **NEVER connect motor directly to Arduino pins** - use motor driver
- **Use external power supply for motor** (Arduino can't supply enough current)
- **Connect Arduino GND to motor driver GND** (common ground)

### Complete Wiring Summary

```
┌─────────────────┐
│   Arduino Uno   │
├─────────────────┤
│ 5V ───┬────────┐ │
│       │        │ │
│ A0 ───┼── LDR ─┼─┘ Photoresistor
│       │        │
│ GND ──┼── 10kΩ─┘
│       │
│ Pin 8 ─── L293D Pin 2 (Direction)
│ Pin 9 ─── L293D Pin 1 (PWM Enable)
│ 5V ───── L293D Pin 16 (Logic Power)
│ GND ──── L293D Pin 4,5 (GND)
│         L293D Pin 8 ← External 12V (Motor Power)
│         L293D Pin 3 ─── Motor Wire 1
│         L293D Pin 6 ─── Motor Wire 2
└─────────────────┘
```

## ⚙️ Software Configuration

### Step 1: Configure Serial Port

Edit `config.yaml`:
```yaml
serial:
  port: "/dev/ttyACM0"  # Update to your actual port
  baudrate: 115200
  timeout: 2
```

### Step 2: Configure MQTT (Optional)

```yaml
mqtt:
  broker: "localhost"  # Use "localhost" for local broker
  port: 1883
```

### Step 3: Adjust Thresholds

```yaml
curtain:
  thresholds:
    dark: 300    # Curtains open when light < 300
    bright: 700  # Curtains close when light > 700
```

## 🚀 Running the System

### Step 1: Start the Server

```bash
cd /Users/jay/Desktop/week1group4

# Method 1: Using uv
uv run python server/main.py

# Method 2: Using virtual environment
source .venv/bin/activate
python server/main.py
```

### Step 2: Verify Connections

1. **Check Serial Connection**
   - Arduino should connect automatically
   - Check logs for "Connected to Arduino"

2. **Check MQTT Connection**
   - MQTT should connect automatically
   - Check logs for "Connected to MQTT broker"

3. **Open Web Interface**
   - Go to: http://localhost:5000
   - You should see the dashboard

### Step 3: Test Functionality

1. **Manual Control**
   - Click "Open Curtains" button
   - Motor should turn on briefly
   - Position should update

2. **Light Sensor**
   - Cover photoresistor with hand
   - Light value should decrease
   - Uncover to see increase

3. **Auto Mode**
   - Toggle to "Auto" mode
   - Cover sensor (light < 300) → curtains should open
   - Expose sensor (light > 700) → curtains should close

## 🧪 Testing Procedures

### Test 1: Arduino Communication

```bash
# On Raspberry Pi, test serial connection
python3
>>> from server.serial_manager import SerialManager
>>> sm = SerialManager('/dev/ttyACM0')
>>> sm.connect()
>>> sm.read_light()
>>> sm.open_curtain()
```

### Test 2: MQTT Communication

```bash
# Subscribe to MQTT topics
mosquitto_sub -h localhost -t 'curtain/#' -v

# In another terminal, publish test command
mosquitto_pub -h localhost -t 'curtain/control/command' -m '{"command":"open"}'
```

### Test 3: Web Interface

1. Open browser to http://localhost:5000
2. Check that light sensor shows values
3. Click buttons and verify they work
4. Toggle auto mode and test thresholds

## 🔍 Troubleshooting

### Common Issues

**Problem:** Arduino not detected
```
Solution:
1. Check USB cable connection
2. Verify Arduino has power (ON light)
3. Check port in config.yaml
4. Run: ls /dev/tty* to see available ports
```

**Problem:** Light sensor shows constant value
```
Solution:
1. Check photoresistor wiring
2. Verify 10kΩ resistor is connected
3. Test with multimeter for resistance change
4. Check A0 pin connection
```

**Problem:** Motor doesn't move
```
Solution:
1. Verify motor driver connections
2. Check external power supply
3. Test motor with direct power
4. Verify pin 9 and 8 connections
```

**Problem:** Web interface shows "Disconnected"
```
Solution:
1. Check server logs: uv run python server/main.py
2. Verify Arduino connection in logs
3. Check MQTT broker status: systemctl status mosquitto
4. Restart server if needed
```

**Problem:** Auto mode doesn't work
```
Solution:
1. Check light thresholds in config.yaml
2. Verify light sensor is reading correctly
3. Check server logs for auto mode activity
4. Test manual controls first
```

## 📊 System Verification

### Check System Status

1. **View Logs**
   ```bash
   # Check server logs
   tail -f logs/curtain_control.log
   
   # Check MQTT logs
   mosquitto_sub -h localhost -t 'curtain/#' -v
   ```

2. **Database Verification**
   ```bash
   # Check if database has data
   uv run python -c "
   from server.database import Database
   db = Database('curtain_control.db')
   readings = db.get_recent_light_readings(hours=1)
   print(f'Found {len(readings)} light readings')
   "
   ```

3. **Hardware Test**
   ```python
   # Test all components
   from server.serial_manager import SerialManager
   sm = SerialManager('/dev/ttyACM0')
   sm.connect()
   print(f'Light: {sm.read_light()}')
   sm.open_curtain()
   sm.close_curtain()
   ```

## ⚠️ Safety Notes

1. **Motor Power**: Always use external power supply for motors
2. **Heat Management**: Monitor Raspberry Pi temperature during operation
3. **Power Cycling**: If system becomes unresponsive, power cycle both devices
4. **Emergency Stop**: Use the "Stop" button in web interface for emergencies
5. **Backups**: Keep backups of configuration files

## 📚 Additional Resources

- **Arduino Documentation**: https://www.arduino.cc/reference
- **Raspberry Pi Setup**: https://www.raspberrypi.com/documentation/
- **MQTT Tutorial**: https://www.hivemq.com/mqtt/
- **uv Documentation**: https://docs.astral.sh/uv/

## 🎯 Next Steps

After successful setup:

1. **Calibrate Light Sensor**
   - Use web interface to start calibration
   - Move sensor between dark and bright areas
   - Save calibration values

2. **Adjust Thresholds**
   - Set appropriate dark/bright thresholds for your environment
   - Test auto mode functionality

3. **Monitor Performance**
   - Check system status regularly
   - Review logs for any issues
   - Optimize thresholds as needed

---

**Congratulations!** 🎉 Your IoT Curtain Control System is now ready for use. The system will automatically control your curtains based on ambient light levels while providing a beautiful web interface for monitoring and manual control.
