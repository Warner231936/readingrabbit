"""OCR utilities."""
import pytesseract
import cv2


def extract_text(frame) -> str:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    text = pytesseract.image_to_string(gray)
    return text.strip()
