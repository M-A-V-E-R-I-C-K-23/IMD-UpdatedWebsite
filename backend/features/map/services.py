from core.config import STATIONS, STATION_STATES, STATE_BOUNDARIES

def get_required_state_boundaries():
    """
    Determine which state boundaries are needed based on configured airports
    and return the boundary paths.
    """
    required_states = set()
    for icao in STATIONS.keys():
        state = STATION_STATES.get(icao, "Maharashtra")
        required_states.add(state)
    
    # Get boundaries for required states
    state_boundaries = {state: STATE_BOUNDARIES.get(state, []) for state in required_states}
    
    return required_states, state_boundaries
