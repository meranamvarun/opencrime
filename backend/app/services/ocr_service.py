import os
import tempfile
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def extract_text_from_file(file_path: str) -> str:
    """Extract text from PDF or image using OCR."""
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return _extract_from_pdf(file_path)
    elif suffix in (".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp"):
        return _extract_from_image(file_path)
    else:
        raise ValueError(f"Unsupported file type: {suffix}")


def _extract_from_pdf(file_path: str) -> str:
    try:
        from pdf2image import convert_from_path
        import pytesseract

        pages = convert_from_path(file_path, dpi=300)
        texts = []
        for i, page in enumerate(pages):
            text = pytesseract.image_to_string(page, lang="eng+hin")
            texts.append(text)
            logger.info(f"Extracted text from page {i+1}/{len(pages)}")
        return "\n\n--- Page Break ---\n\n".join(texts)
    except Exception as e:
        logger.error(f"PDF OCR failed: {e}")
        raise


def _extract_from_image(file_path: str) -> str:
    try:
        import pytesseract
        from PIL import Image

        img = Image.open(file_path)
        text = pytesseract.image_to_string(img, lang="eng+hin")
        return text
    except Exception as e:
        logger.error(f"Image OCR failed: {e}")
        raise


def get_file_type(file_path: str) -> str:
    suffix = Path(file_path).suffix.lower()
    if suffix == ".pdf":
        return "pdf"
    elif suffix in (".png", ".jpg", ".jpeg"):
        return "image"
    elif suffix in (".tiff", ".tif"):
        return "image"
    return "unknown"
