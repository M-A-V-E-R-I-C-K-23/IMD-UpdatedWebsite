import requests
from bs4 import BeautifulSoup

url = "http://rvrcamd.imd.gov.in:5000/live-rvr"

try:
    print(f"Fetching {url}...")
    resp = requests.get(url, timeout=10)
    print(f"Status: {resp.status_code}")
    
    with open("rvr_debug.html", "w", encoding="utf-8") as f:
        f.write(resp.text)
    print("Saved HTML to rvr_debug.html")
    
    soup = BeautifulSoup(resp.content, 'html.parser')
    rows = soup.find_all('tr')
    print(f"Found {len(rows)} rows.")
    
    found = False
    for i, row in enumerate(rows):
        text = row.get_text(strip=True)
        if "VABB" in text or "MUMBAI" in text.upper():
            print(f"MATCH FOUND at row {i}: {text}")
            found = True
            
    if not found:
        print("Target station NOT found in default view.")
        
except Exception as e:
    print(f"Error: {e}")
