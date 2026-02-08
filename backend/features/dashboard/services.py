from datetime import datetime, timedelta
from core.config import MIN_OBSERVATIONS_PER_DAY, MIN_HOUR_SPREAD
from core.extensions import logger
from .rvr_screenshot import fetch_rvr_screenshot

def fetch_live_rvr(station_code="VABB"):
    """
    Fetch live RVR data.
    Method: STRICT SCREENSHOT ONLY (Selenium + OCR).
    """
    # No caching allowed per requirements.
    # No requests allowed.
    
    return fetch_rvr_screenshot()

def validate_day_completeness(observations):
    """
    Validate if a day has sufficient data coverage for the full 24-hour period.
    
    Returns:
        tuple: (is_complete: bool, coverage_info: dict)
    """
    # ... logic unchanged ...
    if not observations:
        return False, {
            "status": "no_data",
            "message": "No observations available",
            "observation_count": 0,
            "hours_covered": []
        }
    
    # Extract hours from observations
    hours_with_data = set()
    for obs in observations:
        try:
            obs_dt = datetime.fromisoformat(obs['timestamp_utc'])
            hours_with_data.add(obs_dt.hour)
        except:
            continue
    
    observation_count = len(observations)
    hours_covered = sorted(list(hours_with_data))
    
    # Calculate hour spread (difference between max and min hour)
    if hours_covered:
        hour_spread = max(hours_covered) - min(hours_covered)
    else:
        hour_spread = 0
    
    # Determine completeness
    is_complete = (
        observation_count >= MIN_OBSERVATIONS_PER_DAY and
        hour_spread >= MIN_HOUR_SPREAD
    )
    
    status = "complete" if is_complete else "incomplete"
    
    return is_complete, {
        "status": status,
        "observation_count": observation_count,
        "hours_covered": hours_covered,
        "hour_spread": hour_spread,
        "min_hour": min(hours_covered) if hours_covered else None,
        "max_hour": max(hours_covered) if hours_covered else None
    }

import math

def format_observations(observations):
    """
    Format a list of observation dictionaries for the frontend.
    """
    formatted = []
    for obs in observations:
        try:
            obs_dt = datetime.fromisoformat(obs['timestamp_utc'])
            time_str = obs_dt.strftime("%H:%M")
            
            # Calculate Relative Humidity (RH)
            # RH = 100 * (EXP((17.625 * TD) / (243.04 + TD)) / EXP((17.625 * T) / (243.04 + T)))
            t = obs.get('temperature')
            td = obs.get('dew_point')
            rh = None
            
            if t is not None and td is not None:
                try:
                    # Ensure float
                    t = float(t)
                    td = float(td)
                    
                    numerator = math.exp((17.625 * td) / (243.04 + td))
                    denominator = math.exp((17.625 * t) / (243.04 + t))
                    
                    rh_val = 100 * (numerator / denominator)
                    
                    # Round to 2 decimals and clamp 0-100
                    rh = round(max(0, min(100, rh_val)), 2)
                except Exception as calc_err:
                    logger.warning(f"RH split calc error: {calc_err}")
                    rh = None

            formatted.append({
                "time": time_str,
                "hour": obs_dt.hour,
                "full_ts": obs['timestamp_utc'],
                "temperature": obs['temperature'],
                "dew_point": obs['dew_point'],
                "relative_humidity": rh,
                "wind_speed": obs['wind_speed'],
                "wind_direction": obs['wind_direction'],
                "visibility": obs['visibility'],
                "qnh": obs['qnh']
            })
        except Exception as e:
            logger.error(f"Error processing observation: {e}")
            continue
    return formatted
