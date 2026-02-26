
import requests
import json

# explicit key from user request
KEY = "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"

def test_key():
    print(f"[*] Verifying Key: {KEY[:15]}...")
    
    # Check validity via auth endpoint
    url = "https://openrouter.ai/api/v1/auth/key"
    headers = {
        "Authorization": f"Bearer {KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        print(f"[*] GET {url}")
        response = requests.get(url, headers=headers, timeout=10)
        
        print(f"[*] Status Code: {response.status_code}")
        print(f"[*] Body: {response.text}")
        
        if response.status_code == 200:
            print(f"[+] SUCCESS: Key is Valid.")
        else:
            print(f"[-] FAILED: {response.status_code}")
            
    except Exception as e:
        print(f"[-] EXCEPTION: {e}")

if __name__ == "__main__":
    test_key()
