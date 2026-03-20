import urllib.request
import json
import time

BASE_URL = "http://localhost:8000"

def check_endpoint(endpoint):
    try:
        with urllib.request.urlopen(f"{BASE_URL}{endpoint}") as response:
            data = json.loads(response.read().decode())
            print(f"[SUCCESS] {endpoint}: {len(data) if isinstance(data, list) else 'OK'}")
            # print(json.dumps(data, indent=2))
            return True
    except Exception as e:
        print(f"[ERROR] {endpoint}: {e}")
        return False

print("Waiting for server...")
time.sleep(3) # Give server time to start

print("Verifying API Endpoints...")
check_endpoint("/")
check_endpoint("/api/stats")
check_endpoint("/api/users/risk")
check_endpoint("/api/events/risk")
