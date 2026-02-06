import requests

# Try new AWC API format
# https://aviationweather.gov/data/api/

print("Testing AWC API new format...")
url = "https://aviationweather.gov/api/data/metar"
params = {
    'ids': 'VABB',
    'format': 'raw',
    'hours': 72
}

response = requests.get(url, params=params, timeout=60)
print(f"Status: {response.status_code}")
print(f"Response length: {len(response.text)}")
print("\nFirst 3000 chars:")
print(response.text[:3000])
