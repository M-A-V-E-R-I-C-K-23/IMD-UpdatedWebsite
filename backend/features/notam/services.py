from database import auto_expire_notams
from core.extensions import logger

def check_expired_notams():
    """Check for expired NOTAMs and archive them."""
    try:
        auto_expire_notams()
        
    except Exception as e:
        logger.error(f"Error checking expired NOTAMs: {e}")
