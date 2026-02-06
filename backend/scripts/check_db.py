import sqlite3

def check_db():
    try:
        conn = sqlite3.connect('met_data.db')
        cursor = conn.cursor()
        
        print("--- NOTICES TABLE INFO ---")
        cursor.execute("PRAGMA table_info(notices)")
        columns = cursor.fetchall()
        for col in columns:
            print(col)
            
        print("\n--- NEWS_EVENTS TABLE INFO ---")
        cursor.execute("PRAGMA table_info(news_events)")
        columns = cursor.fetchall()
        for col in columns:
            print(col)
            
        conn.close()
    except Exception as e:
        print(e)

if __name__ == "__main__":
    check_db()
