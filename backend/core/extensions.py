from apscheduler.schedulers.background import BackgroundScheduler
import logging

# Initialize Scheduler
scheduler = BackgroundScheduler()

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mwo_app")
