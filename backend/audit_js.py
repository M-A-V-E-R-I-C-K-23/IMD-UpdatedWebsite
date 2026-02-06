import requests
import re

url = "http://rvrcamd.imd.gov.in:5000/assets/index-cHCasGQW.js"

try:
    print(f"Fetching {url}...")
    resp = requests.get(url, timeout=10)
    
    if resp.status_code == 200:
        content = resp.text
        # Look for API paths or URLs
        # regex for /api/something or http://...
        urls = re.findall(r'["\'](http[s]?://[^"\']+|/api/[^"\']+)["\']', content)
        print("Found URLs/Paths:")
        for u in set(urls):
            print(u)
            
        # Also look for 'fetch(' calls
        fetches = re.findall(r'fetch\(([^)]+)\)', content)
        print("\nFetch calls:")
        for f in fetches:
            print(f[:100]) # Print first 100 chars
            
    else:
        print(f"Failed to fetch JS: {resp.status_code}")

except Exception as e:
    print(f"Error: {e}")
