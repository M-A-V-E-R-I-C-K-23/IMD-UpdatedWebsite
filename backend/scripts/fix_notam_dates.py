from database.operations import get_db_connection
from datetime import datetime

def fix_dates():
    conn = get_db_connection()
    try:
        # Set all NOTAMs to expire in 2027
        new_date = "2027-01-01 12:00:00"
        conn.execute("UPDATE notams SET valid_till_utc = ? WHERE status IN ('ACTIVE', 'DRAFT')", (new_date,))
        conn.commit()
        print(f"Updated NOTAMs to expire at {new_date}")
        
    except Exception as e:
        print(e)
    finally:
        conn.close()

if __name__ == "__main__":
    fix_dates()
