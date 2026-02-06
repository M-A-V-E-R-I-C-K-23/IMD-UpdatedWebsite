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

# Configure Tesseract path if needed (e.g., for Windows dev)
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

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
        
        # 1. Load Page with tight timeout
        driver.set_page_load_timeout(10)
        driver.get("http://rvrcamd.imd.gov.in:5000/live-rvr")
        
        # 2. Wait for table
        wait = WebDriverWait(driver, 5)
        # Assuming there's a search box or we need to find "MUMBAI"
        # The prompt says "Parses RWY / TDZ...". 
        # We need to simulate the interaction or crop the visible table.
        # Based on previous Playwright logic, we searched "Mumbai".
        
        # Interaction
        try:
            search_box = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='search']")))
            search_box.send_keys("Mumbai")
            # Wait for update
            time.sleep(1) 
        except Exception as e:
            logger.warning(f"Selenium interaction failed, trying raw page: {e}")

        # 3. Screenshot
        # Find the table to crop, or take full page and hope
        # Let's target the table for better OCR results
        try:
            table = wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
            png_data = table.screenshot_as_png
        except:
             # Fallback to full screenshot if specific table not found
            png_data = driver.get_screenshot_as_png()

        # 4. Process Image
        image = Image.open(io.BytesIO(png_data))
        # Grayscale
        image = image.convert('L')
        # Thresholding (simple binary)
        image = image.point(lambda x: 0 if x < 128 else 255, '1')
        
        # 5. OCR
        text = pytesseract.image_to_string(image)
        logger.debug(f"OCR Output: {text}")
        
        # 6. Parse
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
        # Heuristic: Valid row has at least 4 numbers or parts
        # e.g. RWY(27) TDZ(1000) MID(1000) END(1000) TREND(N)
        if len(parts) >= 4:
            # Check if first part looks like a runway (digits, maybe with letter like 09L)
            rwy = parts[0]
            
            # Simple validation: RWY must be 2 digits approx
            # And subsequent tokens must be numeric or '---'
            
            # Filter parts to remove garbage?
            # Let's try to map indices
            try:
                # Basic cleanup
                clean_parts = [p.strip() for p in parts if p.strip()]
                
                if len(clean_parts) < 4: continue
                
                # Check for "MUMBAI" row header if present? 
                # OCR often loses layout. 
                # Let's assume the cropped table has rows of data.
                
                # Extract numbers
                # Exclude non-numeric/special chars unless they are part of value
                
                item = {
                   "rwy": clean_parts[0],
                   "tdz": clean_parts[1],
                   "mid": clean_parts[2],
                   "end": clean_parts[3],
                   "trend": clean_parts[4] if len(clean_parts) > 4 else "N"
                }
                
                # Validate numeric-ish structure for TDZ/MID/END 
                # (They can be '---' or '2000' or '2000m')
                valid_count = 0
                for k in ['tdz', 'mid', 'end']:
                    if item[k].replace('m','').isdigit() or '---' in item[k]:
                        valid_count += 1
                
                if valid_count >= 2: # At least 2 valid readings
                     data.append(item)
            except:
                continue
                
    return data
