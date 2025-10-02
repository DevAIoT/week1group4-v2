from flask import Flask, jsonify, render_template_string, request
import serial
import time
import threading

# Serial setup (match Arduino)
arduino = serial.Serial('/dev/ttyACM0', 115200, timeout=1)
time.sleep(2)

# Shared state
latest_value = {"analog": None}
lock = threading.Lock()

# Background thread to read serial continuously
def read_serial():
    while True:
        line = arduino.readline().decode(errors="ignore").strip()
        if line.startswith("VAL:"):
            try:
                value = int(line.split(":")[1])
                with lock:
                    latest_value["analog"] = value
            except:
                pass
        # Optional: print debug
        # else:
        #     print("Arduino:", line)

thread = threading.Thread(target=read_serial, daemon=True)
thread.start()

app = Flask(__name__)

def send_command(command: str):
    arduino.write((command + "\n").encode())
    return "OK"

# HTML template with toggle button + live value
INDEX_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Arduino LED & Sensor</title>
    <script>
        async function toggleLED() {
            let resp = await fetch('/toggle', {method: 'POST'});
            let data = await resp.json();
            document.getElementById('ledstatus').innerText = "LED: " + data.status;
        }

        async function updateValue() {
            let resp = await fetch('/value');
            let data = await resp.json();
            document.getElementById('sensor').innerText = "Analog Value: " + data.value;
        }

        setInterval(updateValue, 1000); // poll every 1s
        window.onload = updateValue;
    </script>
</head>
<body>
    <h1>Arduino LED & Sensor Monitor</h1>
    <button onclick="toggleLED()">Toggle LED</button>
    <p id="ledstatus">LED: Unknown</p>
    <p id="sensor">Analog Value: -</p>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(INDEX_HTML)

@app.route("/toggle", methods=["POST"])
def toggle():
    # Very naive: alternate ON/OFF by tracking last command
    if getattr(toggle, "state", "OFF") == "OFF":
        send_command("ON")
        toggle.state = "ON"
        return jsonify({"status": "ON"})
    else:
        send_command("OFF")
        toggle.state = "OFF"
        return jsonify({"status": "OFF"})

@app.route("/value")
def value():
    with lock:
        val = latest_value["analog"]
    return jsonify({"value": val})
    
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

