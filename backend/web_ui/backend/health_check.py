#!/usr/bin/env python3
"""
Health check script for the Stock Analysis Web UI Backend.
"""

import requests
import sys
import time
import json

def check_health(host="localhost", port=8000, timeout=5):
    """Check if the backend is healthy."""
    try:
        url = f"http://{host}:{port}/health"
        response = requests.get(url, timeout=timeout)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Backend is healthy")
            print(f"  Status: {data.get('status', 'unknown')}")
            print(f"  Timestamp: {data.get('timestamp', 'unknown')}")
            print(f"  Version: {data.get('version', 'unknown')}")
            return True
        else:
            print(f"✗ Backend returned status code: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"✗ Cannot connect to backend at {host}:{port}")
        return False
    except requests.exceptions.Timeout:
        print(f"✗ Backend health check timed out")
        return False
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False

def check_websocket(host="localhost", port=8000):
    """Check if WebSocket endpoint is available."""
    try:
        import websockets
        import asyncio
        
        async def test_websocket():
            uri = f"ws://{host}:{port}/ws"
            try:
                async with websockets.connect(uri, timeout=5) as websocket:
                    # Send a ping message
                    await websocket.send(json.dumps({"type": "ping"}))
                    response = await asyncio.wait_for(websocket.recv(), timeout=5)
                    return True
            except Exception:
                return False
        
        result = asyncio.run(test_websocket())
        if result:
            print("✓ WebSocket endpoint is working")
        else:
            print("✗ WebSocket endpoint is not responding")
        return result
        
    except ImportError:
        print("⚠ websockets package not available, skipping WebSocket test")
        return True
    except Exception as e:
        print(f"✗ WebSocket test failed: {e}")
        return False

def main():
    """Main health check."""
    print("Stock Analysis Web UI Backend - Health Check")
    print("=" * 50)
    
    # Check HTTP health endpoint
    http_ok = check_health()
    
    # Check WebSocket endpoint
    ws_ok = check_websocket()
    
    print("=" * 50)
    
    if http_ok and ws_ok:
        print("✓ All health checks passed!")
        sys.exit(0)
    else:
        print("✗ Some health checks failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()