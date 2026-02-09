from apscheduler.schedulers.background import BackgroundScheduler
import logging

scheduler = BackgroundScheduler()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mwo_app")
