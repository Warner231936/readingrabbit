"""LLM orchestrator for text verification."""
from __future__ import annotations

from transformers import pipeline


_verifier = None


def verify_text(
    text: str,
    model_name: str,
    use_gpu: bool,
    prompt_template: str,
    gpu_index: int = 0,
) -> str:
    """Use a text-to-text model to clean or validate OCR output.

    Parameters
    ----------
    text:
        The raw OCR-extracted string.
    model_name:
        Identifier of the transformer model to load.
    use_gpu:
        Whether to run the model on GPU when available.
    prompt_template:
        Template string that formats the prompt with ``text``.
    gpu_index:
        Index of the GPU device to use.

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
            device = gpu_index if use_gpu else -1
            _verifier = pipeline("text2text-generation", model=model_name, device=device)
        except Exception:
            return text

    try:
        prompt = prompt_template.format(text=text)
        result = _verifier(prompt, max_new_tokens=min(len(text), 64))
        return result[0]["generated_text"].strip()
    except Exception:
        return text

