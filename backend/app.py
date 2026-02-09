import os
from flask import Flask
from flask_cors import CORS
from flask_compress import Compress
from core.config import UPLOAD_FOLDER, MAX_CONTENT_LENGTH, SECRET_KEY, DB_NAME
from core.extensions import scheduler, logger
from database import init_db, cleanup_expired_uploads

from features.map import map_bp
from features.dashboard import dashboard_bp, configure_rvr_scheduler
from features.notam import notam_bp, configure_notam_scheduler
from features.ogimet import ogimet_bp, configure_scheduler

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
    app.run(debug=True, port=5000)
