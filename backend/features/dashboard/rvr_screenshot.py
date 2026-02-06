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

# Helper to configure Tesseract command if on Windows local dev
# import os
# if os.name == 'nt':
#     pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

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
        
        # 1. Load Page (Extended timeout for Docker)
        driver.set_page_load_timeout(30) # Increased from 8 to 30
        try:
            driver.get("http://rvrcamd.imd.gov.in:5000/live-rvr")
        except:
            logger.warning("Page load timeout (continuing to check DOM)...")
        
        # 2. Wait for Key Elements (Deterministic)
        wait = WebDriverWait(driver, 15)
        
        try:
            # Wait for search box validity
            search_box = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='search']")))
            search_box.clear()
            search_box.send_keys("Mumbai")
            # Wait for valid data row to appear after filter
            wait.until(EC.presence_of_element_located((By.XPATH, "//td[contains(text(), '27') or contains(text(), '14') or contains(text(), '09') or contains(text(), '32')]")))
            time.sleep(2) # Stabilize render
        except Exception as e:
            logger.warning(f"Search/Filter interaction failed: {e}")

        # 3. Screenshot
        png_data = None
        try:
            # Target the specific data table
            table = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.table, table.dataTable")))
            png_data = table.screenshot_as_png
        except Exception as e:
            logger.warning(f"Specific table selection failed: {e}. Capturing full body.")
            body = driver.find_element(By.TAG_NAME, "body")
            png_data = body.screenshot_as_png

        # 4. Preprocess
        image = Image.open(io.BytesIO(png_data))
        # Save debug image
        try:
            image.save("/app/uploads/debug_ocr_crop.png")
        except:
            pass
            
        image = image.convert('L')
        # Binarize for sharper text
        image = image.point(lambda x: 0 if x < 140 else 255, '1')

        # 5. OCR
        # PSM 6 = Assume a single uniform block of text
        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(image, config=custom_config)
        logger.info(f"OCR Content Snippet: {text[:100]}...")

        # 6. Parse with Aviation Logic
        data = _parse_ocr_output(text)
        
        elapsed = time.time() - start_time
        logger.info(f"Pipeline finished in {elapsed:.2f}s. Extracted {len(data)} rows.")
        
        if not data:
            # If we have no data, but the OCR didn't crash, it means we couldn't parse any valid rows.
            # This is an OCR_FAIL state unless we decide it's just empty.
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
    
    # Runway patterns: 27, 09, 14, 32, 27L, etc.
    rwy_pattern = re.compile(r'\b(?:\d{2}[A-Z]?)\b')
    
    for line in lines:
        line = line.strip()
        if not line: continue
        
        # Filter headers
        if "RWY" in line.upper() and "TDZ" in line.upper(): continue
        
        parts = line.split()
        if len(parts) < 2: continue # Need at least RWY and one value
        
        # Identify Runway (usually first token)
        # Sometimes OCR merges it: "27 2000" -> ["27", "2000"]
        # Or "RWY27" -> ["RWY27"]
        
        rwy_candidate = parts[0].upper().replace("RWY", "")
        if not re.match(r'^\d{2}[A-Z]?$', rwy_candidate):
            continue
            
        rwy_id = f"RWY{rwy_candidate}"
        
        # Remove the runway token and process the rest as sensor readings
        readings = parts[1:]
        
        # Expected order: TDZ, MID, END, TREND (optional)
        # We need to map these safely.
        # "2000 1000 500 N" -> TDZ=2000, MID=1000, END=500
        # "P2000 --- --- U" -> TDZ=P2000, MID=---, END=---
        
        # Helper to parse a single sensor token
        def parse_sensor(token, default_name):
            # Clean unit 'm' or 'M'
            raw = token.upper().replace('M', '').strip()
            
            # STATE: NO_DATA
            if '---' in raw or '///' in raw or raw == '':
                return {
                    "runway": rwy_id, # Actually sensor name should probably be generic or key-based? 
                                      # The prompt asks for { "runway": "RWY27", "value": ... }
                                      # Use default_name to distinguish (USER DATA MODEL REQUIREMENT doesn't specify unique keys per sensor, 
                                      # but usually `runway` field implies the strip. 
                                      # Wait, the prompt example shows "runway": "RWYMID1" for the MID sensor.
                    "value": None,
                    "modifier": None,
                    "unit": "m",
                    "status": "NO_DATA"
                }
            
            # STATE: OK (Numeric or P/M prefix)
            modifier = None
            value = None
            
            # Check prefix
            if raw.startswith('P') or raw.startswith('M'):
                modifier = raw[0]
                val_str = raw[1:]
            else:
                val_str = raw
                
            # Parse number
            if val_str.isdigit():
                value = int(val_str)
                return {
                    "runway": default_name if default_name else rwy_id, # Use specific logical name if needed
                    "value": value,
                    "modifier": modifier,
                    "unit": "m",
                    "status": "OK"
                }
            
            # Fallback (maybe garbage check)
            return None 

        # We construct a composite object or a list of sensors?
        # The prompt implies: "Each runway sensor must return structured output like..." from "parsing rules".
        # It seems the user wants a LIST of objects, one for each "Reading".
        # BUT typical RVR dashboards return one object per runway with tdz, mid, end.
        # However, the prompt explicitly says:
        # { "runway": "RWYMID1", ... } for --- m.
        # This implies "RWY27" (implicit TDZ?), "RWYMID1" (MID?), "RWYEND1" (END?).
        # Let's infer the naming convention users implies:
        # TDZ -> RWY{XX}
        # MID -> RWYMID{XX}? Or just separate objects.
        # Let's return a list format, but sticking to valid semantics.
        # Let's map indexes 0, 1, 2 to TDZ, MID, END.
        
        row_sensors = []
        
        # 0: TDZ
        if len(readings) > 0:
            parsed = parse_sensor(readings[0], rwy_id) # Main runway ID usually means TDZ
            if parsed: row_sensors.append(parsed)
            
        # 1: MID
        if len(readings) > 1:
            # Check if it's actually a trend (N/U/D are short)
            if readings[1] in ['N', 'U', 'D', 'n', 'u', 'd']:
                pass # It's a trend, no MID/END
            else:
                parsed = parse_sensor(readings[1], f"RWYMID{rwy_candidate}") # Construct unique ID for MID
                if parsed: row_sensors.append(parsed)

        # 2: END
        if len(readings) > 2:
            if readings[2] in ['N', 'U', 'D', 'n', 'u', 'd']:
                pass
            else:
                parsed = parse_sensor(readings[2], f"RWYEND{rwy_candidate}")
                if parsed: row_sensors.append(parsed)
                
        # If we got at least one valid sensor from this row, add to global data
        if row_sensors:
            data.extend(row_sensors)

    return data
