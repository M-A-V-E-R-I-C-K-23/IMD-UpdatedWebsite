import re
import io
import os
import logging
from datetime import datetime, timedelta
from pypdf import PdfReader
import fitz  
import pytesseract
from PIL import Image

logger = logging.getLogger(__name__)

TESSERACT_PATHS = [
    r'C:\Program Files\Tesseract-OCR\tesseract.exe',
    r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
    os.path.expanduser(r'~\AppData\Local\Tesseract-OCR\tesseract.exe')
]

def _get_tesseract_cmd():
    """Finds Tesseract executable or returns None."""
    
    import shutil
    if shutil.which("tesseract"):
        return "tesseract"
        
    for path in TESSERACT_PATHS:
        if os.path.exists(path):
            return path
    return None

def parse_notam_pdf(filepath):
    """
    Parses a NOTAM PDF file. 
    1. Tries standard text extraction.
    2. If text is empty/insufficient, tries OCR.
    """
    try:
        
        logger.info(f"Parsing PDF: {filepath}")
        text = ""
        try:
            
            with open(filepath, 'rb') as f:
                reader = PdfReader(f)
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
        except Exception as e:
            logger.warning(f"Standard extraction failed: {e}")

        text = text.replace('\n', ' ').strip()
        logger.info(f"Initial text extraction length: {len(text)}")

        if not text or len(text) < 20:
            logger.info("Text insufficient. Checking Tesseract availability...")
            tess_cmd = _get_tesseract_cmd()
            
            if not tess_cmd:
                logger.error("Tesseract-OCR not found on system.")
                return {
                    "success": False, 
                    "error": "PDF Parsing Failed: This looks like a scanned PDF, but Tesseract-OCR is NOT installed or found on the server. Please install Tesseract-OCR to enable scanning."
                }

            pytesseract.pytesseract.tesseract_cmd = tess_cmd
            logger.info(f"Using Tesseract at: {tess_cmd}. Starting OCR...")
            
            try:
                text = _perform_ocr(filepath)
                logger.info("OCR Processing Complete.")
            except Exception as e:
                logger.error(f"OCR Runtime Error: {e}")
                return {
                    "success": False, 
                    "error": f"OCR Failed: {str(e)}"
                }

        text = text.replace('\n', ' ').strip()
        
        if not text or len(text) < 10:
             return {
                "success": False, 
                "error": "PDF Parsing Failed: Text is still empty after OCR processing."
            }

        if "UNSERVICEABLE" in text.upper() or "U/S" in text.upper() or "OUT OF SERVICE" in text.upper():
            status = "UNSERVICEABLE"
        else:
            status = "STATUS UNKNOWN" 

        if "DRISHTI" in text.upper() or "RVR" in text.upper():
            equipment = "DRISHTI (RVR)"
        elif "ILS" in text.upper():
            equipment = "ILS"
        else:
            equipment = "EQUIPMENT" 

        rwys = []

        metpark_matches = re.findall(r'Metpark[\s-]*(\d{2})', text, re.IGNORECASE)
        for m in metpark_matches:
            rwys.append(m)

        std_matches = re.findall(r'(?:RWY|RUNWAY)[\s-]*(\d{2}[LR]?)', text, re.IGNORECASE)
        for m in std_matches:
            rwys.append(m)

        rwy_str = ""
        if rwys:
            unique_rwys = sorted(list(set(rwys)))
            rwy_str = " ".join([f"RWY {r}" for r in unique_rwys])
        
        if not rwy_str: rwy_str = ""

        validity_end = None
        validity_str = ""

        date_pattern = re.search(r'(\d{4})(?:Z|UTC)?\s+(\d{1,2})\s*([A-Za-z]{3})\s*(\d{4})', text)

        numeric_date_pattern = re.search(r'till\s+(\d{4})\s*UTC\s+of\s+(\d{2})/(\d{2})/(\d{4})', text, re.IGNORECASE)

        if date_pattern:
            time_raw = date_pattern.group(1) 
            day_raw = date_pattern.group(2) 
            month_raw = date_pattern.group(3) 
            year_raw = date_pattern.group(4) 
            
            validity_str = f"{time_raw}Z {day_raw}{month_raw.upper()}{year_raw}"
            
            try:
                dt_str = f"{day_raw} {month_raw} {year_raw} {time_raw}"
                validity_end = datetime.strptime(dt_str, "%d %b %Y %H%M")
            except:
                pass
        
        elif numeric_date_pattern:
             time_raw = numeric_date_pattern.group(1)
             day_raw = numeric_date_pattern.group(2)
             month_num = int(numeric_date_pattern.group(3))
             year_raw = numeric_date_pattern.group(4)

             month_abbr = datetime(2000, month_num, 1).strftime('%b').upper()
             
             validity_str = f"{time_raw}Z {day_raw}{month_abbr}{year_raw}"
             try:
                 dt_str = f"{day_raw} {month_num} {year_raw} {time_raw}"
                 validity_end = datetime.strptime(dt_str, "%d %m %Y %H%M")
             except:
                 pass
        
        if not validity_end:
             
             validity_end = datetime.utcnow() + timedelta(hours=24)
             validity_str = validity_end.strftime("%H%MZ %d%b%Y").upper()

        if status == "UNSERVICEABLE" and "DRISHTI" in equipment and not rwy_str:
             
             final_text = f"NOTAM {status} {equipment} {rwy_str} TILL {validity_str}".strip()
        else:
             
             final_text = f"NOTAM {status} {equipment} {rwy_str} TILL {validity_str}".strip()

        final_text = re.sub(r'\s+', ' ', final_text)

        return {
            "success": True,
            "formatted_text": final_text,
            "valid_until": validity_end,
            "raw_data": {
                "equipment": equipment,
                "status": status,
                "runways": list(set(rwys)) if rwys else [],
                "validity_str": validity_str
            }
        }

    except Exception as e:
        logger.error(f"PDF Parsing Error: {e}")
        return {"success": False, "error": str(e)}

def _perform_ocr(filepath):
    """
    Renders PDF pages to images and runs Tesseract OCR.
    Preprocesses images with OpenCV (Grayscale + Otsu) for better accuracy on scans.
    """
    import cv2
    import numpy as np

    text = ""
    doc = None
    try:
        doc = fitz.open(filepath)
        
        for page_num in range(min(len(doc), 2)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap(dpi=300) 
            img_bytes = pix.tobytes("png")

            nparr = np.frombuffer(img_bytes, np.uint8)
            img_cv = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if img_cv is not None:
                gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

                blur = cv2.GaussianBlur(gray, (5,5), 0)
                _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

                pil_img = Image.fromarray(thresh)
            else:
                 
                 pil_img = Image.open(io.BytesIO(img_bytes))

            custom_config = r'--oem 3 --psm 6' 
            text += pytesseract.image_to_string(pil_img, config=custom_config, timeout=10) + "\n"
    except Exception as e:
        logger.error(f"Error in OCR loop: {e}")
        raise e
    finally:
        if doc:
            doc.close()
        
    return text
