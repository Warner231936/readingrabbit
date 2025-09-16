"""OCR utilities with optional GPU acceleration."""
from __future__ import annotations

import logging
from typing import Mapping, Optional, Sequence

import cv2
import numpy as np

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
_preprocess_settings: Mapping[str, object] = {}
_logger = logging.getLogger("readingrabbit")


def setup_ocr(
    use_gpu: bool,
    languages: Sequence[str],
    gpu_index: int = 0,
    preprocessing: Optional[Mapping[str, object]] = None,
) -> None:
    """Initialize the OCR reader."""

    global _reader, _reader_config, _tesseract_langs, _preprocess_settings
    langs = tuple(sorted(str(lang) for lang in languages if lang)) or ("en",)
    _tesseract_langs = "+".join(langs)
    _preprocess_settings = preprocessing or {}

    desired_config = (use_gpu, langs, gpu_index)
    if _reader_config == desired_config and _reader is not None:
        return

    _reader_config = desired_config
    if easyocr is not None:
        try:
            _reader = easyocr.Reader(list(langs), gpu=use_gpu, gpu_device_id=gpu_index)
            _logger.info("EasyOCR initialised for languages: %s", ",".join(langs))
            return
        except Exception:
            _logger.warning("EasyOCR unavailable, falling back to Tesseract", exc_info=True)
            _reader = None

    _reader = None


def _apply_common_preprocessing(frame) -> cv2.Mat:
    settings = _preprocess_settings or {}
    work = frame
    scale = float(settings.get("resize_scale", 1.0)) if settings else 1.0
    if scale > 0 and abs(scale - 1.0) > 1e-3:
        work = cv2.resize(work, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    if work.ndim == 3:
        gray = cv2.cvtColor(work, cv2.COLOR_BGR2GRAY)
    else:
        gray = work.copy()

    bilateral_d = int(settings.get("bilateral_diameter", 0)) if settings else 0
    if bilateral_d > 0:
        sigma_color = int(settings.get("bilateral_sigma_color", 75))
        sigma_space = int(settings.get("bilateral_sigma_space", 75))
        gray = cv2.bilateralFilter(gray, bilateral_d, sigma_color, sigma_space)

    clip_limit = float(settings.get("clahe_clip_limit", 0.0)) if settings else 0.0
    if clip_limit > 0:
        tile = max(1, int(settings.get("clahe_tile_grid_size", 8)))
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile, tile))
        gray = clahe.apply(gray)

    if bool(settings.get("use_adaptive_threshold")):
        block_size = int(settings.get("adaptive_threshold_block_size", 15))
        if block_size % 2 == 0:
            block_size += 1
        block_size = max(3, block_size)
        c_val = float(settings.get("adaptive_threshold_c", 2.0))
        gray = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            block_size,
            c_val,
        )
    elif settings.get("use_otsu_threshold", True):
        _, gray = cv2.threshold(
            gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )

    sharpen_amount = float(settings.get("sharpen_amount", 0.0)) if settings else 0.0
    if sharpen_amount > 0:
        kernel = np.array(
            [
                [0.0, -sharpen_amount, 0.0],
                [-sharpen_amount, 1 + (4 * sharpen_amount), -sharpen_amount],
                [0.0, -sharpen_amount, 0.0],
            ],
            dtype="float32",
        )
        gray = cv2.filter2D(gray, -1, kernel)

    return gray


def _prepare_for_easyocr(frame) -> cv2.Mat:
    settings = _preprocess_settings or {}
    if not settings.get("apply_to_easyocr"):
        return frame
    gray = _apply_common_preprocessing(frame)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


def _prepare_for_tesseract(frame) -> cv2.Mat:
    return _apply_common_preprocessing(frame)


def extract_text(frame) -> str:
    """Run OCR on a frame using EasyOCR if available, otherwise Tesseract."""

    easyocr_frame = _prepare_for_easyocr(frame)
    if _reader is not None:
        try:
            results = _reader.readtext(easyocr_frame)
            return " ".join(res[1] for res in results).strip()
        except Exception:
            _logger.error("EasyOCR failed during extraction", exc_info=True)
            pass

    if pytesseract is None:
        return ""

    processed = _prepare_for_tesseract(frame)
    text = pytesseract.image_to_string(processed, lang=_tesseract_langs)
    return text.strip()
