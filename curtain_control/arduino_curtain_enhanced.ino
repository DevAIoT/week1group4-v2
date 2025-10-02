/*
 * Enhanced IoT Curtain Control - Arduino Firmware
 * Version: 2.0
 * Features:
 * - Smoothed light sensor readings with running average
 * - Calibration support for min/max light values
 * - Comprehensive command protocol
 * - Motor position tracking
 * - EEPROM persistence for calibration
 * - Error handling and validation
 */

#include <EEPROM.h>

// ============================================================================
// CONFIGURATION
// ============================================================================

// Pin definitions
const int MOTOR_PIN = 9;           // PWM-capable pin for motor control
const int LIGHT_SENSOR_PIN = A0;   // Analog pin for photoresistor
const int MOTOR_DIR_PIN = 8;       // Optional: motor direction control

// Timing constants
const unsigned long LIGHT_READ_INTERVAL = 500;      // ms between light readings
const unsigned long STATUS_REPORT_INTERVAL = 5000;  // ms between status reports
const unsigned long MOTOR_TIMEOUT = 30000;          // ms max motor runtime

// Light sensor configuration
const int LIGHT_SAMPLES = 10;      // Number of samples for averaging
const int LIGHT_MIN_DEFAULT = 50;  // Default minimum light value
const int LIGHT_MAX_DEFAULT = 950; // Default maximum light value

// EEPROM addresses for persistent storage
const int EEPROM_ADDR_MIN_LIGHT = 0;
const int EEPROM_ADDR_MAX_LIGHT = 2;
const int EEPROM_ADDR_CALIBRATED = 4;
const int EEPROM_MAGIC_NUMBER = 0xAB;

// ============================================================================
// GLOBAL VARIABLES
// ============================================================================

// Light sensor state
int lightReadings[LIGHT_SAMPLES];
int lightReadIndex = 0;
int lightTotal = 0;
int lightAverage = 0;
int lightMin = LIGHT_MIN_DEFAULT;
int lightMax = LIGHT_MAX_DEFAULT;
bool isCalibrated = false;

// Motor state
enum MotorState {
  MOTOR_STOPPED,
  MOTOR_OPENING,
  MOTOR_CLOSING
};

enum CurtainPosition {
  POSITION_UNKNOWN,
  POSITION_OPEN,
  POSITION_CLOSED,
  POSITION_PARTIAL
};

MotorState motorState = MOTOR_STOPPED;
CurtainPosition curtainPosition = POSITION_UNKNOWN;
unsigned long motorStartTime = 0;
int motorSpeed = 255; // 0-255 PWM value

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
  Serial.begin(115200);
  while (!Serial) {
    ; // Wait for serial port to connect
  }
  
  // Initialize pins
  pinMode(MOTOR_PIN, OUTPUT);
  pinMode(MOTOR_DIR_PIN, OUTPUT);
  digitalWrite(MOTOR_PIN, LOW);
  digitalWrite(MOTOR_DIR_PIN, LOW);
  
  // Initialize light sensor readings array
  for (int i = 0; i < LIGHT_SAMPLES; i++) {
    lightReadings[i] = 0;
  }
  
  // Load calibration from EEPROM
  loadCalibration();
  
  // Send ready message
  Serial.println("READY:Arduino Curtain Control v2.0");
  Serial.print("CALIBRATION:");
  Serial.print(isCalibrated ? "YES" : "NO");
  Serial.print(",MIN:");
  Serial.print(lightMin);
  Serial.print(",MAX:");
  Serial.println(lightMax);
  
  delay(100);
}

// ============================================================================
// MAIN LOOP
// ============================================================================

void loop() {
  unsigned long currentTime = millis();
  
  // Read and process serial commands
  processSerialCommands();
  
  // Read light sensor with smoothing
  if (currentTime - lastLightRead >= LIGHT_READ_INTERVAL) {
    readLightSensor();
    lastLightRead = currentTime;
  }
  
  // Send periodic status reports
  if (currentTime - lastStatusReport >= STATUS_REPORT_INTERVAL) {
    sendStatusReport();
    lastStatusReport = currentTime;
  }
  
  // Check motor timeout
  if (motorState != MOTOR_STOPPED) {
    if (currentTime - motorStartTime >= MOTOR_TIMEOUT) {
      stopMotor();
      Serial.println("ERROR:MOTOR_TIMEOUT");
    }
  }
}

// ============================================================================
// LIGHT SENSOR FUNCTIONS
// ============================================================================

void readLightSensor() {
  // Subtract the last reading
  lightTotal = lightTotal - lightReadings[lightReadIndex];
  
  // Read new value
  lightReadings[lightReadIndex] = analogRead(LIGHT_SENSOR_PIN);
  
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

int getPercentageLight() {
  if (!isCalibrated) {
    return map(lightAverage, 0, 1023, 0, 100);
  }
  
  int percentage = map(lightAverage, lightMin, lightMax, 0, 100);
  return constrain(percentage, 0, 100);
}

// ============================================================================
// MOTOR CONTROL FUNCTIONS
// ============================================================================

void openCurtain() {
  if (curtainPosition == POSITION_OPEN) {
    Serial.println("STATUS:Already open");
    return;
  }
  
  digitalWrite(MOTOR_DIR_PIN, HIGH);
  analogWrite(MOTOR_PIN, motorSpeed);
  motorState = MOTOR_OPENING;
  motorStartTime = millis();
  curtainPosition = POSITION_PARTIAL;
  
  Serial.println("MOTOR:OPENING");
  Serial.println("POSITION:OPENING");
}

void closeCurtain() {
  if (curtainPosition == POSITION_CLOSED) {
    Serial.println("STATUS:Already closed");
    return;
  }
  
  digitalWrite(MOTOR_DIR_PIN, LOW);
  analogWrite(MOTOR_PIN, motorSpeed);
  motorState = MOTOR_CLOSING;
  motorStartTime = millis();
  curtainPosition = POSITION_PARTIAL;
  
  Serial.println("MOTOR:CLOSING");
  Serial.println("POSITION:CLOSING");
}

void stopMotor() {
  digitalWrite(MOTOR_PIN, LOW);
  motorState = MOTOR_STOPPED;
  
  Serial.println("MOTOR:STOPPED");
  
  // Update position based on previous state
  if (motorState == MOTOR_OPENING) {
    curtainPosition = POSITION_OPEN;
    Serial.println("POSITION:OPEN");
  } else if (motorState == MOTOR_CLOSING) {
    curtainPosition = POSITION_CLOSED;
    Serial.println("POSITION:CLOSED");
  }
}

void setMotorSpeed(int speed) {
  motorSpeed = constrain(speed, 0, 255);
  Serial.print("MOTOR_SPEED:");
  Serial.println(motorSpeed);
  
  // Update current motor if running
  if (motorState != MOTOR_STOPPED) {
    analogWrite(MOTOR_PIN, motorSpeed);
  }
}

// ============================================================================
// CALIBRATION FUNCTIONS
// ============================================================================

void startCalibration() {
  Serial.println("CALIBRATION:STARTED");
  Serial.println("STATUS:Move sensor between darkest and brightest positions");
  
  lightMin = 1023;
  lightMax = 0;
  
  unsigned long calibrationStart = millis();
  const unsigned long CALIBRATION_TIME = 10000; // 10 seconds
  
  while (millis() - calibrationStart < CALIBRATION_TIME) {
    int reading = analogRead(LIGHT_SENSOR_PIN);
    
    if (reading < lightMin) {
      lightMin = reading;
      Serial.print("CALIBRATION:MIN_UPDATE:");
      Serial.println(lightMin);
    }
    
    if (reading > lightMax) {
      lightMax = reading;
      Serial.print("CALIBRATION:MAX_UPDATE:");
      Serial.println(lightMax);
    }
    
    delay(100);
  }
  
  // Add some margin
  lightMin = max(0, lightMin - 10);
  lightMax = min(1023, lightMax + 10);
  
  // Save to EEPROM
  saveCalibration();
  
  Serial.print("CALIBRATION:COMPLETE,MIN:");
  Serial.print(lightMin);
  Serial.print(",MAX:");
  Serial.println(lightMax);
}

void saveCalibration() {
  EEPROM.write(EEPROM_ADDR_CALIBRATED, EEPROM_MAGIC_NUMBER);
  EEPROM.write(EEPROM_ADDR_MIN_LIGHT, lowByte(lightMin));
  EEPROM.write(EEPROM_ADDR_MIN_LIGHT + 1, highByte(lightMin));
  EEPROM.write(EEPROM_ADDR_MAX_LIGHT, lowByte(lightMax));
  EEPROM.write(EEPROM_ADDR_MAX_LIGHT + 1, highByte(lightMax));
  
  isCalibrated = true;
  Serial.println("CALIBRATION:SAVED");
}

void loadCalibration() {
  byte magic = EEPROM.read(EEPROM_ADDR_CALIBRATED);
  
  if (magic == EEPROM_MAGIC_NUMBER) {
    lightMin = word(EEPROM.read(EEPROM_ADDR_MIN_LIGHT + 1), 
                    EEPROM.read(EEPROM_ADDR_MIN_LIGHT));
    lightMax = word(EEPROM.read(EEPROM_ADDR_MAX_LIGHT + 1), 
                    EEPROM.read(EEPROM_ADDR_MAX_LIGHT));
    isCalibrated = true;
    Serial.println("CALIBRATION:LOADED");
  } else {
    Serial.println("CALIBRATION:NOT_FOUND");
    isCalibrated = false;
  }
}

void resetCalibration() {
  lightMin = LIGHT_MIN_DEFAULT;
  lightMax = LIGHT_MAX_DEFAULT;
  isCalibrated = false;
  EEPROM.write(EEPROM_ADDR_CALIBRATED, 0);
  Serial.println("CALIBRATION:RESET");
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
  if (cmd == "OPEN_CURTAIN" || cmd == "OPEN") {
    openCurtain();
  }
  else if (cmd == "CLOSE_CURTAIN" || cmd == "CLOSE") {
    closeCurtain();
  }
  else if (cmd == "STOP_MOTOR" || cmd == "STOP") {
    stopMotor();
  }
  else if (cmd == "READ_LIGHT") {
    Serial.print("LIGHT:");
    Serial.println(lightAverage);
    Serial.print("LIGHT_PERCENT:");
    Serial.println(getPercentageLight());
  }
  else if (cmd == "GET_STATUS") {
    sendStatusReport();
  }
  else if (cmd == "CALIBRATE_LIGHT" || cmd == "CALIBRATE") {
    startCalibration();
  }
  else if (cmd == "RESET_CALIBRATION") {
    resetCalibration();
  }
  else if (cmd == "SET_SPEED") {
    if (params.length() > 0) {
      int speed = params.toInt();
      setMotorSpeed(map(speed, 0, 100, 0, 255));
    } else {
      Serial.println("ERROR:MISSING_SPEED_PARAMETER");
    }
  }
  else if (cmd == "PING") {
    Serial.println("PONG");
  }
  else if (cmd == "VERSION") {
    Serial.println("VERSION:2.0");
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
  Serial.print("LIGHT_PERCENT:");
  Serial.println(getPercentageLight());
  
  // Motor status
  Serial.print("MOTOR:");
  switch(motorState) {
    case MOTOR_STOPPED:  Serial.println("STOPPED"); break;
    case MOTOR_OPENING:  Serial.println("OPENING"); break;
    case MOTOR_CLOSING:  Serial.println("CLOSING"); break;
  }
  
  // Curtain position
  Serial.print("POSITION:");
  switch(curtainPosition) {
    case POSITION_UNKNOWN: Serial.println("UNKNOWN"); break;
    case POSITION_OPEN:    Serial.println("OPEN"); break;
    case POSITION_CLOSED:  Serial.println("CLOSED"); break;
    case POSITION_PARTIAL: Serial.println("PARTIAL"); break;
  }
  
  // Calibration status
  Serial.print("CALIBRATION:");
  Serial.print(isCalibrated ? "YES" : "NO");
  Serial.print(",MIN:");
  Serial.print(lightMin);
  Serial.print(",MAX:");
  Serial.println(lightMax);
  
  // System info
  Serial.print("UPTIME:");
  Serial.println(millis());
  
  Serial.println("STATUS:REPORT_END");
} 