import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from core.config import UPLOAD_FOLDER

logger = logging.getLogger("mwo_app")

RVR_URL = "http://rvrcamd.imd.gov.in:5000/live-rvr"
SCREENSHOT_PATH = os.path.join(os.getcwd(), '..', 'frontend', 'static', 'rvr', 'latest_rvr.png')
TEMP_SCREENSHOT_PATH = os.path.join(os.getcwd(), '..', 'frontend', 'static', 'rvr', 'temp_rvr.png')

os.makedirs(os.path.dirname(SCREENSHOT_PATH), exist_ok=True)

def get_driver():
    """Configures and returns a headless Chrome driver."""
    options = Options()

    chrome_bin = os.environ.get("CHROME_BIN", "/usr/bin/chromium")
    if os.path.exists(chrome_bin):
        options.binary_location = chrome_bin
    
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-images") 

    driver_path = os.environ.get("CHROMEDRIVER_PATH")
    if driver_path and os.path.exists(driver_path):
        service = Service(driver_path)
    else:
        
        try:
            service = Service(ChromeDriverManager().install())
        except Exception as e:
            logger.warning(f"WebDriverManager failed, trying default 'chromedriver': {e}")
            service = Service("chromedriver")

    return webdriver.Chrome(service=service, options=options)

def capture_rvr_snapshot():
    """
    Captures a screenshot of the RVR table and saves it atomically.
    Designed to be run by a background scheduler.
    """
    driver = None
    try:
        start_time = time.time()
        logger.info("Starting RVR Screenshot Task...")
        
        driver = get_driver()

        driver.set_page_load_timeout(30)
        driver.get(RVR_URL)

        wait = WebDriverWait(driver, 15)

        try:
            search_box = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='search']")))
            search_box.clear()
            search_box.send_keys("Mumbai")

            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.table tbody tr")))
            time.sleep(1) 
            
        except Exception as e:
            logger.warning(f"Search interaction failed, capturing default view: {e}")

        try:

            target = driver.find_element(By.TAG_NAME, "body")
        except Exception as e:
            logger.error(f"Could not find body element: {e}")
            return

        target.screenshot(TEMP_SCREENSHOT_PATH)

        if os.path.exists(TEMP_SCREENSHOT_PATH) and os.path.getsize(TEMP_SCREENSHOT_PATH) > 0:
            
            os.replace(TEMP_SCREENSHOT_PATH, SCREENSHOT_PATH)
            logger.info(f"RVR Screenshot saved successfully: {SCREENSHOT_PATH}")
        else:
            logger.error("Screenshot file was empty or not created.")

        elapsed = time.time() - start_time
        logger.info(f"RVR Screenshot Task completed in {elapsed:.2f}s")
        
    except Exception as e:
        logger.error(f"RVR Screenshot Task Failed: {e}")

    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass
