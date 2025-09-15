"""OCR utilities with optional GPU acceleration."""
from __future__ import annotations

import cv2

try:
    import easyocr  # type: ignore
except Exception:  # easyocr is optional; fallback to pytesseract
    easyocr = None

import pytesseract

_reader = None


def setup_ocr(use_gpu: bool, languages: list[str], gpu_index: int = 0) -> None:
    """Initialize the OCR reader.

    Parameters
    ----------
    use_gpu:
        Whether to enable GPU acceleration if supported.
    languages:
        List of language codes for recognition.
    gpu_index:
        Index of the GPU device to use.
    """

    global _reader
    if easyocr is not None:
        try:
            _reader = easyocr.Reader(languages, gpu=use_gpu, gpu_device_id=gpu_index)
        except Exception:
            _reader = None
    else:
        _reader = None


def extract_text(frame) -> str:
    """Run OCR on a frame using EasyOCR if available, otherwise Tesseract."""
    if _reader is not None:
        try:
            results = _reader.readtext(frame)
            return " ".join([res[1] for res in results]).strip()
        except Exception:
            pass
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    text = pytesseract.image_to_string(gray)
    return text.strip()
