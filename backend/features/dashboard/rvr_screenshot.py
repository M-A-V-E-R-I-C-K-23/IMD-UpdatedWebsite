from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pytesseract
from PIL import Image, ImageOps, ImageEnhance
import io
import re
from core.extensions import logger
import time

from selenium.webdriver.chrome.service import Service

def fetch_rvr_screenshot():
    """
    Strict Screenshot-Only RVR Fetcher.
    Selenium -> Screenshot -> OCR -> Parse.
    """
    options = Options()
    options.binary_location = "/usr/bin/chromium"
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-images")
    options.add_argument("--page-load-strategy=eager") 
    options.add_argument("--blink-settings=imagesEnabled=false")
    
    driver = None
    try:
        start_time = time.time()
        logger.info("Starting Screenshot-Only RVR Fetch...")
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)

        driver.set_page_load_timeout(30) 
        try:
            driver.get("http://rvrcamd.imd.gov.in:5000/live-rvr")
        except:
            logger.warning("Page load timeout (continuing to check DOM)...")

        wait = WebDriverWait(driver, 15)
        
        try:
            
            search_box = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='search']")))
            search_box.clear()
            search_box.send_keys("Mumbai")
            
            wait.until(EC.presence_of_element_located((By.XPATH, "//td[contains(text(), '27') or contains(text(), '14') or contains(text(), '09') or contains(text(), '32')]")))
            time.sleep(2) 
        except Exception as e:
            logger.warning(f"Search/Filter interaction failed: {e}")

        png_data = None
        try:
            
            table = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.table, table.dataTable")))
            png_data = table.screenshot_as_png
        except Exception as e:
            logger.warning(f"Specific table selection failed: {e}. Capturing full body.")
            body = driver.find_element(By.TAG_NAME, "body")
            png_data = body.screenshot_as_png

        image = Image.open(io.BytesIO(png_data))
        
        try:
            image.save("/app/uploads/debug_ocr_crop.png")
        except:
            pass
            
        image = image.convert('L')
        
        image = image.point(lambda x: 0 if x < 140 else 255, '1')

        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(image, config=custom_config)
        logger.info(f"OCR Content Snippet: {text[:100]}...")

        data = _parse_ocr_output(text)
        
        elapsed = time.time() - start_time
        logger.info(f"Pipeline finished in {elapsed:.2f}s. Extracted {len(data)} rows.")
        
        if not data:

            logger.error(f"OCR produced text but parsing found 0 valid rows. Raw text: {text[:200]}")
            return _error_response("Parsed 0 valid RVR rows from screenshot")

        return {
            "status": "ok",
            "data": data,
            "message": "Extracted via screenshot OCR",
            "source": "SCREENSHOT"
        }

    except Exception as e:
        msg = str(e)
        logger.error(f"Screenshot Pipeline Critical Failure: {e}")
        return _error_response(f"Pipeline Failed: {msg}")
        
    finally:
        if driver:
            try: driver.quit()
            except: pass

def _error_response(msg):
    return {
        "status": "error",
        "data": [],
        "message": msg,
        "source": "SCREENSHOT"
    }

def _parse_ocr_output(text):
    """
    Strict Aviation RVR Parser.
    Handles: "P2000", "---", "M0050", numeric values.
    Returns structured JSON per sensor.
    """
    data = []
    lines = text.split('\n')

    rwy_pattern = re.compile(r'\b(?:\d{2}[A-Z]?)\b')
    
    for line in lines:
        line = line.strip()
        if not line: continue

        if "RWY" in line.upper() and "TDZ" in line.upper(): continue
        
        parts = line.split()
        if len(parts) < 2: continue 

        rwy_candidate = parts[0].upper().replace("RWY", "")
        if not re.match(r'^\d{2}[A-Z]?$', rwy_candidate):
            continue
            
        rwy_id = f"RWY{rwy_candidate}"

        readings = parts[1:]

        def parse_sensor(token, default_name):
            
            raw = token.upper().replace('M', '').strip()

            if '---' in raw or '///' in raw or raw == '':
                return {
                    "runway": rwy_id, 

                    "value": None,
                    "modifier": None,
                    "unit": "m",
                    "status": "NO_DATA"
                }

            modifier = None
            value = None

            if raw.startswith('P') or raw.startswith('M'):
                modifier = raw[0]
                val_str = raw[1:]
            else:
                val_str = raw

            if val_str.isdigit():
                value = int(val_str)
                return {
                    "runway": default_name if default_name else rwy_id, 
                    "value": value,
                    "modifier": modifier,
                    "unit": "m",
                    "status": "OK"
                }

            return None 

        row_sensors = []

        if len(readings) > 0:
            parsed = parse_sensor(readings[0], rwy_id) 
            if parsed: row_sensors.append(parsed)

        if len(readings) > 1:
            
            if readings[1] in ['N', 'U', 'D', 'n', 'u', 'd']:
                pass 
            else:
                parsed = parse_sensor(readings[1], f"RWYMID{rwy_candidate}") 
                if parsed: row_sensors.append(parsed)

        if len(readings) > 2:
            if readings[2] in ['N', 'U', 'D', 'n', 'u', 'd']:
                pass
            else:
                parsed = parse_sensor(readings[2], f"RWYEND{rwy_candidate}")
                if parsed: row_sensors.append(parsed)

        if row_sensors:
            data.extend(row_sensors)

    return data
