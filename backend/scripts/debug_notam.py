from database.operations import get_public_active_notam, get_notams_by_status, get_db_connection
from datetime import datetime

def check_notam():
    print(f"Current Time (UTC): {datetime.utcnow()}")
    
    print("\n--- All ACTIVE Notams in DB ---")
    active_list = get_notams_by_status('ACTIVE')
    for n in active_list:
        print(f"ID: {n['id']}, ValidTill: {n['valid_till_utc']}")
        
    print("\n--- Public Active Notam (Filtered) ---")
    public = get_public_active_notam()
    print(public)

if __name__ == "__main__":
    check_notam()
