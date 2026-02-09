import re

def decode_metar(raw_metar, station_icao, observation_time):
    """
    Decodes a raw METAR string into a dictionary of parameters.
    
    Args:
        raw_metar (str): The raw METAR string.
        station_icao (str): ICAO code of the station.
        observation_time (datetime): The time of observation (UTC).

    Returns:
        dict: Decoded parameters or None if decoding fails significantly.
    """
    if not raw_metar:
        return None

    data = {
        'station_icao': station_icao,
        'timestamp_utc': observation_time,
        'raw_metar': raw_metar,
        'temperature': None,
        'dew_point': None,
        'wind_direction': None,
        'wind_speed': None,
        'visibility': None,
        'qnh': None
    }

    metar = raw_metar.strip()

    temp_pattern = r'(M?\d{2})/(M?\d{2})'
    temp_match = re.search(temp_pattern, metar)
    if temp_match:
        try:
            t_str = temp_match.group(1).replace('M', '-')
            d_str = temp_match.group(2).replace('M', '-')
            data['temperature'] = float(t_str)
            data['dew_point'] = float(d_str)
        except ValueError:
            pass

    wind_pattern = r'(\d{3}|VRB)(\d{2,3})(KT|MPS)'
    wind_match = re.search(wind_pattern, metar)
    if wind_match:
        try:
            direction_str = wind_match.group(1)
            speed_str = wind_match.group(2)
            unit = wind_match.group(3)

            if direction_str == 'VRB':
                data['wind_direction'] = 0 
            else:
                data['wind_direction'] = int(direction_str)

            speed = int(speed_str)
            if unit == 'MPS':
                speed = int(speed * 1.94384) 
            data['wind_speed'] = speed
        except ValueError:
            pass

    vis_pattern = r'\s(\d{4})\s'
    vis_match = re.search(vis_pattern, metar)
    if vis_match:
        try:
            data['visibility'] = int(vis_match.group(1))
        except ValueError:
            pass
    
    if 'CAVOK' in metar:
        data['visibility'] = 10000

    qnh_pattern = r'Q(\d{4})'
    qnh_match = re.search(qnh_pattern, metar)
    if qnh_match:
        try:
            data['qnh'] = float(qnh_match.group(1))
        except ValueError:
            pass
    else:
        
        a_pattern = r'A(\d{4})'
        a_match = re.search(a_pattern, metar)
        if a_match:
            try:
                inhg = float(a_match.group(1)) / 100.0
                data['qnh'] = int(inhg * 33.8639) 
            except ValueError:
                pass

    return data
