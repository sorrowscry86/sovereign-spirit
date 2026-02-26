
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_endpoint(name, method, url, json_body=None):
    print(f"\n[*] Testing {name} ({method} {url})...")
    try:
        if method == "GET":
            response = requests.get(f"{BASE_URL}{url}", timeout=5)
        else:
            response = requests.post(f"{BASE_URL}{url}", json=json_body, timeout=5)
            
        print(f"    Status: {response.status_code}")
        if response.status_code in [200, 201]:
            print(f"    [+] SUCCESS")
            try:
                print(f"    Body: {json.dumps(response.json(), indent=2)[:500]}...")
            except:
                print(f"    Body: {response.text[:200]}")
            return True
        else:
            print(f"    [-] FAILED: {response.text}")
            return False
    except Exception as e:
        print(f"    [-] EXCEPTION: {e}")
        return False

def main():
    print("=== OPERATION SCRYING GLASS: API VERIFICATION ===")
    
    # 1. Health
    if not test_endpoint("Health Check", "GET", "/health"):
        print("CRITICAL: API seemingly offline.")
        return

    # 2. Trigger Pulse (Global)
    test_endpoint("Global Pulse Trigger", "POST", "/api/pulse/trigger", {"action": "TEST_PULSE"})
    
    # Wait for processing
    time.sleep(2)
    
    # 3. Read Logs/Thoughts
    test_endpoint("Read Thoughts", "GET", "/api/logs/thoughts?limit=5")
    
    print("\n=== VERIFICATION COMPLETE ===")

if __name__ == "__main__":
    main()
