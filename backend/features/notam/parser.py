import re
import io
import os
import logging
from datetime import datetime, timedelta
from pypdf import PdfReader
import fitz  # PyMuPDF
import pytesseract
from PIL import Image

logger = logging.getLogger(__name__)

# Standard Tesseract Paths on Windows
TESSERACT_PATHS = [
    r'C:\Program Files\Tesseract-OCR\tesseract.exe',
    r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
    os.path.expanduser(r'~\AppData\Local\Tesseract-OCR\tesseract.exe')
]

def _get_tesseract_cmd():
    """Finds Tesseract executable or returns None."""
    # Check PATH first (let pytesseract handle it if in path? No, explicit is safer)
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
        # 1. Try Standard Text Extraction
        logger.info(f"Parsing PDF: {filepath}")
        text = ""
        try:
            # Open file specifically to ensure closure
            with open(filepath, 'rb') as f:
                reader = PdfReader(f)
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
        except Exception as e:
            logger.warning(f"Standard extraction failed: {e}")
            
    # Post-process text: Flatten to single line
    # ... (rest of logic) ...

        
    # Post-process text: Flatten to single line
        text = text.replace('\n', ' ').strip()
        logger.info(f"Initial text extraction length: {len(text)}")
        
        # 2. Check if OCR is needed
        if not text or len(text) < 20:
            logger.info("Text insufficient. Checking Tesseract availability...")
            tess_cmd = _get_tesseract_cmd()
            
            if not tess_cmd:
                logger.error("Tesseract-OCR not found on system.")
                return {
                    "success": False, 
                    "error": "PDF Parsing Failed: This looks like a scanned PDF, but Tesseract-OCR is NOT installed or found on the server. Please install Tesseract-OCR to enable scanning."
                }
            
            # Configure pytesseract
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

        # 3. Clean Text again after OCR
        text = text.replace('\n', ' ').strip()
        
        if not text or len(text) < 10:
             return {
                "success": False, 
                "error": "PDF Parsing Failed: Text is still empty after OCR processing."
            }
        
        # --- PARSING LOGIC (Regex) ---
        
        # 1. Status
        if "UNSERVICEABLE" in text.upper() or "U/S" in text.upper() or "OUT OF SERVICE" in text.upper():
            status = "UNSERVICEABLE"
        else:
            status = "STATUS UNKNOWN" 

        # 2. Equipment
        if "DRISHTI" in text.upper() or "RVR" in text.upper():
            equipment = "DRISHTI (RVR)"
        elif "ILS" in text.upper():
            equipment = "ILS"
        else:
            equipment = "EQUIPMENT" 

        # 3. Runways (Handle "Metpark 09" -> "RWY 09" and "Metpark-27" -> "RWY 27")
        # Look for patterns like "Metpark[- ]*(\d{2})" OR "RWY[- ]*(\d{2})"
        rwys = []
        
        # Specific case for Metpark/Drishti
        metpark_matches = re.findall(r'Metpark[\s-]*(\d{2})', text, re.IGNORECASE)
        for m in metpark_matches:
            rwys.append(m)
            
        # Standard Runway matches
        std_matches = re.findall(r'(?:RWY|RUNWAY)[\s-]*(\d{2}[LR]?)', text, re.IGNORECASE)
        for m in std_matches:
            rwys.append(m)
        
        # Formatting Runways as RWY XX
        rwy_str = ""
        if rwys:
            unique_rwys = sorted(list(set(rwys)))
            rwy_str = " ".join([f"RWY {r}" for r in unique_rwys])
        
        if not rwy_str: rwy_str = ""
        
        # 4. Validity
        validity_end = None
        validity_str = ""
        
        # Regex for HHMMZ DDMMMYYYY
        date_pattern = re.search(r'(\d{4})(?:Z|UTC)?\s+(\d{1,2})\s*([A-Za-z]{3})\s*(\d{4})', text)
        
        # New pattern: "till 0900 UTC of 19/02/2026"
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
             
             # Convert numeric month to abbreviated month (FEB)
             month_abbr = datetime(2000, month_num, 1).strftime('%b').upper()
             
             validity_str = f"{time_raw}Z {day_raw}{month_abbr}{year_raw}"
             try:
                 dt_str = f"{day_raw} {month_num} {year_raw} {time_raw}"
                 validity_end = datetime.strptime(dt_str, "%d %m %Y %H%M")
             except:
                 pass
        
        if not validity_end:
             # Fallback
             validity_end = datetime.utcnow() + timedelta(hours=24)
             validity_str = validity_end.strftime("%H%MZ %d%b%Y").upper()

        if status == "UNSERVICEABLE" and "DRISHTI" in equipment and not rwy_str:
             # If exact match for the sample case
             final_text = f"NOTAM {status} {equipment} {rwy_str} TILL {validity_str}".strip()
        else:
             # General construction ensuring format: NOTAM STATUS SYSTEM RWYS TILL TIME DATE
             final_text = f"NOTAM {status} {equipment} {rwy_str} TILL {validity_str}".strip()
         
        # Clean up double spaces
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
        # Limit to first 2 pages to prevent massive processing time on large docs
        for page_num in range(min(len(doc), 2)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap(dpi=300) # Higher DPI for better OCR
            img_bytes = pix.tobytes("png")
            
            # Convert to numpy array for OpenCV
            nparr = np.frombuffer(img_bytes, np.uint8)
            img_cv = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            # Preprocessing
            if img_cv is not None:
                gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
                
                # Otsu's thresholding
                # Apply slight blur to reduce noise before thresholding
                blur = cv2.GaussianBlur(gray, (5,5), 0)
                _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                
                # Convert back to PIL Image for Tesseract
                pil_img = Image.fromarray(thresh)
            else:
                 # Fallback if cv2 fails to decode
                 pil_img = Image.open(io.BytesIO(img_bytes))
            
            # Add timeout to fail fast if it hangs
            # custom config to assume single block of text might help
            custom_config = r'--oem 3 --psm 6' 
            text += pytesseract.image_to_string(pil_img, config=custom_config, timeout=10) + "\n"
    except Exception as e:
        logger.error(f"Error in OCR loop: {e}")
        raise e
    finally:
        if doc:
            doc.close()
        
    return text
