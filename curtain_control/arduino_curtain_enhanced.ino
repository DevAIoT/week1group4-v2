/*
 * Enhanced IoT Curtain Control - Arduino Firmware
 * Version: 2.2 - LDR-Controlled Motor Speed
 * Features:
 * - Motor speed directly controlled by light level
 * - Smoothed light sensor readings with running average
 * - Auto/Manual mode switching
 * - Adjustable light threshold
 * - Serial command protocol for IoT integration
 * - EEPROM persistence for calibration
 */

#include <EEPROM.h>

// ============================================================================
// CONFIGURATION
// ============================================================================

// Pin definitions
const int MOTOR_PIN = 9;           // PWM-capable pin for motor control
const int LIGHT_SENSOR_PIN = A0;   // Analog pin for LDR

// Light threshold settings
int openThreshold = 300;           // Open curtain when light falls below this
int closeThreshold = 700;          // Close curtain when light rises above this

// Timing constants
const unsigned long LIGHT_READ_INTERVAL = 200;      // ms between light readings (match your delay)
const unsigned long STATUS_REPORT_INTERVAL = 5000;  // ms between status reports
const unsigned long MANUAL_OPEN_DURATION = 3000;    // 3 seconds for manual open
const unsigned long MANUAL_CLOSE_DURATION = 6000;   // 6 seconds for manual close

// Light sensor configuration
const int LIGHT_SAMPLES = 5;       // Number of samples for averaging (faster response)

// EEPROM addresses for persistent storage
const int EEPROM_ADDR_OPEN_THRESHOLD = 0;
const int EEPROM_ADDR_CLOSE_THRESHOLD = 2;
const int EEPROM_ADDR_AUTO_MODE = 4;
const int EEPROM_MAGIC_NUMBER = 0xCD;

// ============================================================================
// GLOBAL VARIABLES
// ============================================================================

// Light sensor state
int lightReadings[LIGHT_SAMPLES];
int lightReadIndex = 0;
int lightTotal = 0;
int lightAverage = 0;
int currentLightRaw = 0;

// Motor state
int currentMotorSpeed = 0;         // Current PWM value (0-255)
bool autoMode = true;              // Auto mode: motor controlled by light
bool manualMode = false;           // Manual mode: motor controlled by commands
int manualMotorSpeed = 0;          // Manual mode speed setting

// Manual mode timing
unsigned long manualStartTime = 0; // When manual operation started
bool manualOperationActive = false; // If manual operation is in progress
bool manualOpenOperation = false;  // True for open, false for close

// Timing variables
unsigned long lastLightRead = 0;
unsigned long lastStatusReport = 0;

// Command buffer
String commandBuffer = "";
const int MAX_COMMAND_LENGTH = 64;

// ============================================================================
// SETUP
// ============================================================================

void setup() {
  // Initialize serial communication
  Serial.begin(115200);  // Using 115200 for consistency with server
  // while (!Serial) {
  //   ; // Wait for serial port to connect
  // }
  
  // Initialize pins
  pinMode(MOTOR_PIN, OUTPUT);
  analogWrite(MOTOR_PIN, 0);  // Start with motor stopped
  
  // Initialize light sensor readings array
  for (int i = 0; i < LIGHT_SAMPLES; i++) {
    lightReadings[i] = 0;
  }
  
  // Pre-fill light readings with initial values
  for (int i = 0; i < LIGHT_SAMPLES; i++) {
    int reading = analogRead(LIGHT_SENSOR_PIN);
    lightReadings[i] = reading;
    lightTotal += reading;
    delay(10);
  }
  lightAverage = lightTotal / LIGHT_SAMPLES;
  
  // Load settings from EEPROM
  loadSettings();
  
  // Send ready message
  Serial.println("READY:Arduino Curtain Control v2.3 (Enhanced Control)");
  Serial.print("MODE:");
  Serial.println(autoMode ? "AUTO" : "MANUAL");
  Serial.print("OPEN_THRESHOLD:");
  Serial.println(openThreshold);
  Serial.print("CLOSE_THRESHOLD:");
  Serial.println(closeThreshold);
  Serial.print("INITIAL_LIGHT:");
  Serial.println(lightAverage);
  
  delay(100);
}

// ============================================================================
// MAIN LOOP
// ============================================================================

void loop() {
  unsigned long currentTime = millis();
  
  // Read and process serial commands
  processSerialCommands();
  
  // Read light sensor
  if (currentTime - lastLightRead >= LIGHT_READ_INTERVAL) {
    readLightSensor();
    
    // Update motor based on mode
    if (autoMode) {
      updateMotorFromLight();
    } else {
      // Manual mode - check if timed operation is active
      updateManualMode();
    }
    
    lastLightRead = currentTime;
  }
  
  // Send periodic status reports
  if (currentTime - lastStatusReport >= STATUS_REPORT_INTERVAL) {
    sendStatusReport();
    lastStatusReport = currentTime;
  }
}

// ============================================================================
// LIGHT SENSOR FUNCTIONS
// ============================================================================

void readLightSensor() {
  // Subtract the last reading
  lightTotal = lightTotal - lightReadings[lightReadIndex];
  
  // Read new value
  currentLightRaw = analogRead(LIGHT_SENSOR_PIN);
  lightReadings[lightReadIndex] = currentLightRaw;
  
  // Add to total
  lightTotal = lightTotal + lightReadings[lightReadIndex];
  
  // Advance to next position
  lightReadIndex = (lightReadIndex + 1) % LIGHT_SAMPLES;
  
  // Calculate average
  lightAverage = lightTotal / LIGHT_SAMPLES;
  
  // Send light reading
  Serial.print("LIGHT:");
  Serial.println(lightAverage);
}

// ============================================================================
// MOTOR CONTROL FUNCTIONS
// ============================================================================

void updateMotorFromLight() {
  int motorSpeed;
  
  // Continuous motor operation based on light level
  // Dark (low light) = slower speed, Bright (high light) = faster speed
  if (lightAverage <= openThreshold) {
    // Dark conditions - run at slower speed
    motorSpeed = 80;  // Slow speed for dark conditions
    Serial.print("AUTO DARK MODE - ");
  } else if (lightAverage >= closeThreshold) {
    // Bright conditions - run at faster speed  
    motorSpeed = 180; // Fast speed for bright conditions
    Serial.print("AUTO BRIGHT MODE - ");
  } else {
    // Between thresholds - medium speed
    motorSpeed = 120; // Medium speed between thresholds
    Serial.print("AUTO MEDIUM MODE - ");
  }

  // Apply speed to motor
  analogWrite(MOTOR_PIN, motorSpeed);
  currentMotorSpeed = motorSpeed;
  
  // Debug info
  Serial.print("LDR: ");
  Serial.print(lightAverage);
  Serial.print(" | Motor Speed: ");
  Serial.println(motorSpeed);
}

void updateManualMode() {
  unsigned long currentTime = millis();
  
  if (manualOperationActive) {
    unsigned long duration = manualOpenOperation ? MANUAL_OPEN_DURATION : MANUAL_CLOSE_DURATION;
    
    if (currentTime - manualStartTime >= duration) {
      // Operation complete - stop motor
      stopMotor();
      manualOperationActive = false;
      Serial.print("MANUAL ");
      Serial.print(manualOpenOperation ? "OPEN" : "CLOSE");
      Serial.println(" COMPLETED");
    }
    // Motor continues running at set speed until duration expires
  }
}

void startManualOpen() {
  if (!manualMode) {
    Serial.println("ERROR:NOT_IN_MANUAL_MODE");
    return;
  }
  
  manualStartTime = millis();
  manualOperationActive = true;
  manualOpenOperation = true;
  manualMotorSpeed = 200; // Medium-high speed for opening
  
  analogWrite(MOTOR_PIN, manualMotorSpeed);
  currentMotorSpeed = manualMotorSpeed;
  
  Serial.print("MANUAL_OPEN_STARTED:");
  Serial.print(MANUAL_OPEN_DURATION);
  Serial.println("ms");
}

void startManualClose() {
  if (!manualMode) {
    Serial.println("ERROR:NOT_IN_MANUAL_MODE");
    return;
  }
  
  manualStartTime = millis();
  manualOperationActive = true;
  manualOpenOperation = false;
  manualMotorSpeed = 150; // Medium speed for closing
  
  analogWrite(MOTOR_PIN, manualMotorSpeed);
  currentMotorSpeed = manualMotorSpeed;
  
  Serial.print("MANUAL_CLOSE_STARTED:");
  Serial.print(MANUAL_CLOSE_DURATION);
  Serial.println("ms");
}

void setMotorSpeedManual(int speed) {
  if (!manualMode) {
    Serial.println("ERROR:NOT_IN_MANUAL_MODE");
    return;
  }
  
  manualMotorSpeed = constrain(speed, 0, 255);
  analogWrite(MOTOR_PIN, manualMotorSpeed);
  currentMotorSpeed = manualMotorSpeed;
  
  Serial.print("MOTOR_SPEED:");
  Serial.println(manualMotorSpeed);
}

void stopMotor() {
  analogWrite(MOTOR_PIN, 0);
  currentMotorSpeed = 0;
  manualMotorSpeed = 0;
  manualOperationActive = false;
  Serial.println("MOTOR:STOPPED");
}

void setAutoMode(bool enable) {
  autoMode = enable;
  manualMode = !enable;
  
  // Always stop motor when changing modes
  stopMotor();
  
  saveSettings();
  
  Serial.print("MODE:");
  Serial.println(autoMode ? "AUTO" : "MANUAL");
  Serial.print("MANUAL_MODE:");
  Serial.println(manualMode ? "TRUE" : "FALSE");
}

void setOpenThreshold(int newThreshold) {
  openThreshold = constrain(newThreshold, 0, 1023);
  saveSettings();
  
  Serial.print("OPEN_THRESHOLD:");
  Serial.println(openThreshold);
}

void setCloseThreshold(int newThreshold) {
  closeThreshold = constrain(newThreshold, 0, 1023);
  saveSettings();
  
  Serial.print("CLOSE_THRESHOLD:");
  Serial.println(closeThreshold);
}

// ============================================================================
// EEPROM FUNCTIONS
// ============================================================================

void saveSettings() {
  EEPROM.write(EEPROM_ADDR_AUTO_MODE, EEPROM_MAGIC_NUMBER);
  EEPROM.write(EEPROM_ADDR_OPEN_THRESHOLD, lowByte(openThreshold));
  EEPROM.write(EEPROM_ADDR_OPEN_THRESHOLD + 1, highByte(openThreshold));
  EEPROM.write(EEPROM_ADDR_CLOSE_THRESHOLD, lowByte(closeThreshold));
  EEPROM.write(EEPROM_ADDR_CLOSE_THRESHOLD + 1, highByte(closeThreshold));
  
  Serial.println("SETTINGS:SAVED");
}

void loadSettings() {
  byte magic = EEPROM.read(EEPROM_ADDR_AUTO_MODE);
  
  if (magic == EEPROM_MAGIC_NUMBER) {
    openThreshold = word(EEPROM.read(EEPROM_ADDR_OPEN_THRESHOLD + 1), 
                         EEPROM.read(EEPROM_ADDR_OPEN_THRESHOLD));
    closeThreshold = word(EEPROM.read(EEPROM_ADDR_CLOSE_THRESHOLD + 1), 
                          EEPROM.read(EEPROM_ADDR_CLOSE_THRESHOLD));
    Serial.println("SETTINGS:LOADED");
  } else {
    Serial.println("SETTINGS:NOT_FOUND_USING_DEFAULTS");
  }
}

void resetSettings() {
  openThreshold = 300;
  closeThreshold = 700;
  autoMode = true;
  manualMode = false;
  EEPROM.write(EEPROM_ADDR_AUTO_MODE, 0);
  Serial.println("SETTINGS:RESET");
}

// ============================================================================
// COMMAND PROCESSING
// ============================================================================

void processSerialCommands() {
  while (Serial.available() > 0) {
    char inChar = Serial.read();
    
    if (inChar == '\n' || inChar == '\r') {
      if (commandBuffer.length() > 0) {
        processCommand(commandBuffer);
        commandBuffer = "";
      }
    } else if (commandBuffer.length() < MAX_COMMAND_LENGTH) {
      commandBuffer += inChar;
    }
  }
}

void processCommand(String command) {
  command.trim();
  command.toUpperCase();
  
  // Parse command and optional parameters
  int colonPos = command.indexOf(':');
  String cmd = (colonPos > 0) ? command.substring(0, colonPos) : command;
  String params = (colonPos > 0) ? command.substring(colonPos + 1) : "";
  
  // Command routing
  if (cmd == "AUTO" || cmd == "AUTO_MODE") {
    setAutoMode(true);
  }
  else if (cmd == "MANUAL" || cmd == "MANUAL_MODE") {
    setAutoMode(false);
  }
  else if (cmd == "SET_SPEED") {
    if (params.length() > 0) {
      int speed = params.toInt();
      // If percentage (0-100), convert to PWM (0-255)
      if (speed <= 100) {
        speed = map(speed, 0, 100, 0, 255);
      }
      setMotorSpeedManual(speed);
    } else {
      Serial.println("ERROR:MISSING_SPEED_PARAMETER");
    }
  }
  else if (cmd == "STOP_MOTOR" || cmd == "STOP") {
    stopMotor();
  }
  else if (cmd == "SET_OPEN_THRESHOLD") {
    if (params.length() > 0) {
      int threshold = params.toInt();
      setOpenThreshold(threshold);
    } else {
      Serial.println("ERROR:MISSING_THRESHOLD_PARAMETER");
    }
  }
  else if (cmd == "SET_CLOSE_THRESHOLD") {
    if (params.length() > 0) {
      int threshold = params.toInt();
      setCloseThreshold(threshold);
    } else {
      Serial.println("ERROR:MISSING_THRESHOLD_PARAMETER");
    }
  }
  else if (cmd == "OPEN_CURTAIN") {
    if (manualMode) {
      startManualOpen();
    } else {
      Serial.println("ERROR:NOT_IN_MANUAL_MODE");
    }
  }
  else if (cmd == "CLOSE_CURTAIN") {
    if (manualMode) {
      startManualClose();
    } else {
      Serial.println("ERROR:NOT_IN_MANUAL_MODE");
    }
  }
  else if (cmd == "READ_LIGHT") {
    Serial.print("LIGHT:");
    Serial.println(lightAverage);
    Serial.print("LIGHT_RAW:");
    Serial.println(currentLightRaw);
  }
  else if (cmd == "GET_STATUS") {
    sendStatusReport();
  }
  else if (cmd == "RESET_SETTINGS") {
    resetSettings();
  }
  else if (cmd == "TEST_MOTOR") {
    testMotor();
  }
  else if (cmd == "PING") {
    Serial.println("PONG");
  }
  else if (cmd == "VERSION") {
    Serial.println("VERSION:2.3-Enhanced");
  }
  else {
    Serial.print("ERROR:UNKNOWN_COMMAND:");
    Serial.println(cmd);
  }
}

// ============================================================================
// STATUS REPORTING
// ============================================================================

void sendStatusReport() {
  Serial.println("STATUS:REPORT_START");
  
  // Light sensor status
  Serial.print("LIGHT:");
  Serial.println(lightAverage);
  Serial.print("LIGHT_RAW:");
  Serial.println(currentLightRaw);
  Serial.print("OPEN_THRESHOLD:");
  Serial.println(openThreshold);
  Serial.print("CLOSE_THRESHOLD:");
  Serial.println(closeThreshold);
  
  // Motor status
  Serial.print("MOTOR_SPEED:");
  Serial.println(currentMotorSpeed);
  
  // Mode status
  Serial.print("MODE:");
  Serial.println(autoMode ? "AUTO" : "MANUAL");
  
  // System info
  Serial.print("UPTIME:");
  Serial.println(millis());
  
  Serial.println("STATUS:REPORT_END");
}

// ============================================================================
// TESTING FUNCTIONS
// ============================================================================

void testMotor() {
  Serial.println("TEST:MOTOR_START");
  
  // Save current mode
  bool wasAuto = autoMode;
  
  // Switch to manual for testing
  autoMode = false;
  manualMode = true;
  
  Serial.println("TEST:Testing 25% speed...");
  analogWrite(MOTOR_PIN, 64);
  delay(2000);
  
  Serial.println("TEST:Testing 50% speed...");
  analogWrite(MOTOR_PIN, 128);
  delay(2000);
  
  Serial.println("TEST:Testing 75% speed...");
  analogWrite(MOTOR_PIN, 192);
  delay(2000);
  
  Serial.println("TEST:Testing 100% speed...");
  analogWrite(MOTOR_PIN, 255);
  delay(2000);
  
  Serial.println("TEST:Stopping motor...");
  analogWrite(MOTOR_PIN, 0);
  
  // Restore previous mode
  autoMode = wasAuto;
  manualMode = !wasAuto;
  
  Serial.println("TEST:MOTOR_COMPLETE");
  Serial.print("TEST:Restored to ");
  Serial.println(autoMode ? "AUTO" : "MANUAL");
} 