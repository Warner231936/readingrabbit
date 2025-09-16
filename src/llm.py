
"""LLM orchestrator for text verification."""
from __future__ import annotations

import logging
from threading import Lock

try:
    from transformers import pipeline
except Exception:  # transformers is optional at runtime
    pipeline = None  # type: ignore


_verifier = None
_lock = Lock()
_logger = logging.getLogger("readingrabbit")


def verify_text(
    text: str,
    model_name: str,
    use_gpu: bool,
    prompt_template: str,
    gpu_index: int = 0,
) -> str:
    """Use a text-to-text model to clean or validate OCR output."""

    if not text or not model_name or pipeline is None:
        return text

    global _verifier
    with _lock:
        if _verifier is None:
            try:
                device = gpu_index if use_gpu else -1
                _verifier = pipeline("text2text-generation", model=model_name, device=device)
            except Exception:
                _verifier = None
                _logger.warning("Unable to load LLM model '%s'", model_name)
                return text

    if _verifier is None:
        return text

    try:
        prompt = prompt_template.format(text=text)
        result = _verifier(prompt, max_new_tokens=min(len(text), 128))
        return result[0]["generated_text"].strip()
    except Exception:
        _logger.error("LLM verification failed", exc_info=True)
        return text

