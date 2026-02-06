import requests
import json

try:
    print("Testing /api/rvr/status...")
    resp = requests.get("http://127.0.0.1:5000/api/rvr/status")
    print(f"Status Code: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(json.dumps(data, indent=2))
        if data.get('status') in ['ok', 'error']:
            print("SUCCESS: API returned valid structure.")
        else:
            print("FAILURE: API returned unexpected structure.")
    else:
        print(f"FAILURE: API returned status {resp.status_code}")
        print(resp.text)

except Exception as e:
    print(f"ERROR: {e}")
