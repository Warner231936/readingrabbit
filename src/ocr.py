"""OCR utilities with optional GPU acceleration."""
from __future__ import annotations

from typing import Optional, Sequence

import cv2

try:
    import easyocr  # type: ignore
except Exception:  # easyocr is optional; fallback to pytesseract
    easyocr = None

try:
    import pytesseract
except Exception:  # pytesseract is optional but recommended
    pytesseract = None  # type: ignore

_reader = None
_reader_config: Optional[tuple[bool, tuple[str, ...], int]] = None
_tesseract_langs = "eng"


def setup_ocr(use_gpu: bool, languages: Sequence[str], gpu_index: int = 0) -> None:
    """Initialize the OCR reader."""

    global _reader, _reader_config, _tesseract_langs
    langs = tuple(sorted(str(lang) for lang in languages if lang)) or ("en",)
    _tesseract_langs = "+".join(langs)

    desired_config = (use_gpu, langs, gpu_index)
    if _reader_config == desired_config and _reader is not None:
        return

    _reader_config = desired_config
    if easyocr is not None:
        try:
            _reader = easyocr.Reader(list(langs), gpu=use_gpu, gpu_device_id=gpu_index)
            return
        except Exception:
            _reader = None

    _reader = None


def _prepare_for_tesseract(frame) -> cv2.Mat:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    denoised = cv2.bilateralFilter(gray, 9, 75, 75)
    _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh


def extract_text(frame) -> str:
    """Run OCR on a frame using EasyOCR if available, otherwise Tesseract."""

    if _reader is not None:
        try:
            results = _reader.readtext(frame)
            return " ".join(res[1] for res in results).strip()
        except Exception:
            pass

    if pytesseract is None:
        return ""

    processed = _prepare_for_tesseract(frame)
    text = pytesseract.image_to_string(processed, lang=_tesseract_langs)
    return text.strip()
