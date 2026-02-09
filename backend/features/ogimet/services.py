import requests
from datetime import datetime, timedelta
import re
from core.extensions import logger, scheduler
from core.config import STATIONS
from database import save_observation, save_sigmet_status
from .parser import decode_metar

def fetch_metar_data():
    logger.info("Starting METAR data fetch...")
    
    for icao in STATIONS.keys():
        try:
            fetch_station_data(icao)
        except Exception as e:
            logger.error(f"Failed to fetch data for {icao}: {e}")

    logger.info("Data fetch completed.")

def fetch_station_data(icao, hours=None, start_dt=None, end_dt=None):
    url = "https://aviationweather.gov/api/data/metar"
    params = {
        'ids': icao,
        'format': 'raw',
        'format': 'raw',
    }
    
    if start_dt and end_dt:
        diff = datetime.utcnow() - start_dt
        hours_needed = int(diff.total_seconds() / 3600) + 2 
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
    
    lines = content.strip().split('\n')
    
    count = 0
    for line in lines:
        line = line.strip()
        if not line or not line.startswith('METAR') and not line.startswith('SPECI'):
            if not line.startswith(icao):
                continue
        
        raw_metar = line
        
        ts_match = re.search(r'(\d{2})(\d{2})(\d{2})Z', raw_metar)
        if not ts_match:
            continue
        
        day = int(ts_match.group(1))
        hour = int(ts_match.group(2))
        minute = int(ts_match.group(3))
        
        now = datetime.utcnow()
        try:
            obs_time = datetime(now.year, now.month, day, hour, minute)
            if obs_time > now + timedelta(days=1):
                if now.month == 1:
                    obs_time = datetime(now.year - 1, 12, day, hour, minute)
                else:
                    obs_time = datetime(now.year, now.month - 1, day, hour, minute)
        except ValueError:
            continue
        
        decoded = decode_metar(raw_metar, icao, obs_time)
        if decoded:
            save_observation(decoded)
            count += 1
    
    logger.info(f"Saved {count} observations for {icao}")

def fetch_today_data():
    logger.info("Starting Today's data fetch...")
    now = datetime.utcnow()
    start_dt = datetime(now.year, now.month, now.day, 0, 0, 0)
    
    for icao in STATIONS.keys():
        try:
            fetch_station_data(icao, start_dt=start_dt, end_dt=now)
        except Exception as e:
            logger.error(f"Failed to fetch today's data for {icao}: {e}")
            
    logger.info("Today's data fetch completed.")

def fetch_sigmet_data():
    logger.info("Starting SIGMET data fetch...")
    
    url = "https://aviationweather.gov/api/data/isigmet"
    params = {
        'format': 'json',
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
        
        active_sigmets = []
        
        for item in data:
            fir_id = item.get('firId', '').upper()
            icao_id = item.get('icaoId', '').upper()
            raw_text = item.get('rawSigmet', '').upper()
            
            if fir_id == 'VABF' or 'VABF' in raw_text or 'MUMBAI FIR' in raw_text:
                active_sigmets.append(item)
                
        if active_sigmets:
            first = active_sigmets[0]
            
            phenomenon = first.get('hazard', 'Unknown').upper()
            if not phenomenon or phenomenon == 'UNKNOWN':
                match = re.search(r'(TS|TURB|ICE|MTW|DS|SS|VA|RDOACT|CHEM)', first.get('rawSigmet', ''), re.IGNORECASE)
                if match:
                    phenomenon = match.group(1).upper()
            
            valid_from = first.get('validTimeFrom', '')
            valid_to = first.get('validTimeTo', '')
            
            validity_text = f"{valid_from[11:16]} - {valid_to[11:16]} UTC" if valid_from and valid_to else "Active"
             
            status = {
                "is_active": True,
                "count": len(active_sigmets),
                "phenomenon": phenomenon,
                "validity_text": validity_text,
                "raw_data": str(active_sigmets)
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
    scheduler.add_job(func=fetch_metar_data, trigger="interval", minutes=30, next_run_time=datetime.now())
    
    scheduler.add_job(func=fetch_sigmet_data, trigger="interval", minutes=5, next_run_time=datetime.now() + timedelta(seconds=5))
    
    scheduler.add_job(func=fetch_today_data, trigger="interval", minutes=10, next_run_time=datetime.now() + timedelta(seconds=10))
    
    scheduler.start()
    logger.info("Scheduler started.")
