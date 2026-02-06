import requests
import json

base = "http://rvrcamd.imd.gov.in:5000"
endpoints = [
    "/config",
    "/api/rvr",
    "/api/live",
    "/live-rvr/data",
    "/rvr-data",
    "/api/stations",
    "/data/live"
]

for ep in endpoints:
    url = base + ep
    print(f"Checking {url}...")
    try:
        resp = requests.get(url, timeout=5)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            print("Response start:", resp.text[:200])
            try:
                data = resp.json()
                print("JSON DATA FOUND!")
                print(json.dumps(data, indent=2)[:500]) # Print first 500 chars
            except:
                print("Not JSON.")
    except Exception as e:
        print(f"Error: {e}")
