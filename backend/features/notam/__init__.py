from .routes import notam_bp
from .services import check_expired_notams

def configure_notam_scheduler(scheduler):
    scheduler.add_job(func=check_expired_notams, trigger="interval", minutes=60)

