import sqlite3
import os

DB_NAME = 'met_data.db'

def verify_schema():
    if not os.path.exists(DB_NAME):
        print(f"Database {DB_NAME} not found.")
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Check news_events
    print("\nChecking news_events columns:")
    try:
        cursor.execute("PRAGMA table_info(news_events)")
        columns = [row[1] for row in cursor.fetchall()]
        print(columns)
        if 'upload_id' in columns:
            print("✅ 'upload_id' exists in news_events")
        else:
            print("❌ 'upload_id' MISSING in news_events")
            # Attempt fix
            print("Attempting to add column...")
            try:
                conn.execute("ALTER TABLE news_events ADD COLUMN upload_id INTEGER")
                conn.commit()
                print("✅ Added 'upload_id' to news_events")
            except Exception as e:
                print(f"Failed to add column: {e}")
    except Exception as e:
        print(f"Error checking news_events: {e}")

    # Check notices
    print("\nChecking notices columns:")
    try:
        cursor.execute("PRAGMA table_info(notices)")
        columns = [row[1] for row in cursor.fetchall()]
        print(columns)
        if 'upload_id' in columns:
            print("✅ 'upload_id' exists in notices")
        else:
            print("❌ 'upload_id' MISSING in notices")
            try:
                conn.execute("ALTER TABLE notices ADD COLUMN upload_id INTEGER")
                conn.commit()
                print("✅ Added 'upload_id' to notices")
            except Exception as e:
                print(f"Failed to add column: {e}")
    except Exception as e:
        print(f"Error checking notices: {e}")

    # Check admin_uploads content
    print("\nChecking admin_uploads content:")
    try:
        cursor.execute("SELECT * FROM admin_uploads")
        rows = cursor.fetchall()
        print(f"Total rows in admin_uploads: {len(rows)}")
        for row in rows:
            print(row)
    except Exception as e:
        print(f"Error checking admin_uploads: {e}")

    # Check notams columns
    print("\nChecking notams columns:")
    try:
        cursor.execute("PRAGMA table_info(notams)")
        columns = [row[1] for row in cursor.fetchall()]
        print(columns)
        if 'upload_id' in columns:
            print("✅ 'upload_id' exists in notams")
        else:
            print("❌ 'upload_id' MISSING in notams")
            try:
                conn.execute("ALTER TABLE notams ADD COLUMN upload_id INTEGER")
                conn.commit()
                print("✅ Added 'upload_id' to notams")
            except Exception as e:
                print(f"Failed to add column: {e}")
    except Exception as e:
        print(f"Error checking notams: {e}")
        
    conn.close()

if __name__ == '__main__':
    verify_schema()
