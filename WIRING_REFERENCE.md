# 🔌 Hardware Wiring Reference

## Arduino Uno Pin Layout

```
┌─────────────────┐
│       USB       │ ← Connect to Raspberry Pi
│                 │
│   13 12 11 10  │ ← Digital pins
│   9  8  7  6   │ ← Motor control pins ⭐
│   5  4  3  2   │
│   A0 A1 A2 A3  │ ← Analog pins (A0 = light sensor) ⭐
│   A4 A5         │
│   GND 5V        │ ← Power pins ⭐
└─────────────────┘
```

## Photoresistor (Light Sensor)

### Components
- Photoresistor (LDR)
- 10kΩ resistor
- Jumper wires

### Wiring Diagram
```
Arduino A0 ───┬─── Photoresistor ───┬─── GND
              │                     │
              └─── 10kΩ Resistor ───┘
```

### Breadboard Layout
```
┌─────────────────────────────────┐
│  +5V ──────────┬──────────────── │
│                │                │
│  A0  ──────────┼── LDR ─────────┼── GND
│                │                │
│  GND ──────────┴── 10kΩ ────────┘
└─────────────────────────────────┘
```

## L293D Motor Driver Circuit

### L293D Pinout
```
┌─────────────────┐
│ 1  2  3  4  5  │ ← Enable and Input pins
│ 6  7  8  9 10  │
│11 12 13 14 15  │ ← Motor outputs
│16     GND      │
└─────────────────┘
```

### Arduino Connections
```
Pin 9 ─── L293D Pin 1 (Enable 1,2) ← PWM control
Pin 8 ─── L293D Pin 2 (Input 1)    ← Direction control
5V ────── L293D Pin 16 (VCC)       ← Logic power
GND ───── L293D Pin 4,5 (GND)      ← Ground
```

### Motor Connections
```
L293D Pin 3 ─── Motor Wire 1
L293D Pin 6 ─── Motor Wire 2
L293D Pin 8 ←── External 12V (Motor Power)
```

### Complete Circuit
```
┌─────────────────────────────────┐
│ Arduino:                        │
│ Pin 9  ─── L293D Pin 1          │
│ Pin 8  ─── L293D Pin 2          │
│ 5V     ─── L293D Pin 16         │
│ GND    ─── L293D Pin 4,5        │
│                                 │
│ L293D:                          │
│ Pin 8  ←── External 12V         │
│ Pin 3  ─── Motor Wire 1         │
│ Pin 6  ─── Motor Wire 2         │
└─────────────────────────────────┘
```

## Power Requirements

### Arduino Power
- **USB Power**: 5V from Raspberry Pi (sufficient for logic)
- **Current**: ~50mA for Arduino + sensors

### Motor Power
- **External Supply**: 12V DC power adapter recommended
- **Current**: Depends on motor (typically 200mA-1A)
- **Connection**: Connect to L293D Pin 8 only

### ⚠️ Critical Safety Notes

1. **Never connect motor directly to Arduino pins**
2. **Use external power for motors**
3. **Connect Arduino GND to motor driver GND**
4. **Use appropriate wire gauge for motor current**
5. **Add flyback diode across motor terminals**

## Testing Your Wiring

### 1. Photoresistor Test
```bash
# In Arduino IDE Serial Monitor (115200 baud)
# Should see varying values when covering/exposing sensor
LIGHT:450
LIGHT:200  # When covered
LIGHT:800  # When exposed
```

### 2. Motor Test
```python
# On Raspberry Pi
from server.serial_manager import SerialManager
sm = SerialManager('/dev/ttyACM0')
sm.connect()
sm.open_curtain()  # Should hear motor
sm.close_curtain() # Should hear motor in opposite direction
```

### 3. System Integration Test
```bash
# Start the server
uv run python server/main.py

# Open browser to http://localhost:5000
# Should show real-time light values and control buttons
```

## Troubleshooting Wiring Issues

### No Light Readings
- Check A0 pin connection
- Verify 10kΩ resistor is installed
- Test photoresistor with multimeter

### Motor Not Moving
- Check L293D pin connections
- Verify external power supply
- Test motor with direct battery connection

### Arduino Not Detected
- Check USB cable and connection
- Verify Arduino has power (ON LED)
- Check port in config.yaml
- Run: `ls /dev/tty*` to see available ports

### Intermittent Connection
- Check all wire connections
- Verify power supply stability
- Check for loose connections
- Try different USB cable

## Component Specifications

### Photoresistor
- **Type**: CdS (Cadmium Sulfide)
- **Resistance**: 1MΩ (dark) to 1kΩ (bright)
- **Response Time**: ~10ms

### Motor
- **Type**: DC geared motor
- **Voltage**: 5-12V DC
- **Current**: 100-500mA (depending on load)
- **RPM**: 10-100 RPM (for curtain applications)

### L293D Motor Driver
- **Channels**: 2 (can control 2 motors)
- **Current**: Up to 600mA per channel
- **Voltage**: 4.5-36V motor power
- **Logic**: 5V TTL compatible

## Best Practices

1. **Use color-coded wires** (red for power, black for ground)
2. **Label all connections** before assembly
3. **Test each component individually** before integration
4. **Use proper wire gauge** for current requirements
5. **Add decoupling capacitors** near motor driver
6. **Secure loose wires** with electrical tape
7. **Document your wiring** with photos/diagrams

## Shopping List with Links

- **Arduino Uno**: https://amzn.to/3QK8L5Z
- **Photoresistor Kit**: https://amzn.to/3QJ8f9Y
- **L293D Motor Driver**: https://amzn.to/3QK8L5Z
- **DC Motor 12V**: https://amzn.to/3QJ8f9Y
- **Breadboard**: https://amzn.to/3QK8L5Z
- **Jumper Wires**: https://amzn.to/3QJ8f9Y

---

**Ready to assemble?** Follow the step-by-step guide in `SETUP_GUIDE.md` for complete instructions! 🔧
