#!/usr/bin/env python3
"""
Test script to verify mode synchronization between server and Arduino
"""

import requests
import time
import sys

BASE_URL = "http://localhost:5000"

def print_status(msg):
    """Print status message"""
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}")

def get_system_status():
    """Get current system status"""
    try:
        response = requests.get(f"{BASE_URL}/api/v1/system/status")
        if response.ok:
            return response.json()
        else:
            print(f"❌ Error getting status: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return None

def set_mode(mode):
    """Set curtain mode"""
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/curtain/mode",
            json={"mode": mode}
        )
        return response.json()
    except Exception as e:
        print(f"❌ Error setting mode: {e}")
        return None

def test_mode_sync():
    """Test mode synchronization"""
    print_status("IoT Curtain Control - Mode Sync Test")
    
    # Test 1: Check initial status
    print("\n📋 Test 1: Checking initial status...")
    status = get_system_status()
    if not status:
        print("❌ Cannot connect to server. Is it running?")
        print("   Run: python server/main.py")
        sys.exit(1)
    
    if not status.get('arduino', {}).get('connected'):
        print("❌ Arduino not connected!")
        print("   Check Arduino connection and serial port in config.yaml")
        sys.exit(1)
    
    print("✅ Server is running")
    print("✅ Arduino is connected")
    
    initial_mode = status.get('curtain', {}).get('mode')
    print(f"📍 Initial mode: {initial_mode}")
    
    if initial_mode != 'manual':
        print("⚠️  WARNING: Initial mode should be 'manual' after server startup")
        print("   This might indicate the startup sync didn't work")
    else:
        print("✅ Initial mode is correct (manual)")
    
    # Test 2: Switch to Auto mode
    print("\n📋 Test 2: Switching to AUTO mode...")
    result = set_mode('auto')
    if result:
        print(f"   Server response: {result}")
    
    time.sleep(0.5)  # Wait for mode to sync
    
    status = get_system_status()
    auto_mode = status.get('curtain', {}).get('mode')
    auto_enabled = status.get('settings', {}).get('auto_mode_enabled')
    
    print(f"   Current mode: {auto_mode}")
    print(f"   Auto enabled: {auto_enabled}")
    
    if auto_mode == 'auto' and auto_enabled:
        print("✅ AUTO mode set successfully")
    else:
        print(f"❌ Mode sync failed! Expected 'auto' but got '{auto_mode}'")
        print(f"   Auto enabled: {auto_enabled} (expected True)")
        return False
    
    # Test 3: Switch to Manual mode
    print("\n📋 Test 3: Switching to MANUAL mode...")
    result = set_mode('manual')
    if result:
        print(f"   Server response: {result}")
    
    time.sleep(0.5)  # Wait for mode to sync
    
    status = get_system_status()
    manual_mode = status.get('curtain', {}).get('mode')
    manual_disabled = not status.get('settings', {}).get('auto_mode_enabled')
    
    print(f"   Current mode: {manual_mode}")
    print(f"   Auto disabled: {manual_disabled}")
    
    if manual_mode == 'manual' and manual_disabled:
        print("✅ MANUAL mode set successfully")
    else:
        print(f"❌ Mode sync failed! Expected 'manual' but got '{manual_mode}'")
        print(f"   Auto disabled: {manual_disabled} (expected True)")
        return False
    
    # Test 4: Rapid toggle test
    print("\n📋 Test 4: Rapid toggle test (5 cycles)...")
    for i in range(5):
        mode = 'auto' if i % 2 == 0 else 'manual'
        print(f"   Cycle {i+1}: Setting {mode}...", end=' ')
        set_mode(mode)
        time.sleep(0.3)
        
        status = get_system_status()
        actual = status.get('curtain', {}).get('mode')
        
        if actual == mode:
            print(f"✅ {actual}")
        else:
            print(f"❌ Expected {mode} but got {actual}")
            return False
    
    print("✅ Rapid toggle test passed")
    
    # Final status
    print_status("Test Results")
    status = get_system_status()
    
    print("\n📊 Final System Status:")
    print(f"   Arduino: {'✅ Connected' if status['arduino']['connected'] else '❌ Disconnected'}")
    print(f"   Mode: {status['curtain']['mode']}")
    print(f"   Position: {status['curtain']['position']}")
    print(f"   Motor State: {status['curtain']['motor_state']}")
    print(f"   Auto Mode Enabled: {status['settings']['auto_mode_enabled']}")
    print(f"   Light Value: {status['latest_light']['raw_value'] if status.get('latest_light') else 'N/A'}")
    
    print("\n" + "="*60)
    print("  ✅ ALL TESTS PASSED!")
    print("  Mode synchronization is working correctly!")
    print("="*60)
    
    return True

if __name__ == "__main__":
    try:
        success = test_mode_sync()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

