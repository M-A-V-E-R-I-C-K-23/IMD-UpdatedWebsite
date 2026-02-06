import sqlite3
import os

DB_NAME = 'met_data.db'

def fix_table():
    print(f"Connecting to {DB_NAME}...")
    conn = sqlite3.connect(DB_NAME)
    try:
        print("Creating admin_uploads table...")
        conn.execute('''
            CREATE TABLE IF NOT EXISTS admin_uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                file_type TEXT, -- pdf, image, etc
                file_path TEXT NOT NULL, -- Relative path or subfolder/filename
                uploaded_by TEXT,
                upload_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                expiration_date DATETIME, -- 6 months from upload
                is_deleted BOOLEAN DEFAULT 0
            );
        ''')
        conn.commit()
        print("✅ Table admin_uploads created successfully.")
        
        # Verify
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admin_uploads';")
        if cursor.fetchone():
            print("Verified: Table exists.")
        else:
            print("❌ Verification Failed: Table not found.")
            
    except Exception as e:
        print(f"Error creating table: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    fix_table()
