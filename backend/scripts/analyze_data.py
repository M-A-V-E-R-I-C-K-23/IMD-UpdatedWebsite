from database import get_db_connection

conn = get_db_connection()
stations = ['VASL', 'VOND', 'VAKP']
print(f"{'STATION':<8} {'DATE':<12} {'COUNT':<6} {'START_TIME':<10} {'END_TIME':<10}")
print("-" * 50)

for station in stations:
    rows = conn.execute('''
        SELECT 
            date(timestamp_utc) as d, 
            COUNT(*) as c, 
            MIN(time(timestamp_utc)) as start_t, 
            MAX(time(timestamp_utc)) as end_t 
        FROM observations 
        WHERE station_icao = ? 
        GROUP BY d
        ORDER BY d DESC
    ''', (station,)).fetchall()
    
    for row in rows:
        print(f"{station:<8} {row['d']:<12} {row['c']:<6} {row['start_t']:<10} {row['end_t']:<10}")
