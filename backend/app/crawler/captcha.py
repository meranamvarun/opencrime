"""EasyOCR-based CAPTCHA solver for government portal CAPTCHAs.

Government portals typically use low-distortion alphanumeric CAPTCHAs —
EasyOCR at ~80% accuracy is sufficient for an MVP.  On failure the caller
should retry (most portals regenerate the CAPTCHA on the same session).
"""
from __future__ import annotations

import io
import logging
from typing import Optional

import numpy as np
from PIL import Image, ImageFilter, ImageOps

logger = logging.getLogger(__name__)

# Lazy-load the EasyOCR reader — it takes ~4 s on first call.
_reader = None


def _get_reader():
    global _reader
    if _reader is None:
        import easyocr  # imported lazily so the module loads fast at startup
        _reader = easyocr.Reader(["en"], gpu=False, verbose=False)
    return _reader


def solve(image_bytes: bytes, allowlist: str = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz") -> Optional[str]:
    """Return the solved CAPTCHA text, or None on failure."""
    try:
        img = _preprocess(image_bytes)
        arr = np.array(img)
        results = _get_reader().readtext(
            arr,
            detail=0,
            allowlist=allowlist,
            paragraph=False,
            width_ths=0.9,
        )
        text = "".join(results).strip().replace(" ", "")
        if not text:
            logger.debug("EasyOCR returned empty string for CAPTCHA")
            return None
        logger.debug("Solved CAPTCHA: %r", text)
        return text
    except Exception as exc:
        logger.warning("CAPTCHA solve failed: %s", exc)
        return None


def _preprocess(image_bytes: bytes) -> Image.Image:
    """Convert to clean grayscale BW suitable for OCR."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    # Scale up small CAPTCHAs — EasyOCR works best ≥ 32 px tall
    w, h = img.size
    if h < 60:
        scale = 60 / h
        img = img.resize((int(w * scale), 60), Image.LANCZOS)

    # Grayscale → denoise → threshold
    gray = ImageOps.grayscale(img)
    gray = gray.filter(ImageFilter.MedianFilter(size=3))

    # Otsu-style binarisation via numpy
    arr = np.array(gray)
    threshold = int(arr.mean())
    bw = Image.fromarray(np.where(arr > threshold, 255, 0).astype(np.uint8))
    return bw
