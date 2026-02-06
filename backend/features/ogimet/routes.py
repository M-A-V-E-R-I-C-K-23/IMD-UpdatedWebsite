# Optional: If we want to expose trigger routes here, we can.
from flask import Blueprint, jsonify
from .services import fetch_metar_data

ogimet_bp = Blueprint('ogimet', __name__)

@ogimet_bp.route('/api/trigger_fetch')
def trigger_fetch():
    """Helper to manually trigger fetch for testing."""
    fetch_metar_data()
    return jsonify({"status": "Fetch triggered"})
