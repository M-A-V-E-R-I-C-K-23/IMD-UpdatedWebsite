import cv2
import numpy as np
import pytesseract
from PIL import Image
import io
import re

def preprocess_image(filepath):
    img = cv2.imread(filepath)
    if img is None:
        raise ValueError("Could not load image")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)

    _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    return Image.fromarray(thresh)

def extract_text_from_image(filepath):
    try:
        pil_img = preprocess_image(filepath)
        
        custom_config = r'--oem 3 --psm 3'
        text = pytesseract.image_to_string(pil_img, config=custom_config)
        return text.strip()
    except Exception as e:
        print(f"OCR Error: {e}")
        return ""

def generate_summary(text):
    if not text:
        return "No text detected."

    clean_text = re.sub(r'\s+', ' ', text).strip()
    
    summary_parts = []
    
    subject_match = re.search(r'(?:Sub|Subject|Regarding|Ref)[:\s\-\.]+(.*?)[\.\n]', text, re.IGNORECASE)
    if subject_match:
        summary_parts.append(f"Subject: {subject_match.group(1).strip()[:100]}")
    
    date_match = re.search(r'(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})', text)       
    if date_match and "Date" not in clean_text[:20]: 
         pass 
         
    sentences = re.split(r'(?<=[.!?]) +', clean_text)
    
    if not summary_parts:
        candidate = " ".join(sentences[:2])
        if len(candidate) > 250:
            candidate = candidate[:247] + "..."
        summary_parts.append(candidate)
    
    if len(summary_parts) == 1 and len(summary_parts[0]) < 50 and len(sentences) > 1:
         summary_parts.append(sentences[1][:100])

    return " ".join(summary_parts)
