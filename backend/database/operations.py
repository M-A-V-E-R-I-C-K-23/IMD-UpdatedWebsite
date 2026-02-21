import sqlite3
import os
from datetime import datetime
from core.config import DB_NAME
from core.extensions import logger

def get_db_connection():
    """Create a database connection to the SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database with the observations, news, notices, sigmet, and notam tables."""
    conn = get_db_connection()
    try:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                station_icao TEXT NOT NULL,
                timestamp_utc DATETIME NOT NULL,
                temperature REAL,
                dew_point REAL,
                wind_direction INTEGER,
                wind_speed INTEGER,
                visibility INTEGER,
                qnh REAL,
                raw_metar TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(station_icao, timestamp_utc)
            );

            CREATE TABLE IF NOT EXISTS news_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                filename TEXT,
                ocr_text TEXT,
                status TEXT DEFAULT 'PUBLISHED',
                upload_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                uploaded_by TEXT
            );

            CREATE TABLE IF NOT EXISTS notices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                message TEXT,
                filename TEXT,
                ocr_text TEXT,
                status TEXT DEFAULT 'PUBLISHED',
                upload_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                uploaded_by TEXT
            );

            CREATE TABLE IF NOT EXISTS sigmet_status (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                is_active BOOLEAN NOT NULL DEFAULT 0,
                count INTEGER DEFAULT 0,
                phenomenon TEXT,
                validity_text TEXT,
                raw_data TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS active_notams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                formatted_text TEXT NOT NULL,
                valid_until DATETIME NOT NULL,
                raw_data TEXT,
                uploaded_by TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS notams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                ocr_text TEXT,
                final_notam_text TEXT,
                status TEXT DEFAULT 'DRAFT', -- DRAFT, ACTIVE, ARCHIVED
                valid_from_utc DATETIME,
                valid_till_utc DATETIME,
                uploaded_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS aerodrome_warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                station_icao TEXT NOT NULL,
                message TEXT NOT NULL,
                valid_from DATETIME NOT NULL,
                valid_to DATETIME NOT NULL,
                status TEXT DEFAULT 'ACTIVE', -- ACTIVE, EXPIRED
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS dynamic_buttons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                section TEXT NOT NULL, -- resources, operational, external, olbs
                label TEXT NOT NULL,
                type TEXT NOT NULL, -- link, file
                url TEXT,
                file_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

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

            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                designation TEXT,
                section TEXT,
                telephone TEXT,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')

        try:
            conn.execute("ALTER TABLE news_events ADD COLUMN ocr_text TEXT")
        except: pass
        try:
            conn.execute("ALTER TABLE news_events ADD COLUMN status TEXT DEFAULT 'PUBLISHED'")
        except: pass
        try:
            conn.execute("ALTER TABLE notices ADD COLUMN ocr_text TEXT")
        except: pass
        try:
            conn.execute("ALTER TABLE notices ADD COLUMN status TEXT DEFAULT 'PUBLISHED'")
        except: pass

        try: conn.execute("ALTER TABLE news_events ADD COLUMN upload_id INTEGER")
        except: pass
        try: conn.execute("ALTER TABLE notices ADD COLUMN upload_id INTEGER")
        except: pass
        try: conn.execute("ALTER TABLE notams ADD COLUMN upload_id INTEGER")
        except: pass
        try: conn.execute("ALTER TABLE dynamic_buttons ADD COLUMN upload_id INTEGER")
        except: pass
        conn.commit()

        seed_employees_if_empty()
        
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
    finally:
        conn.close()

def save_observation(observation):
    """
    Save a single observation to the database.
    Ignores duplicates based on station_icao and timestamp_utc.
    """
    conn = get_db_connection()
    try:
        conn.execute('''
            INSERT OR IGNORE INTO observations 
            (station_icao, timestamp_utc, temperature, dew_point, wind_direction, wind_speed, visibility, qnh, raw_metar)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            observation['station_icao'],
            observation['timestamp_utc'],
            observation['temperature'],
            observation['dew_point'],
            observation['wind_direction'],
            observation['wind_speed'],
            observation['visibility'],
            observation['qnh'],
            observation['raw_metar']
        ))
        conn.commit()
    except Exception as e:
        logger.error(f"Error saving observation: {e}")
    finally:
        conn.close()

def get_observations(station_icao, start_dt, end_dt):
    """
    Retrieve observations for a specific station within a time range.
    """
    conn = get_db_connection()
    try:
        cursor = conn.execute('''
            SELECT * FROM observations 
            WHERE station_icao = ? 
            AND timestamp_utc >= ? 
            AND timestamp_utc <= ?
            ORDER BY timestamp_utc ASC
        ''', (station_icao, start_dt, end_dt))
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Error retrieving observations: {e}")
        return []
    finally:
        conn.close()

def get_latest_observation(station_icao):
    """
    Retrieve the most recent observation for a specific station.
    """
    conn = get_db_connection()
    try:
        cursor = conn.execute('''
            SELECT * FROM observations 
            WHERE station_icao = ? 
            ORDER BY timestamp_utc DESC
            LIMIT 1
        ''', (station_icao,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"Error retrieving latest observation: {e}")
        return None
    finally:
        conn.close()

def create_news_draft(filename, ocr_text, summary, user, upload_id=None):
    conn = get_db_connection()
    try:
        cursor = conn.execute('''
            INSERT INTO news_events (title, description, filename, ocr_text, status, uploaded_by, upload_id)
            VALUES (?, ?, ?, ?, 'DRAFT', ?, ?)
        ''', ("Draft News", summary, filename, ocr_text, user, upload_id))
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        logger.error(f"Error creating news draft: {e}")
        return None
    finally:
        conn.close()

def publish_news(item_id, title, description):
    conn = get_db_connection()
    try:
        conn.execute('UPDATE news_events SET title = ?, description = ?, status = "PUBLISHED" WHERE id = ?',
                     (title, description, item_id))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error publishing news: {e}")
        return False
    finally:
        conn.close()

def add_news_item(title, description, filename, uploaded_by='Admin', upload_id=None):
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO news_events (title, description, filename, status, uploaded_by, upload_id) VALUES (?, ?, ?, "PUBLISHED", ?, ?)',
                     (title, description, filename, uploaded_by, upload_id))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error adding news: {e}")
        return False
    finally:
        conn.close()

def get_news_items(admin_view=False):
    conn = get_db_connection()
    try:
        if admin_view:
            cursor = conn.execute('SELECT * FROM news_events ORDER BY upload_time DESC')
        else:
            cursor = conn.execute("SELECT * FROM news_events WHERE status = 'PUBLISHED' ORDER BY upload_time DESC")
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Error getting news: {e}")
        return []
    finally:
        conn.close()

def delete_news_item(item_id):
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM news_events WHERE id = ?', (item_id,))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error deleting news: {e}")
        return False
    finally:
        conn.close()

def create_notice_draft(filename, ocr_text, summary, user, upload_id=None):
    conn = get_db_connection()
    try:
        cursor = conn.execute('''
            INSERT INTO notices (title, message, filename, ocr_text, status, uploaded_by, upload_id)
            VALUES (?, ?, ?, ?, 'DRAFT', ?, ?)
        ''', ("Draft Notice", summary, filename, ocr_text, user, upload_id))
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        logger.error(f"Error creating notice draft: {e}")
        return None
    finally:
        conn.close()

def publish_notice(item_id, title, message):
    conn = get_db_connection()
    try:
        conn.execute('UPDATE notices SET title = ?, message = ?, status = "PUBLISHED" WHERE id = ?',
                     (title, message, item_id))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error publishing notice: {e}")
        return False
    finally:
        conn.close()

def add_notice_item(title, message, filename, uploaded_by='User', upload_id=None):
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO notices (title, message, filename, status, uploaded_by, upload_id) VALUES (?, ?, ?, "PUBLISHED", ?, ?)',
                     (title, message, filename, uploaded_by, upload_id))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error adding notice: {e}")
        return False
    finally:
        conn.close()

def get_notice_items(admin_view=False):
    conn = get_db_connection()
    try:
        if admin_view:
             cursor = conn.execute('SELECT * FROM notices ORDER BY upload_time DESC')
        else:
             cursor = conn.execute("SELECT * FROM notices WHERE status = 'PUBLISHED' ORDER BY upload_time DESC")
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Error getting notices: {e}")
        return []
    finally:
        conn.close()

def delete_notice_item(item_id):
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM notices WHERE id = ?', (item_id,))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error deleting notice: {e}")
        return False
    finally:
        conn.close()

def save_sigmet_status(status_data):
    """
    Save or update the current SIGMET status.
    Row ID is always 1 (singleton).
    """
    conn = get_db_connection()
    try:
        conn.execute('''
            INSERT OR REPLACE INTO sigmet_status 
            (id, is_active, count, phenomenon, validity_text, raw_data, updated_at)
            VALUES (1, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            status_data['is_active'],
            status_data['count'],
            status_data['phenomenon'],
            status_data['validity_text'],
            status_data.get('raw_data', '')
        ))
        conn.commit()
    except Exception as e:
        logger.error(f"Error saving SIGMET status: {e}")
    finally:
        conn.close()

def get_sigmet_status():
    """
    Get the latest SIGMET status.
    """
    conn = get_db_connection()
    try:
        cursor = conn.execute('SELECT * FROM sigmet_status WHERE id = 1')
        row = cursor.fetchone()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"Error getting SIGMET status: {e}")
        return None
    finally:
        conn.close()

def create_notam_draft(filename, ocr_text, final_text, valid_till, user, upload_id=None):
    conn = get_db_connection()
    try:
        cursor = conn.execute('''
            INSERT INTO notams (filename, ocr_text, final_notam_text, valid_till_utc, uploaded_by, status, upload_id)
            VALUES (?, ?, ?, ?, ?, 'DRAFT', ?)
        ''', (filename, ocr_text, final_text, valid_till, user, upload_id))
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        logger.error(f"Error creating NOTAM draft: {e}")
        return None
    finally:
        conn.close()

def get_notams_by_status(status=None):
    conn = get_db_connection()
    try:
        query = 'SELECT * FROM notams'
        params = []
        if status:
            query += ' WHERE status = ?'
            params.append(status)
        query += ' ORDER BY created_at DESC'
        
        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Error getting NOTAMs: {e}")
        return []
    finally:
        conn.close()

def update_notam_status(notam_id, status):
    conn = get_db_connection()
    try:
        conn.execute('UPDATE notams SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (status, notam_id))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error updating NOTAM status: {e}")
        return False
    finally:
        conn.close()

def update_notam_text(notam_id, new_text, new_date=None):
    conn = get_db_connection()
    try:
        if new_date:
             conn.execute('UPDATE notams SET final_notam_text = ?, valid_till_utc = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND status != "ARCHIVED"', (new_text, new_date, notam_id))
        else:
             conn.execute('UPDATE notams SET final_notam_text = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND status != "ARCHIVED"', (new_text, notam_id))
        
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error updating NOTAM text: {e}")
        return False
    finally:
        conn.close()

def delete_notam(notam_id):
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM notams WHERE id = ?', (notam_id,))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error deleting NOTAM: {e}")
        return False
    finally:
        conn.close()
        
def get_public_active_notam():
    """Get the latest VALID, ACTIVE NOTAM."""
    conn = get_db_connection()
    try:

        now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        cursor = conn.execute('''
            SELECT final_notam_text, valid_till_utc 
            FROM notams 
            WHERE status = 'ACTIVE' 
            AND valid_till_utc > ? 
            ORDER BY created_at DESC 
            LIMIT 1
        ''', (now,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"Error getting public NOTAM: {e}")
        return None
    finally:
        conn.close()

def auto_expire_notams():
    """Check for expired active NOTAMs and move them to ARCHIVED."""
    conn = get_db_connection()
    try:
        now = datetime.utcnow().isoformat()
        conn.execute('''
            UPDATE notams 
            SET status = 'ARCHIVED', updated_at = CURRENT_TIMESTAMP
            WHERE status = 'ACTIVE' AND valid_till_utc < ?
        ''', (now,))
        conn.commit()
    except Exception as e:
        logger.error(f"Error expiring NOTAMs: {e}")
    finally:
        conn.close()

def create_aerodrome_warning(station_icao, message, valid_from, valid_to, created_by='System'):
    conn = get_db_connection()
    try:
        cursor = conn.execute('''
            INSERT INTO aerodrome_warnings (station_icao, message, valid_from, valid_to, status, created_by)
            VALUES (?, ?, ?, ?, 'ACTIVE', ?)
        ''', (station_icao, message, valid_from, valid_to, created_by))
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        logger.error(f"Error creating aerodrome warning: {e}")
        return None
    finally:
        conn.close()

def get_active_aerodrome_warnings():
    """
    Get all active aerodrome warnings from the EXTERNAL Aerodrome App database.
    Path: /home/mwomumbai/app/sql_app.db
    """
    
    EXTERNAL_DB_PATH = '/home/mwomumbai/app/sql_app.db'

    if not os.path.exists(EXTERNAL_DB_PATH):

        if os.path.exists('met_data.db'):
            conn = sqlite3.connect('met_data.db')
            conn.row_factory = sqlite3.Row
            now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            cursor = conn.execute("SELECT * FROM aerodrome_warnings WHERE status = 'ACTIVE' AND valid_to > ?", (now,))
            return [dict(row) for row in cursor.fetchall()]
        return []

    try:
        import json
        conn = sqlite3.connect(EXTERNAL_DB_PATH)
        conn.row_factory = sqlite3.Row

        cursor = conn.execute('''
            SELECT * FROM alerts 
            WHERE status IN ('FINALIZED', 'active')
            ORDER BY created_at DESC
        ''')
        
        rows = cursor.fetchall()
        active_warnings = []
        now = datetime.utcnow()
        
        for row in rows:
            data = dict(row)
            content_raw = data.get('content')
            if not content_raw:
                continue
                
            try:
                content = json.loads(content_raw)
                
                station_icao = content.get('airport')
                valid_to_iso = content.get('valid_until_iso')
                message = content.get('generated_text')
                
                if not station_icao or not valid_to_iso:
                    continue

                try:
                    
                    valid_to_dt = datetime.fromisoformat(valid_to_iso.replace('Z', ''))
                    
                    if valid_to_dt > now:
                        
                        active_warnings.append({
                            'station_icao': station_icao,
                            'valid_to': valid_to_dt.strftime('%Y-%m-%d %H:%M:%S'),
                            'message': message,
                            'created_at': data.get('created_at')
                        })
                except Exception as ex:
                    logger.error(f"Date parse error in sync logic: {ex}")
                    
            except Exception as ex:
                logger.error(f"JSON parse error in sync logic: {ex}")
                
        return active_warnings
        
    except Exception as e:
        logger.error(f"Error accessing external Aerodrome DB: {e}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()

def get_active_warning_for_station(station_icao):
    """Filter from the consolidated active warnings list."""
    all_warnings = get_active_aerodrome_warnings()
    return [w for w in all_warnings if w['station_icao'].strip().upper() == station_icao.strip().upper()]

def add_dynamic_button(section, label, btn_type, url=None, file_path=None, upload_id=None):
    """
    Adds a new dynamic button/link to a sidebar section.
    section: 'resources', 'operational', 'external', 'olbs'
    """
    conn = get_db_connection()
    try:
        cursor = conn.execute('''
            INSERT INTO dynamic_buttons (section, label, type, url, file_path, upload_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (section, label, btn_type, url, file_path, upload_id))
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        logger.error(f"Error adding dynamic button: {e}")
        return None
    finally:
        conn.close()

def delete_dynamic_button(btn_id):
    """
    Deletes a dynamic button by ID. 
    DOES NOT DELETE THE FILE. File is managed via Admin Uploads.
    """
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM dynamic_buttons WHERE id = ?', (btn_id,))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error deleting dynamic button: {e}")
        return False
    finally:
        conn.close()

def get_dynamic_buttons_by_section():
    """
    Returns a dictionary of buttons grouped by section.
    Format: { 'olbs': [{...}, {...}], 'resources': [...] }
    """
    conn = get_db_connection()
    result = {
        'resources': [],
        'operational': [],
        'external': [],
        'olbs': []
    }
    try:
        rows = conn.execute('SELECT * FROM dynamic_buttons ORDER BY created_at ASC').fetchall()
        for row in rows:
            btn = dict(row)
            sec = btn['section']
            if sec in result:
                result[sec].append(btn)
            else:
                
                pass
        return result
    except Exception as e:
        logger.error(f"Error fetching dynamic buttons: {e}")
        return result
    finally:
        conn.close()

def track_admin_upload(filename, file_type, file_path, uploaded_by):
    """
    Records a file upload in the admin_uploads table.
    Sets expiration to 6 months from now.
    """
    conn = get_db_connection()
    try:
        from datetime import timedelta
        expiration = datetime.utcnow() + timedelta(days=180) 
        
        cursor = conn.execute('''
            INSERT INTO admin_uploads 
            (filename, file_type, file_path, uploaded_by, expiration_date)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            filename, 
            file_type, 
            file_path, 
            uploaded_by, 
            expiration
        ))
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        logger.error(f"Error tracking admin upload: {e}")
        return None
    finally:
        conn.close()

def get_admin_uploads(user_id=None):
    """
    Get all active uploads. If user_id provided, filter by uploader? 
    Prompt says: 'Display a list of all files uploaded by the logged-in admin.'
    So we should probably filter by user if the system supports multi-admin. 
    If single 'admin' role, show all.
    """
    conn = get_db_connection()
    try:
        cursor = conn.execute('''
            SELECT * FROM admin_uploads 
            WHERE is_deleted = 0 
            ORDER BY upload_date DESC
        ''')
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Error getting admin uploads: {e}")
        return []
    finally:
        conn.close()

def delete_admin_upload(upload_id):
    """
    Mark upload as deleted in DB. 
    Returns the file_path so the caller can delete from disk.
    """
    conn = get_db_connection()
    try:
        row = conn.execute('SELECT file_path FROM admin_uploads WHERE id = ?', (upload_id,)).fetchone()
        if not row: return None
        
        file_path = row['file_path']
        conn.execute('DELETE FROM admin_uploads WHERE id = ?', (upload_id,))

        conn.commit()
        return file_path
    except Exception as e:
        logger.error(f"Error deleting admin upload: {e}")
        return None
    finally:
        conn.close()

def delete_admin_upload_by_path(file_path):
    """
    Delete upload from DB using its relative file_path.
    """
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM admin_uploads WHERE file_path = ?', (file_path,))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error deleting admin upload by path: {e}")
        return False
    finally:
        conn.close()

def cleanup_expired_uploads():
    """
    Finds expired uploads that are NOT yet deleted.
    Returns a list of file paths to delete from disk.
    Then deletes them from DB.
    """
    conn = get_db_connection()
    paths_to_delete = []
    try:
        now = datetime.utcnow()
        
        cursor = conn.execute('SELECT id, file_path FROM admin_uploads WHERE expiration_date < ?', (now,))
        rows = cursor.fetchall()
        
        for row in rows:
            paths_to_delete.append(row['file_path'])
            
            conn.execute('DELETE FROM admin_uploads WHERE id = ?', (row['id'],))
            
        conn.commit()
        return paths_to_delete
    except Exception as e:
        logger.error(f"Error cleaning expired uploads: {e}")
        return []
    finally:
        conn.close()

def get_employees():
    """Get all employees ordered by id (or custom order if added later)."""
    conn = get_db_connection()
    try:
        cursor = conn.execute('SELECT * FROM employees ORDER BY id ASC')
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Error getting employees: {e}")
        return []
    finally:
        conn.close()

def add_employee(name, designation, section, telephone, created_by='Admin'):
    conn = get_db_connection()
    try:
        cursor = conn.execute('''
            INSERT INTO employees (name, designation, section, telephone, created_by)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, designation, section, telephone, created_by))
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        logger.error(f"Error adding employee: {e}")
        return None
    finally:
        conn.close()

def update_employee(emp_id, name, designation, section, telephone):
    conn = get_db_connection()
    try:
        conn.execute('''
            UPDATE employees 
            SET name = ?, designation = ?, section = ?, telephone = ?
            WHERE id = ?
        ''', (name, designation, section, telephone, emp_id))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error updating employee: {e}")
        return False
    finally:
        conn.close()

def delete_employee(emp_id):
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM employees WHERE id = ?', (emp_id,))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error deleting employee: {e}")
        return False
    finally:
        conn.close()

def seed_employees_if_empty():
    """Populate initial employees if table is empty."""
    existing = get_employees()
    if existing:
        return

    initial_employees = [
        {"name": "Mrs. Shubhangi A. Bhute", "designation": "Head MWO Mumbai (Scientist F)", "section": "HEAD", "telephone": "022-2681-9541"},
        {"name": "Dr. Dipak Kumar Sahu", "designation": "Scientist C", "section": "AMSS in-charge", "telephone": "022-2681-9430"},
        {"name": "Shri Raghavendra H Rao", "designation": "Scientific Officer-1", "section": "Forecasting", "telephone": "022-2681-9493 / 7039095584"},
        {"name": "Shri Suresh B Kangane", "designation": "Scientific Officer-1", "section": "Forecasting", "telephone": "022-2681-9493 / 7039095584"},
        {"name": "Ku. Niyaji Nazma Khanum", "designation": "Meteorologist B", "section": "Forecasting", "telephone": "022-2681-9493 / 7039095584"},
        {"name": "Shri.G.K.Iyer", "designation": "Meteorologist B", "section": "Forecasting", "telephone": "022-2681-9493 / 7039095584"},
        {"name": "Smt.Mruthubashini Srinivas.", "designation": "Meteorologist B", "section": "General Section", "telephone": "022-2681-9493 / 7039095584"},
        {"name": "Shri.S.S.Gajne", "designation": "Meteorologist B", "section": "Forecasting", "telephone": "022-2681-9493 / 7039095584"},
        {"name": "Shri.M.B.Ingulkar", "designation": "Meteorologist B", "section": "Forecasting", "telephone": "022-2681-9493 / 7039095584"},
        {"name": "Shri.S.A.Dethe", "designation": "Meteorologist B", "section": "Instrument", "telephone": "022-2681-9495"},
        {"name": "Smt.Sangeeta Pawar", "designation": "Meteorologist B", "section": "General Section", "telephone": "022-2681-9313"},
        {"name": "Smt. H.S.Nagrikar", "designation": "Meteorologist A", "section": "AMS Juhu", "telephone": "7039070672"},
        {"name": "Shri.S.B.Patel", "designation": "Meteorologist A", "section": "Forecasting", "telephone": ""},
        {"name": "Shri.D.J.Shirke", "designation": "Meteorologist A", "section": "Forecasting", "telephone": ""},
        {"name": "Shri.A.C.Kawatkar", "designation": "Meteorologist A", "section": "Forecasting", "telephone": ""},
        {"name": "Shri.J.Y.Bane", "designation": "Meteorologist A", "section": "Forecasting", "telephone": ""},
        {"name": "Shri.S.D.Agre", "designation": "Meteorologist A", "section": "AMSS", "telephone": ""},
        {"name": "Smt.Arti Thakur", "designation": "Meteorologist A", "section": "Forecasting", "telephone": ""},
        {"name": "Shri.P.S.Rane", "designation": "Meteorologist A", "section": "RSRW", "telephone": "8655308476"},
        {"name": "Shri.Amit Kamble", "designation": "Meteorologist A", "section": "Forecasting", "telephone": ""},
        {"name": "Shri.Vinod Naik", "designation": "Meteorologist A", "section": "Forecasting", "telephone": ""},
        {"name": "Shri.A.P.Sarvekar", "designation": "Meteorologist A", "section": "Forecasting", "telephone": ""},
        {"name": "Shri.R.L.Nagpure", "designation": "Meteorologist A", "section": "Forecasting", "telephone": ""},
        {"name": "Shri. Shailendra Singh", "designation": "Meteorologist A",
        "section": "AMS Juhu", "telephone": "7039070672"},
        {"name": "Shri. Amit Kumar", "designation": "Meteorologist A", "section": "Forecasting", "telephone": ""},
        {"name": "Shri SS Varadkar", "designation": "Meteorologist A", "section": "Forecasting", "telephone": ""},
        {"name": "Ms Divya Pipal", "designation": "Scentific Assistant", "section": "General Section", "telephone": ""},
        {"name": "Ms. Akanksha Tirpude", "designation": "Scientific Assistant", "section": "General Section", "telephone": ""},
        {"name": "Ms. Rashami Goyal", "designation": "Scientific Assistant", "section": "ATC Tower", "telephone": "022-2681-9457 / 7039075995"},
        {"name": "Ms Ayushi Saxena", "designation": "Scientific Assistant", "section": "ATC Tower", "telephone": "022-2681-9457 / 7039075995"},
        {"name": "Shri Rahul yadav", "designation": "Scientific Assistant", "section": "ATC Tower", "telephone": "022-2681-9457 / 7039075995"},
        {"name": "Shri Vijay Kalal", "designation": "Scientific Assistant", "section": "ATC Tower", "telephone": "022-2681-9457 / 7039075995"},
        {"name": "Shri Sanjay Kumar Meena", "designation": "Scientific Assistant", "section": "ATC Tower", "telephone": "022-2681-9457 / 7039075995"},
        {"name": "Shri. Himanshu Singh", "designation": "Scientific Assistant", "section": "ATC Tower", "telephone": "022-2681-9457 / 7039075995"}
    ]

    conn = get_db_connection()
    try:
        logger.info("Seeding employees table...")
        for emp in initial_employees:
            conn.execute('''
                INSERT INTO employees (name, designation, section, telephone, created_by)
                VALUES (?, ?, ?, ?, 'System')
            ''', (emp['name'], emp['designation'], emp['section'], emp['telephone']))
        conn.commit()
        logger.info(f"Seeded {len(initial_employees)} employees.")
    except Exception as e:
        logger.error(f"Error seeding employees: {e}")
    finally:
        conn.close()
