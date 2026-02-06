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

    # Normalize
    metar = raw_metar.strip()

    # Temperature and Dew Point (e.g., 24/18 or M05/M08)
    # Matches 2 digits, optional M (minus), slash, optional M, 2 digits
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

    # Wind (e.g., 34010KT, 09005MPS, VRB02KT)
    # Matches 3 digits (dir) or VRB, followed by 2-3 digits (speed), followed by KT or MPS
    wind_pattern = r'(\d{3}|VRB)(\d{2,3})(KT|MPS)'
    wind_match = re.search(wind_pattern, metar)
    if wind_match:
        try:
            direction_str = wind_match.group(1)
            speed_str = wind_match.group(2)
            unit = wind_match.group(3)

            # Direction
            if direction_str == 'VRB':
                data['wind_direction'] = 0 # Convention for variable, or handle as special
            else:
                data['wind_direction'] = int(direction_str)

            # Speed
            speed = int(speed_str)
            if unit == 'MPS':
                speed = int(speed * 1.94384) # Convert MPS to Knots approx
            data['wind_speed'] = speed
        except ValueError:
            pass

    # Visibility (e.g., 9999, 4000, 0800)
    # 4 digits
    vis_pattern = r'\s(\d{4})\s'
    vis_match = re.search(vis_pattern, metar)
    if vis_match:
        try:
            data['visibility'] = int(vis_match.group(1))
        except ValueError:
            pass
    # Helper for CAVOK? (Means visibility >= 10km)
    if 'CAVOK' in metar:
        data['visibility'] = 10000

    # QNH / Pressure (e.g., Q1012, A2992)
    qnh_pattern = r'Q(\d{4})'
    qnh_match = re.search(qnh_pattern, metar)
    if qnh_match:
        try:
            data['qnh'] = float(qnh_match.group(1))
        except ValueError:
            pass
    else:
        # Try A-setting (Inches of Mercury) - unlikely for IMD but good for robustness
        a_pattern = r'A(\d{4})'
        a_match = re.search(a_pattern, metar)
        if a_match:
            try:
                inhg = float(a_match.group(1)) / 100.0
                data['qnh'] = int(inhg * 33.8639) # Convert to hPa
            except ValueError:
                pass

    return data
