"""Tests for app.services.ocr_service — 100% branch coverage."""
from unittest.mock import MagicMock, patch, call
import pytest


# ---------------------------------------------------------------------------
# extract_text_from_file — dispatch
# ---------------------------------------------------------------------------

def test_extract_pdf_calls_pdf_extractor():
    with patch("app.services.ocr_service._extract_from_pdf", return_value="pdf text") as mock_pdf:
        from app.services.ocr_service import extract_text_from_file
        result = extract_text_from_file("/tmp/doc.pdf")
    mock_pdf.assert_called_once_with("/tmp/doc.pdf")
    assert result == "pdf text"


@pytest.mark.parametrize("path", [
    "/tmp/doc.png",
    "/tmp/doc.jpg",
    "/tmp/doc.jpeg",
    "/tmp/doc.tiff",
    "/tmp/doc.tif",
    "/tmp/doc.bmp",
    "/tmp/doc.webp",
])
def test_extract_image_types_call_image_extractor(path):
    with patch("app.services.ocr_service._extract_from_image", return_value="img text") as mock_img:
        from app.services.ocr_service import extract_text_from_file
        result = extract_text_from_file(path)
    mock_img.assert_called_once_with(path)
    assert result == "img text"


def test_extract_unsupported_type_raises():
    from app.services.ocr_service import extract_text_from_file
    with pytest.raises(ValueError, match="Unsupported file type"):
        extract_text_from_file("/tmp/doc.docx")


# ---------------------------------------------------------------------------
# _extract_from_pdf
# ---------------------------------------------------------------------------

def test_extract_from_pdf_success_single_page():
    mock_page = MagicMock()

    with patch("app.services.ocr_service._extract_from_pdf.__module__"):
        pass  # just to ensure import

    with patch("pdf2image.convert_from_path", return_value=[mock_page]) as mock_convert, \
         patch("pytesseract.image_to_string", return_value="page1 text") as mock_ocr:
        from app.services.ocr_service import _extract_from_pdf
        result = _extract_from_pdf("/tmp/doc.pdf")

    mock_convert.assert_called_once_with("/tmp/doc.pdf", dpi=300)
    assert result == "page1 text"


def test_extract_from_pdf_multipage_joined_with_separator():
    pages = [MagicMock(), MagicMock()]

    with patch("pdf2image.convert_from_path", return_value=pages), \
         patch("pytesseract.image_to_string", side_effect=["page1", "page2"]):
        from app.services.ocr_service import _extract_from_pdf
        result = _extract_from_pdf("/tmp/multi.pdf")

    assert "page1" in result
    assert "page2" in result
    assert "--- Page Break ---" in result


def test_extract_from_pdf_raises_on_exception():
    with patch("pdf2image.convert_from_path", side_effect=Exception("poppler missing")):
        from app.services.ocr_service import _extract_from_pdf
        with pytest.raises(Exception, match="poppler missing"):
            _extract_from_pdf("/tmp/bad.pdf")


# ---------------------------------------------------------------------------
# _extract_from_image
# ---------------------------------------------------------------------------

def test_extract_from_image_success():
    mock_img = MagicMock()

    with patch("PIL.Image.open", return_value=mock_img) as mock_open, \
         patch("pytesseract.image_to_string", return_value="image text") as mock_ocr:
        from app.services.ocr_service import _extract_from_image
        result = _extract_from_image("/tmp/photo.jpg")

    mock_open.assert_called_once_with("/tmp/photo.jpg")
    mock_ocr.assert_called_once_with(mock_img, lang="eng+hin")
    assert result == "image text"


def test_extract_from_image_raises_on_exception():
    with patch("PIL.Image.open", side_effect=OSError("file not found")):
        from app.services.ocr_service import _extract_from_image
        with pytest.raises(OSError, match="file not found"):
            _extract_from_image("/tmp/missing.jpg")


# ---------------------------------------------------------------------------
# get_file_type
# ---------------------------------------------------------------------------

def test_get_file_type_pdf():
    from app.services.ocr_service import get_file_type
    assert get_file_type("/tmp/doc.pdf") == "pdf"


@pytest.mark.parametrize("path", ["/tmp/a.png", "/tmp/a.jpg", "/tmp/a.jpeg"])
def test_get_file_type_image(path):
    from app.services.ocr_service import get_file_type
    assert get_file_type(path) == "image"


@pytest.mark.parametrize("path", ["/tmp/a.tiff", "/tmp/a.tif"])
def test_get_file_type_tiff(path):
    from app.services.ocr_service import get_file_type
    assert get_file_type(path) == "image"


def test_get_file_type_unknown():
    from app.services.ocr_service import get_file_type
    assert get_file_type("/tmp/doc.docx") == "unknown"
