// Arduino Uno code with motor control and analog reading

const int motorPin = 9;    // motor control pin (via transistor/driver)
const int analogPin = A0;  // analog pin to read

unsigned long lastRead = 0;
const unsigned long interval = 500; // 500 ms

void setup() {
  pinMode(motorPin, OUTPUT);
  digitalWrite(motorPin, LOW); // motor initially off
  Serial.begin(115200);
}

void loop() {
  // Handle incoming commands
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();

    if (command == "ON") {
      digitalWrite(motorPin, HIGH);
      Serial.println("MOTOR ON");
    } else if (command == "OFF") {
      digitalWrite(motorPin, LOW);
      Serial.println("MOTOR OFF");
    }
  }

  // Periodically send analog value
  if (millis() - lastRead >= interval) {
    int sensorValue = analogRead(analogPin);
    Serial.print("VAL:");
    Serial.println(sensorValue);
    lastRead = millis();
  }
}
