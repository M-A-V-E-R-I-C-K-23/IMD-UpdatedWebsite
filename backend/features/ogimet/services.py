import requests
from datetime import datetime, timedelta
import re
from core.extensions import logger, scheduler
from core.config import STATIONS
from database import save_observation, save_sigmet_status
from .parser import decode_metar

def fetch_metar_data():
    """
    Fetches METAR data from NOAA AWC for all configured stations.
    """
    logger.info("Starting METAR data fetch...")
    
    for icao in STATIONS.keys():
        try:
            fetch_station_data(icao)
        except Exception as e:
            logger.error(f"Failed to fetch data for {icao}: {e}")

    logger.info("Data fetch completed.")

def fetch_station_data(icao, hours=None, start_dt=None, end_dt=None):
    """
    Fetches and processes data for a single station using NOAA AWC API.
    Supports either 'hours' (last N hours) or explicit time window (start_dt to end_dt).
    """
    # NOAA Aviation Weather Center API
    url = "https://aviationweather.gov/api/data/metar"
    params = {
        'ids': icao,
        'format': 'raw',
        'format': 'raw',
    }
    
    if start_dt and end_dt:
        # Calculate hours from now back to start_dt
        # NOAA API uses 'hours' (hours before now)
        # So we need to cover the range from start_dt to now
        diff = datetime.utcnow() - start_dt
        hours_needed = int(diff.total_seconds() / 3600) + 2 # +2 for buffer
        params['hours'] = hours_needed
    else:
        params['hours'] = hours if hours else 120
    
    headers = {
        'User-Agent': 'IMD-Dashboard/1.0'
    }
    
    response = requests.get(url, params=params, headers=headers, timeout=60)
    if response.status_code != 200:
        logger.error(f"AWC returned {response.status_code} for {icao}")
        return

    content = response.text
    
    if not content.strip():
        logger.warning(f"No data returned for {icao}")
        return
    
    # Parse raw METARs - each line is one METAR
    lines = content.strip().split('\n')
    
    count = 0
    for line in lines:
        line = line.strip()
        if not line or not line.startswith('METAR') and not line.startswith('SPECI'):
            # Some lines might be just raw METAR without prefix
            if not line.startswith(icao):
                continue
        
        raw_metar = line
        
        # Extract timestamp from METAR (format: ICAO DDHHMMZ ...)
        # Example: VABB 040700Z 01004KT ...
        ts_match = re.search(r'(\d{2})(\d{2})(\d{2})Z', raw_metar)
        if not ts_match:
            continue
        
        day = int(ts_match.group(1))
        hour = int(ts_match.group(2))
        minute = int(ts_match.group(3))
        
        # Construct the observation time (assume current month/year, adjust for day rollover)
        now = datetime.utcnow()
        try:
            obs_time = datetime(now.year, now.month, day, hour, minute)
            # If the day is in the future (e.g. day 28 but we're on day 3), it's last month
            if obs_time > now + timedelta(days=1):
                # Go back to previous month
                if now.month == 1:
                    obs_time = datetime(now.year - 1, 12, day, hour, minute)
                else:
                    obs_time = datetime(now.year, now.month - 1, day, hour, minute)
        except ValueError:
            continue
        
        # Decode
        decoded = decode_metar(raw_metar, icao, obs_time)
        if decoded:
            save_observation(decoded)
            count += 1
    
    logger.info(f"Saved {count} observations for {icao}")

def fetch_today_data():
    """
    Fetches METAR data for all stations for the current UTC day (00:00 to Now).
    """
    logger.info("Starting Today's data fetch...")
    now = datetime.utcnow()
    # Start of today UTC
    start_dt = datetime(now.year, now.month, now.day, 0, 0, 0)
    
    for icao in STATIONS.keys():
        try:
            # We want from 00:00 today up to now
            fetch_station_data(icao, start_dt=start_dt, end_dt=now)
        except Exception as e:
            logger.error(f"Failed to fetch today's data for {icao}: {e}")
            
    logger.info("Today's data fetch completed.")

def fetch_sigmet_data():
    """
    Fetches active SIGMETs from NOAA Aviation Weather Center for Mumbai FIR (VABF).
    Parses the JSON response and updates the system status.
    """
    logger.info("Starting SIGMET data fetch...")
    
    # Using the official JSON endpoint
    url = "https://aviationweather.gov/api/data/isigmet"
    params = {
        'format': 'json',
        #'loc': 'VABF' # Filter by FIR if API supports, otherwise we filter manually
    }
    
    headers = {
        'User-Agent': 'IMD-Dashboard/1.0 (Mumbai MWO)'
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        if response.status_code != 200:
            logger.error(f"SIGMET fetch failed: {response.status_code}")
            return
            
        data = response.json()
        
        # Filter for Mumbai FIR (VABF)
        # The API returns a list of features (GeoJSON-like) or objects
        # Structure varies, assuming list of objects based on typical AWC JSON
        
        active_sigmets = []
        
        for item in data:
            # Check different fields where FIR ID or Name might appear
            # 'firId', 'firName', 'qualifier', 'icaoId'
            # We are looking for VABF
            
            fir_id = item.get('firId', '').upper()
            icao_id = item.get('icaoId', '').upper()
            raw_text = item.get('rawSigmet', '').upper()
            
            # Match VABF or explicit mention of MUMBAI FIR
            if fir_id == 'VABF' or 'VABF' in raw_text or 'MUMBAI FIR' in raw_text:
                active_sigmets.append(item)
                
        # Determine Status
        if active_sigmets:
            # Extract details from the first active one (or aggregate)
            first = active_sigmets[0]
            
            # Try to get phenomenon (e.g., TS, TURB)
            # Sometimes in 'qualifier' or 'hazard' or parsed from text
            phenomenon = first.get('hazard', 'Unknown').upper()
            if not phenomenon or phenomenon == 'UNKNOWN':
                # Try regex on raw text
                match = re.search(r'(TS|TURB|ICE|MTW|DS|SS|VA|RDOACT|CHEM)', first.get('rawSigmet', ''), re.IGNORECASE)
                if match:
                    phenomenon = match.group(1).upper()
            
            # Validity
            valid_from = first.get('validTimeFrom', '')
            valid_to = first.get('validTimeTo', '')
            
            # Simplified validity text
            validity_text = f"{valid_from[11:16]} - {valid_to[11:16]} UTC" if valid_from and valid_to else "Active"
             
            status = {
                "is_active": True,
                "count": len(active_sigmets),
                "phenomenon": phenomenon,
                "validity_text": validity_text,
                "raw_data": str(active_sigmets) # Save raw for debugging
            }
        else:
            status = {
                "is_active": False,
                "count": 0,
                "phenomenon": None,
                "validity_text": None,
                "raw_data": ""
            }
            
        save_sigmet_status(status)
        logger.info(f"SIGMET fetch completed. Active: {status['is_active']}")
        
    except Exception as e:
        logger.error(f"Error executing SIGMET fetch: {e}")

def configure_scheduler():
    """
    Starts the APScheduler background task.
    """
    # Run METAR fetch every 30 minutes
    scheduler.add_job(func=fetch_metar_data, trigger="interval", minutes=30, next_run_time=datetime.now())
    
    # Run SIGMET fetch every 5 minutes
    scheduler.add_job(func=fetch_sigmet_data, trigger="interval", minutes=5, next_run_time=datetime.now() + timedelta(seconds=5))
    
    # Run Today's fetch every 10 minutes
    scheduler.add_job(func=fetch_today_data, trigger="interval", minutes=10, next_run_time=datetime.now() + timedelta(seconds=10))
    
    scheduler.start()
    logger.info("Scheduler started.")
