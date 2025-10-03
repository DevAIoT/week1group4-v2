# Quick Test Instructions - Mode Sync Fix

## Step 1: Stop Current Server (if running)
```bash
# Press Ctrl+C in the terminal running the server
# OR
pkill -f "python.*main.py"
```

## Step 2: Start Fresh Server
```bash
cd /Users/jay/Desktop/week1group4
python server/main.py
```

**Watch for these log messages:**
```
Arduino connected successfully
Initialized Arduino to MANUAL mode          ← Should see this!
Received MODE update from Arduino: 'manual' ← Should see this!
✓ System status updated: mode=manual        ← Should see this!
```

## Step 3: Open Frontend
Open browser: http://localhost:5000

**Expected:** Mode badge shows "Manual" and toggle is OFF

## Step 4: Toggle to Auto Mode
Click the toggle switch to enable Automatic Mode

**Watch server logs for:**
```
📡 Arduino MODE update: 'AUTO' -> passing 'auto' to callback
Received MODE update from Arduino: 'auto'
✓ System status updated: mode=auto, auto_enabled=True
```

**In frontend:**
- Mode badge should change to "Auto"
- "Automatic Mode" label should appear
- Open/Close buttons should become disabled (grayed out)

## Step 5: Toggle Back to Manual
Click the toggle switch to disable Automatic Mode

**Watch server logs for:**
```
📡 Arduino MODE update: 'MANUAL' -> passing 'manual' to callback
Received MODE update from Arduino: 'manual'
✓ System status updated: mode=manual, auto_enabled=False
```

**In frontend:**
- Mode badge should change to "Manual"
- "Manual Mode" label should appear
- Open/Close buttons should become enabled (colored)

## Step 6: Test Manual Controls
With mode set to Manual:
1. Click "Open Curtains" - should work
2. Click "Close Curtains" - should work

Toggle to Auto:
1. Try clicking "Open Curtains" - should show alert: "⚠️ Please switch to Manual Mode first"

## What If It Still Doesn't Work?

### Check Arduino Serial Monitor
1. Open Arduino IDE
2. Tools → Serial Monitor (set to 115200 baud)
3. Type: `MANUAL_MODE` and press Enter
4. You should see: `MODE:MANUAL`
5. Type: `AUTO_MODE` and press Enter
6. You should see: `MODE:AUTO`

If Arduino doesn't respond correctly, re-upload the firmware.

### Check Browser Console
1. Press F12 to open Developer Tools
2. Go to Console tab
3. Toggle the mode switch
4. Look for: "Mode changed: {status: 'success', mode: 'auto'}"

### Run Automated Test
```bash
python test_mode_sync.py
```

This will run through all mode changes automatically and report results.

### Check Server Logs Detail
```bash
tail -f logs/curtain_control.log | grep -i mode
```

Toggle the switch and watch for MODE messages.

