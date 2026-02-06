import sqlite3
import time

def migrate():
    print("Starting migration...")
    try:
        conn = sqlite3.connect('met_data.db', timeout=10) # 10s timeout
        cursor = conn.cursor()
        
        # News
        try:
            cursor.execute("ALTER TABLE news_events ADD COLUMN ocr_text TEXT")
            print("Added ocr_text to news_events")
        except Exception as e:
            print(f"news_events ocr_text: {e}")
            
        try:
            cursor.execute("ALTER TABLE news_events ADD COLUMN status TEXT DEFAULT 'PUBLISHED'")
            print("Added status to news_events")
        except Exception as e:
            print(f"news_events status: {e}")
            
        # Notices
        try:
            cursor.execute("ALTER TABLE notices ADD COLUMN ocr_text TEXT")
            print("Added ocr_text to notices")
        except Exception as e:
            print(f"notices ocr_text: {e}")
            
        try:
            cursor.execute("ALTER TABLE notices ADD COLUMN status TEXT DEFAULT 'PUBLISHED'")
            print("Added status to notices")
        except Exception as e:
            print(f"notices status: {e}")

        conn.commit()
        conn.close()
        print("Migration complete.")
    except Exception as e:
        print(f"CRITICAL DB ERROR: {e}")

if __name__ == "__main__":
    migrate()
