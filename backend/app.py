import os
import sys
from flask import Flask, jsonify
from flask_cors import CORS
from flask_compress import Compress
from core.config import UPLOAD_FOLDER, MAX_CONTENT_LENGTH, SECRET_KEY, DB_NAME
from core.extensions import scheduler, logger
from database import init_db, cleanup_expired_uploads

from features.map import map_bp
from features.dashboard import dashboard_bp, configure_rvr_scheduler
from features.notam import notam_bp, configure_notam_scheduler
from features.ogimet import ogimet_bp, configure_scheduler
from features.documents.routes import documents_bp

TAFOR_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'tafor'))
if TAFOR_DIR not in sys.path:
    sys.path.insert(0, TAFOR_DIR)

from scraper import IMDScraper, OgimetScraper
from taf_generator import TafGenerator
from metar_parser import decode_metar

def create_app():
    app = Flask(__name__, 
                static_folder='../frontend/static',
                template_folder='templates')
    
    app.config['COMPRESS_MIMETYPES'] = [
        'text/html', 
        'text/css', 
        'text/xml', 
        'application/json', 
        'application/javascript', 
        'application/geo+json'
    ]
    Compress(app)
    CORS(app)

    app.secret_key = SECRET_KEY
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
    
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'news'), exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'notices'), exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'notams'), exist_ok=True)
    
    app.register_blueprint(map_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(notam_bp)
    app.register_blueprint(ogimet_bp)
    app.register_blueprint(documents_bp)

    @app.route('/tafor/api/taf/<station>', methods=['GET'])
    def get_local_taf(station):
        station = station.upper()
        imd_scraper = IMDScraper()
        ogimet_scraper = OgimetScraper()
        generator = TafGenerator()

        imd_data = imd_scraper.fetch_data(station)
        ogimet_data = ogimet_scraper.fetch_data(station)

        if "error" in imd_data:
            return jsonify({"error": f"IMD Error: {imd_data['error']}"}), 500
        if "error" in ogimet_data:
            return jsonify({"error": f"Ogimet Error: {ogimet_data['error']}"}), 500

        try:
            short_taf = generator.generate_short_taf(imd_data, ogimet_data)

            parsed_metar = None
            if "raw_metar" in ogimet_data and "dt" in ogimet_data:
                parsed_metar = decode_metar(ogimet_data["raw_metar"], station, ogimet_data["dt"])
                if parsed_metar and "timestamp_utc" in parsed_metar:
                    parsed_metar["timestamp_utc"] = parsed_metar["timestamp_utc"].isoformat() + "Z"

            return jsonify({
                "short_taf": short_taf,
                "station": station,
                "ogimet_metar": parsed_metar
            })
        except Exception as e:
            return jsonify({"error": f"Generation Error: {str(e)}"}), 500
    
    with app.app_context():
        init_db()
        configure_scheduler()
        configure_notam_scheduler(scheduler)
        configure_rvr_scheduler(scheduler)
        
        if not scheduler.get_job('cleanup_uploads'):
            scheduler.add_job(
                func=cleanup_expired_uploads,
                trigger='interval',
                hours=24,
                id='cleanup_uploads',
                replace_existing=True
            )
        
    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5000, use_reloader=False)
