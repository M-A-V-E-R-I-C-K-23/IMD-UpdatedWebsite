from flask import Blueprint, render_template, request, jsonify
from datetime import datetime, timedelta, time
from core.config import STATIONS, DEFAULT_STATION
from core.extensions import logger
from database import get_observations, get_latest_observation
from features.ogimet.services import fetch_station_data
from .services import validate_day_completeness, format_observations, fetch_live_rvr

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/api/rvr/status')
def get_rvr_status():
    result = fetch_live_rvr()
    return jsonify(result)

@dashboard_bp.route('/dashboard/<station_code>')
def dashboard(station_code):
    if station_code not in STATIONS:
        return "Station not found", 404
    
    return render_template('dashboard.html', 
                         stations=STATIONS,
                         selected_station=station_code,
                         station_name=STATIONS[station_code])

@dashboard_bp.route('/api/data')
def get_data():
    station = request.args.get('station', DEFAULT_STATION)
    
    today = datetime.utcnow().date()
    
    candidate_days = []
    for i in range(1, 10):
        candidate_days.append(today - timedelta(days=i))
    
    today_start = datetime.combine(today, time(0, 0, 0))
    today_end = datetime.utcnow()
    
    today_obs = get_observations(station, today_start, today_end)
    formatted_today = format_observations(today_obs)
    
    today_data = {
        "label": "Today (Live)",
        "date": today.strftime("%Y-%m-%d"), 
        "data": formatted_today,
        "is_live": True
    }
    
    response_data = {
        "station": STATIONS.get(station, station),
        "station_code": station,
        "generated_at_utc": datetime.utcnow().isoformat(),
        "today_live": today_data,
        "days": []
    }
    
    complete_days_found = 0
    
    for d in candidate_days:
        if complete_days_found >= 3:
            break
            
        start_ts = datetime.combine(d, time(0, 0, 0))
        end_ts = datetime.combine(d, time(23, 59, 59))
        
        raw_obs = get_observations(station, start_ts, end_ts)
        
        is_complete, coverage_info = validate_day_completeness(raw_obs)
        
        formatted_obs = format_observations(raw_obs)
        
        day_data = {
            "date": d.strftime("%Y-%m-%d"),
            "label": d.strftime("%d %b %Y"),
            "is_complete": is_complete,
            "coverage": coverage_info,
            "data": formatted_obs
        }
        
        if is_complete:
            complete_days_found += 1
            response_data["days"].append(day_data)
        else:
            day_data["label"] = f"{d.strftime('%d %b %Y')} (Incomplete)"
            response_data["days"].append(day_data)
            complete_days_found += 1
        
    return jsonify(response_data)

@dashboard_bp.route('/api/status')
def get_status():
    today = datetime.utcnow().date()
    status_info = {
        "current_utc_time": datetime.utcnow().isoformat(),
        "stations": {}
    }
    
    for icao, name in STATIONS.items():
        station_status = {
            "name": name,
            "days": []
        }
        
        for i in range(1, 5):
            d = today - timedelta(days=i)
            start_ts = datetime.combine(d, time(0, 0, 0))
            end_ts = datetime.combine(d, time(23, 59, 59))
            
            raw_obs = get_observations(icao, start_ts, end_ts)
            is_complete, coverage_info = validate_day_completeness(raw_obs)
            
            station_status["days"].append({
                "date": d.strftime("%Y-%m-%d"),
                "is_complete": is_complete,
                "observation_count": coverage_info["observation_count"],
                "hour_spread": coverage_info.get("hour_spread", 0)
            })
        
        status_info["stations"][icao] = station_status
    
    return jsonify(status_info)

@dashboard_bp.route('/api/latest/<station_code>')
def get_latest(station_code):
    obs = get_latest_observation(station_code)
    
    is_stale = False
    if not obs:
        is_stale = True
    else:
        try:
            obs_dt = obs['timestamp_utc']
            if isinstance(obs_dt, str):
                obs_dt = datetime.fromisoformat(obs_dt)
            
            if (datetime.utcnow() - obs_dt) > timedelta(minutes=20):
                is_stale = True
        except Exception as e:
            logger.error(f"Date parse error in get_latest: {e}")
            is_stale = True

    if is_stale:
        logger.info(f"Data for {station_code} is stale/missing. Fetching live...")
        try:
            fetch_station_data(station_code, hours=2)
            obs = get_latest_observation(station_code)
        except Exception as e:
            logger.error(f"Live fetch failed: {e}")

    if not obs:
        return jsonify({"status": "no_data", "station": station_code, "message": "No data available even after fetch"}), 404
        
    ts_val = obs['timestamp_utc']
    if isinstance(ts_val, str):
        if not ts_val.endswith('Z') and '+' not in ts_val:
             ts_val = ts_val.replace(' ', 'T') + 'Z'
    elif isinstance(ts_val, datetime):
        ts_val = ts_val.isoformat()
        if not ts_val.endswith('Z') and '+' not in ts_val:
            ts_val += 'Z'

    return jsonify({
        "status": "success",
        "station": station_code,
        "data": {
            "timestamp_utc": ts_val,
            "temperature": obs['temperature'],
            "dew_point": obs['dew_point'],
            "wind_direction": obs['wind_direction'],
            "wind_speed": obs['wind_speed'],
            "visibility": obs['visibility'],
            "qnh": obs['qnh'],
            "raw_metar": obs['raw_metar']
        }
    })

@dashboard_bp.route('/api/live_data')
def get_live_data():
    station = request.args.get('station', DEFAULT_STATION)
    today = datetime.utcnow().date()
    
    today_start = datetime.combine(today, time(0, 0, 0))
    today_end = datetime.utcnow()
    
    today_obs = get_observations(station, today_start, today_end)
    formatted_today = format_observations(today_obs)
    
    return jsonify({
        "station": station,
        "generated_at_utc": datetime.utcnow().isoformat(),
        "today_live": {
            "label": "Today (Live)",
            "date": today.strftime("%Y-%m-%d"),
            "data": formatted_today,
            "is_live": True
        }
    })
