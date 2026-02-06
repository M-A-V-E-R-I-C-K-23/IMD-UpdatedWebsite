from .routes import dashboard_bp
from .rvr_image_service import capture_rvr_snapshot
from apscheduler.triggers.interval import IntervalTrigger

def configure_rvr_scheduler(scheduler):
    """Registers the RVR screenshot job."""
    if not scheduler.get_job('rvr_screenshot_job'):
        scheduler.add_job(
            func=capture_rvr_snapshot,
            trigger=IntervalTrigger(minutes=2),
            id='rvr_screenshot_job',
            name='Capture RVR Screenshot',
            max_instances=1,
            coalesce=True,
            replace_existing=True
        )
