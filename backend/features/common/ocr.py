import cv2
import numpy as np
import pytesseract
from PIL import Image
import io
import re

# Add Tesseract path if needed, assuming it's in PATH or handled by env.
# If previous parser.py worked, it should be fine.

def preprocess_image(filepath):
    """
    Standard preprocessing for document OCR.
    """
    img = cv2.imread(filepath)
    if img is None:
        raise ValueError("Could not load image")

    # Grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Denoise
    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)

    # Thresholding (Otsu)
    _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    return Image.fromarray(thresh)

def extract_text_from_image(filepath):
    """
    Runs OCR on the image file.
    """
    try:
        # Preprocess
        pil_img = preprocess_image(filepath)
        
        # OCR
        # --oem 3: Default engine
        # --psm 6: Assume uniform block of text (good for notices) or 3 (auto)
        custom_config = r'--oem 3 --psm 3'
        text = pytesseract.image_to_string(pil_img, config=custom_config)
        return text.strip()
    except Exception as e:
        print(f"OCR Error: {e}")
        return ""

def generate_summary(text):
    """
    Generates a 2-3 line summary from the text.
    Heuristic:
    1. Clean up excessive whitespace/newlines.
    2. Look for "Subject:", "Sub:", "Notice", "Date:" key lines.
    3. Take the first few significant sentences.
    """
    if not text:
        return "No text detected."

    # Normalize whitespace
    clean_text = re.sub(r'\s+', ' ', text).strip()
    
    # Simple Sentence Splitting (by . or newline logic preserved before normalization)
    # Let's try to identify key info
    
    summary_parts = []
    
    # Subject extraction
    subject_match = re.search(r'(?:Sub|Subject|Regarding|Ref)[:\s\-\.]+(.*?)[\.\n]', text, re.IGNORECASE)
    if subject_match:
        summary_parts.append(f"Subject: {subject_match.group(1).strip()[:100]}")
    
    # Date extraction
    date_match = re.search(r'(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})', text)       
    if date_match and "Date" not in clean_text[:20]: # Avoid redundant date if it's the header
         pass # Actually hard to contextually place date, but let's leave it for now.
         
    # Fallback: First 200 chars or 2 sentences
    sentences = re.split(r'(?<=[.!?]) +', clean_text)
    
    if not summary_parts:
        # Take first 2 sentences
        candidate = " ".join(sentences[:2])
        if len(candidate) > 250:
            candidate = candidate[:247] + "..."
        summary_parts.append(candidate)
    
    # Add a bit more context if subject alone is short
    if len(summary_parts) == 1 and len(summary_parts[0]) < 50 and len(sentences) > 1:
         summary_parts.append(sentences[1][:100])

    return " ".join(summary_parts)
