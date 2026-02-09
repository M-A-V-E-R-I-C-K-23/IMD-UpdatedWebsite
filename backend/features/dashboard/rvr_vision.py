from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pytesseract
from PIL import Image
import io
import time
from core.extensions import logger

from selenium.webdriver.chrome.service import Service

def fetch_rvr_fallback():
    """
    Fallback RVR fetcher using Selenium + Screenshot + OCR.
    Timeout enforced by service layer or driver timeout.
    """
    options = Options()
    options.binary_location = "/usr/bin/chromium"
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    driver = None
    try:
        logger.info("Starting Selenium RVR fallback...")
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)

        driver.set_page_load_timeout(10)
        driver.get("http://rvrcamd.imd.gov.in:5000/live-rvr")

        wait = WebDriverWait(driver, 5)

        try:
            search_box = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='search']")))
            search_box.send_keys("Mumbai")
            
            time.sleep(1) 
        except Exception as e:
            logger.warning(f"Selenium interaction failed, trying raw page: {e}")

        try:
            table = wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
            png_data = table.screenshot_as_png
        except:
             
            png_data = driver.get_screenshot_as_png()

        image = Image.open(io.BytesIO(png_data))
        
        image = image.convert('L')
        
        image = image.point(lambda x: 0 if x < 128 else 255, '1')

        text = pytesseract.image_to_string(image)
        logger.debug(f"OCR Output: {text}")

        data = parse_ocr_text(text)
        
        if not data:
            return None
            
        return data

    except Exception as e:
        logger.error(f"RVR Vision Fallback Failed: {e}")
        return None
    finally:
        if driver:
            driver.quit()

def parse_ocr_text(text):
    """
    Parses raw OCR text into structured RVR data.
    Looking for lines like: "27 1200 1000 1000 N"
    """
    data = []
    lines = text.split('\n')
    for line in lines:
        parts = line.split()

        if len(parts) >= 4:
            
            rwy = parts[0]

            try:
                
                clean_parts = [p.strip() for p in parts if p.strip()]
                
                if len(clean_parts) < 4: continue

                item = {
                   "rwy": clean_parts[0],
                   "tdz": clean_parts[1],
                   "mid": clean_parts[2],
                   "end": clean_parts[3],
                   "trend": clean_parts[4] if len(clean_parts) > 4 else "N"
                }

                valid_count = 0
                for k in ['tdz', 'mid', 'end']:
                    if item[k].replace('m','').isdigit() or '---' in item[k]:
                        valid_count += 1
                
                if valid_count >= 2: 
                     data.append(item)
            except:
                continue
                
    return data
