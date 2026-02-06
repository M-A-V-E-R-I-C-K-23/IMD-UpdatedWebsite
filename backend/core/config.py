import os

# Base Config
SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-prod'
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload

# Data Validation Config
MIN_OBSERVATIONS_PER_DAY = 8
MIN_HOUR_SPREAD = 12

# Database Config
DB_NAME = 'met_data.db'

# Map & Station Config
DEFAULT_STATION = "VABB"

MAHARASHTRA_CENTER = [19.7515, 75.7139]
MAHARASHTRA_ZOOM = 7

STATIONS = {
    # User-specified airports
    "VABB": "Mumbai (CSIA)",
    "VASD": "Shirdi Airport",
    "VAJJ": "Juhu Airport",
    "VAJL": "Jalgaon Airport",
    "VAAU": "Aurangabad Airport",
    "VOND": "Nanded Airport",
    "VAKP": "Kolhapur Airport",
    "VOSR": "Sindhudurg Airport",
    "VASL": "Solapur Airport",
    "VOLT": "Latur Airport",
    "VOGA": "Mopa Airport",
    "VANM": "Navi Mumbai Airport"
}


STATION_COORDS = {
    # Authoritative WGS-84 ICAO Coordinates
    "VABB": [19.08956, 72.86561],      # Mumbai (CSIA)
    "VASD": [19.68861, 74.37889],      # Shirdi
    "VAJJ": [19.08956, 72.86561],      # Juhu (using Mumbai coords as Juhu is part of Mumbai)
    "VAJL": [20.96222, 75.61722],      # Jalgaon
    "VAAU": [19.86356, 75.39811],      # Aurangabad
    "VOND": [19.18333, 77.31667],      # Nanded
    "VAKP": [16.66444, 74.28944],      # Kolhapur
    "VOSR": [16.00667, 73.52917],      # Sindhudurg (Chipi Airport)
    "VASL": [17.62861, 75.93472],      # Solapur
    "VOLT": [17.62861, 75.93472],      # Latur (using Solapur coords as canonical)
    "VOGA": [15.38083, 73.83139],      # Mopa (Goa Dabolim)
    "VANM": [18.99860, 73.03300]       # Navi Mumbai
}



# Define which state each station belongs to
STATION_STATES = {
    # Maharashtra airports
    "VABB": "Maharashtra",   # Mumbai (CSIA)
    "VASD": "Maharashtra",   # Shirdi
    "VAJJ": "Maharashtra",   # Juhu
    "VAJL": "Maharashtra",   # Jalgaon
    "VAAU": "Maharashtra",   # Aurangabad
    "VOND": "Maharashtra",   # Nanded
    "VAKP": "Maharashtra",   # Kolhapur
    "VOSR": "Maharashtra",   # Sindhudurg
    "VASL": "Maharashtra",   # Solapur
    "VOLT": "Maharashtra",   # Latur
    "VANM": "Maharashtra",   # Navi Mumbai
    
    # Goa airports
    "VOGA": "Goa",           # Mopa
}


# Define GeoJSON paths for each state
# You will need to add these files to static/geojson/
STATE_BOUNDARIES = {
    "Maharashtra": "/static/geojson/maharashtra_districts.geojson",
    "Gujarat": "/static/geojson/gujarat_districts.geojson",
    "Madhya Pradesh": "/static/geojson/mp_districts.geojson",
    "Chhattisgarh": "/static/geojson/chhattisgarh_districts.geojson",
    "Odisha": "/static/geojson/odisha_districts.geojson",
    "Telangana": "/static/geojson/telangana_districts.geojson",
    "Andhra Pradesh": "/static/geojson/andhra_pradesh_districts.geojson",
    "Goa": "/static/geojson/goa_districts.geojson",
}
