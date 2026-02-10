import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = "dev-secret-key-change-in-production"
DB_NAME = "imd_mwo.db"
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
MAX_CONTENT_LENGTH = 16 * 1024 * 1024

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf', 'doc', 'docx', 'txt', 'xlsx'}

STATIONS = {
    "VABB": "Mumbai",
    "VANM": "Navi Mumbai",
    "VASD": "Shirdi",
    "VAJJ": "Juhu",
    "VAJL": "Jalgaon",
    "VAAU": "Aurangabad",
    "VOND": "Nanded",
    "VAKP": "Kolhapur",
    "VOSR": "Sindhudurg",
    "VASL": "Solapur",
    "VOLT": "Latur",
    "VOGA": "Mopa (Goa)"
}

DEFAULT_STATION = "VABB"

STATION_COORDS = {
    "VABB": [19.0886, 72.868],
    "VANM": [18.9846, 73.0653],
    "VASD": [19.6892, 74.3737],
    "VAJJ": [19.097, 72.833],
    "VAJL": [20.9619, 75.6267],
    "VAAU": [19.863, 75.398],
    "VOND": [19.1833, 77.3167],
    "VAKP": [16.663, 74.288],
    "VOSR": [16.0026, 73.5298],
    "VASL": [17.628, 75.9348],
    "VOLT": [18.4117, 76.4642],
    "VOGA": [15.7442, 73.8606]
}

STATION_STATES = {
    "VABB": "Maharashtra",
    "VANM": "Maharashtra",
    "VASD": "Maharashtra",
    "VAJJ": "Maharashtra",
    "VAJL": "Maharashtra",
    "VAAU": "Maharashtra",
    "VOND": "Maharashtra",
    "VAKP": "Maharashtra",
    "VOSR": "Maharashtra",
    "VASL": "Maharashtra",
    "VOLT": "Maharashtra",
    "VOGA": "Goa"
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
