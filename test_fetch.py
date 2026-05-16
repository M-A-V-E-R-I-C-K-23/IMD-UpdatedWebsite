import sys
import os
sys.path.insert(0, os.path.abspath("backend"))
from backend.features.ogimet.services import fetch_station_data
import sqlite3

fetch_station_data('VANM', hours=5)

db = sqlite3.connect('backend/imd_mwo.db')
cursor = db.cursor()
cursor.execute("SELECT COUNT(*) FROM observations WHERE station_icao='VANM'")
print("VANM rows:", cursor.fetchone()[0])
