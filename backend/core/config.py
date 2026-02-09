import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = "dev-secret-key-change-in-production"
DB_NAME = "imd_mwo.db"
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
MAX_CONTENT_LENGTH = 16 * 1024 * 1024

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf', 'doc', 'docx', 'txt', 'xlsx'}

STATIONS = {
    "VABB": "Mumbai",
    "VAAH": "Ahmedabad", 
    "VANP": "Nagpur",
    "VABO": "Vadodara",
    "VAID": "Indore",
    "VABP": "Bhopal",
    "VAGO": "Goa",
    "VAOZ": "Ozar (Nashik)",
    "VAAU": "Aurangabad", 
    "VAKP": "Kolhapur",
    "VASN": "Sindhudurg",
    "VASU": "Surat",
    "VAJJ": "Juhu"
}

DEFAULT_STATION = "VABB"

STATION_COORDS = {
    "VABB": [19.0886, 72.868],
    "VAAH": [23.076, 72.636],
    "VANP": [21.092, 79.047],
    "VABO": [22.336, 73.226],
    "VAID": [22.722, 75.801],
    "VABP": [23.287, 77.338],
    "VAGO": [15.380, 73.831],
    "VAOZ": [20.119, 73.913],
    "VAAU": [19.863, 75.398],
    "VAKP": [16.663, 74.288],
    "VASN": [16.002, 73.525],
    "VASU": [21.114, 72.742],
    "VAJJ": [19.097, 72.833]
}

STATION_STATES = {
    "VABB": "Maharashtra",
    "VANP": "Maharashtra",
    "VAOZ": "Maharashtra",
    "VAAU": "Maharashtra",
    "VAKP": "Maharashtra",
    "VASN": "Maharashtra",
    "VAJJ": "Maharashtra",
    "VAAH": "Gujarat",
    "VABO": "Gujarat",
    "VASU": "Gujarat",
    "VAID": "Madhya Pradesh",
    "VABP": "Madhya Pradesh",
    "VAGO": "Goa"
}

STATE_BOUNDARIES = {
    "Maharashtra": "/static/geojson/maharashtra_districts.geojson",
    "Gujarat": "/static/geojson/india_state.geojson",  # Fallback
    "Madhya Pradesh": "/static/geojson/india_state.geojson", # Fallback
    "Goa": "/static/geojson/india_state.geojson" # Fallback
}

MAHARASHTRA_CENTER = [20.5, 76.0]
MAHARASHTRA_ZOOM = 1800

MIN_OBSERVATIONS_PER_DAY = 20
MIN_HOUR_SPREAD = 18
