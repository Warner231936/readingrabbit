"""LLM orchestrator for text verification."""
from __future__ import annotations

from transformers import pipeline


_verifier = None


def verify_text(text: str, model_name: str) -> str:
    """Use a text-to-text model to clean or validate OCR output.

    Parameters
    ----------
    text:
        The raw OCR-extracted string.
    model_name:
        Identifier of the transformer model to load.

    Returns
    -------
    str
        The model-corrected text. If the model fails to load, the
        original ``text`` is returned unchanged.
    """

    if not text or not model_name:
        return text

    global _verifier
    if _verifier is None:
        try:
            _verifier = pipeline("text2text-generation", model=model_name)
        except Exception:
            return text

    try:
        result = _verifier(text, max_new_tokens=len(text))
        return result[0]["generated_text"].strip()
    except Exception:
        return text

