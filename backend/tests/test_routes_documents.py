"""Tests for app.api.routes.documents — 100% branch coverage."""
import io
import uuid
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, call

import pytest

from app.models.crime_record import ProcessingStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_doc_ns(doc_id=None, **kwargs):
    defaults = dict(
        id=doc_id or uuid.uuid4(),
        filename="saved.pdf",
        original_filename="test.pdf",
        file_type="pdf",
        file_size=1024,
        status="pending",
        error_message=None,
        crime_record_id=None,
        created_at=datetime(2024, 3, 1, 10, 0, 0),
        updated_at=datetime(2024, 3, 1, 10, 0, 0),
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _make_record_ns(record_id=None, **kwargs):
    from tests.conftest import make_record_ns
    ns = make_record_ns()
    if record_id:
        ns.id = record_id
    for k, v in kwargs.items():
        setattr(ns, k, v)
    return ns


# ---------------------------------------------------------------------------
# POST /upload
# ---------------------------------------------------------------------------

def test_upload_pdf_success(client_db):
    client, mock_db = client_db
    doc_ns = _make_doc_ns()

    with patch("app.api.routes.documents.Document") as MockDoc, \
         patch("app.api.routes.documents.shutil.copyfileobj"), \
         patch("builtins.open", create=True), \
         patch("app.api.routes.documents._process_document_bg"):
        MockDoc.return_value = doc_ns
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("report.pdf", b"pdfcontent", "application/pdf")},
        )

    assert response.status_code == 202
    data = response.json()
    assert data["file_type"] == "pdf"


def test_upload_image_success(client_db):
    client, mock_db = client_db
    doc_ns = _make_doc_ns(file_type="jpg")

    with patch("app.api.routes.documents.Document") as MockDoc, \
         patch("app.api.routes.documents.shutil.copyfileobj"), \
         patch("builtins.open", create=True), \
         patch("app.api.routes.documents._process_document_bg"):
        MockDoc.return_value = doc_ns
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("photo.jpg", b"imgdata", "image/jpeg")},
        )

    assert response.status_code == 202


def test_upload_png_by_extension_accepted(client_db):
    """Content-type not in ALLOWED_TYPES but filename ends with .png — allowed."""
    client, mock_db = client_db
    doc_ns = _make_doc_ns(file_type="png")

    with patch("app.api.routes.documents.Document") as MockDoc, \
         patch("app.api.routes.documents.shutil.copyfileobj"), \
         patch("builtins.open", create=True), \
         patch("app.api.routes.documents._process_document_bg"):
        MockDoc.return_value = doc_ns
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("image.png", b"data", "application/octet-stream")},
        )

    assert response.status_code == 202


def test_upload_unsupported_type_returns_400(client_db):
    client, mock_db = client_db
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("doc.docx", b"data", "application/vnd.openxmlformats")},
    )
    assert response.status_code == 400
    assert "Unsupported" in response.json()["detail"]


def test_upload_oversized_file_returns_413(client_db):
    client, mock_db = client_db
    # 51 MB > 50 MB limit
    big_content = b"x" * (51 * 1024 * 1024)
    with patch("app.api.routes.documents.shutil.copyfileobj"), \
         patch("builtins.open", create=True):
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("big.pdf", big_content, "application/pdf")},
        )
    assert response.status_code == 413


def test_upload_file_without_extension_uses_pdf_default(client_db):
    """A filename with no extension should default to .pdf."""
    client, mock_db = client_db
    doc_ns = _make_doc_ns()

    with patch("app.api.routes.documents.Document") as MockDoc, \
         patch("app.api.routes.documents.shutil.copyfileobj"), \
         patch("builtins.open", create=True), \
         patch("app.api.routes.documents._process_document_bg"):
        MockDoc.return_value = doc_ns
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("noext", b"data", "application/pdf")},
        )

    assert response.status_code == 202


# ---------------------------------------------------------------------------
# GET /{document_id}
# ---------------------------------------------------------------------------

def test_get_document_found(client_db):
    client, mock_db = client_db
    doc_id = uuid.uuid4()
    doc_ns = _make_doc_ns(doc_id=doc_id)
    mock_db.query.return_value.filter.return_value.first.return_value = doc_ns

    response = client.get(f"/api/v1/documents/{doc_id}")
    assert response.status_code == 200
    assert response.json()["filename"] == "saved.pdf"


def test_get_document_not_found(client_db):
    client, mock_db = client_db
    mock_db.query.return_value.filter.return_value.first.return_value = None

    response = client.get(f"/api/v1/documents/{uuid.uuid4()}")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /{document_id}/record
# ---------------------------------------------------------------------------

def test_get_document_record_returns_record(client_db):
    client, mock_db = client_db
    doc_id = uuid.uuid4()
    record_id = uuid.uuid4()

    doc_ns = _make_doc_ns(doc_id=doc_id, crime_record_id=record_id)
    record_ns = _make_record_ns(record_id=record_id)

    first_values = [doc_ns, record_ns]

    def first_side_effect():
        return first_values.pop(0)

    mock_db.query.return_value.filter.return_value.first.side_effect = first_side_effect

    response = client.get(f"/api/v1/documents/{doc_id}/record")
    assert response.status_code == 200
    assert response.json()["crime_category"] == "Cyber Fraud"


def test_get_document_record_document_not_found(client_db):
    client, mock_db = client_db
    mock_db.query.return_value.filter.return_value.first.return_value = None

    response = client.get(f"/api/v1/documents/{uuid.uuid4()}/record")
    assert response.status_code == 404
    assert "Document not found" in response.json()["detail"]


def test_get_document_record_no_crime_record_id(client_db):
    client, mock_db = client_db
    doc_ns = _make_doc_ns(crime_record_id=None)
    mock_db.query.return_value.filter.return_value.first.return_value = doc_ns

    response = client.get(f"/api/v1/documents/{uuid.uuid4()}/record")
    assert response.status_code == 404
    assert "not yet processed" in response.json()["detail"]


def test_get_document_record_crime_record_not_in_db(client_db):
    client, mock_db = client_db
    doc_id = uuid.uuid4()
    record_id = uuid.uuid4()

    doc_ns = _make_doc_ns(doc_id=doc_id, crime_record_id=record_id)
    first_values = [doc_ns, None]

    def first_side_effect():
        return first_values.pop(0)

    mock_db.query.return_value.filter.return_value.first.side_effect = first_side_effect

    response = client.get(f"/api/v1/documents/{doc_id}/record")
    assert response.status_code == 404
    assert "Crime record not found" in response.json()["detail"]


# ---------------------------------------------------------------------------
# _process_document_bg
# ---------------------------------------------------------------------------

def test_process_document_bg_uses_celery():
    from app.api.routes.documents import _process_document_bg

    doc_id = str(uuid.uuid4())
    with patch("app.workers.processing.process_document") as mock_task:
        _process_document_bg(doc_id)
    mock_task.delay.assert_called_once_with(doc_id)


def test_process_document_bg_falls_back_to_sync_on_celery_failure():
    from app.api.routes.documents import _process_document_bg

    doc_id = str(uuid.uuid4())
    with patch("app.workers.processing.process_document") as mock_task, \
         patch("app.api.routes.documents._process_sync") as mock_sync:
        mock_task.delay.side_effect = Exception("Redis down")
        _process_document_bg(doc_id)
    mock_sync.assert_called_once_with(doc_id)


# ---------------------------------------------------------------------------
# _process_sync
# ---------------------------------------------------------------------------

def test_process_sync_full_success():
    from app.api.routes.documents import _process_sync

    mock_db = MagicMock()
    mock_doc = MagicMock()
    mock_doc.file_path = "/tmp/x.pdf"
    mock_db.query.return_value.filter.return_value.first.return_value = mock_doc

    with patch("app.api.routes.documents.SessionLocal", return_value=mock_db), \
         patch("app.core.database.SessionLocal", return_value=mock_db):
        with patch("app.services.ocr_service.extract_text_from_file",
                   return_value="text"), \
             patch("app.services.ai_service.extract_structured_data",
                   return_value={"crime_category": "X", "keywords": []}), \
             patch("app.services.ai_service.redact_pii", return_value="r"), \
             patch("app.services.ai_service.generate_summary", return_value="s"), \
             patch("app.services.search_service.update_search_vector"):
            _process_sync(str(uuid.uuid4()))

    assert mock_doc.status == ProcessingStatus.COMPLETED
    mock_db.close.assert_called_once()


def test_process_sync_doc_not_found_returns_early():
    from app.api.routes.documents import _process_sync

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None

    with patch("app.core.database.SessionLocal", return_value=mock_db):
        _process_sync(str(uuid.uuid4()))

    mock_db.close.assert_called_once()


def test_process_sync_parses_valid_dates():
    from app.api.routes.documents import _process_sync

    mock_db = MagicMock()
    mock_doc = MagicMock()
    mock_doc.file_path = "/tmp/x.pdf"
    mock_db.query.return_value.filter.return_value.first.return_value = mock_doc

    extracted = {
        "crime_category": "X",
        "keywords": [],
        "crime_date": "2024-01-15",
        "registration_date": "2024-01-16",
    }

    with patch("app.core.database.SessionLocal", return_value=mock_db), \
         patch("app.services.ocr_service.extract_text_from_file", return_value="t"), \
         patch("app.services.ai_service.extract_structured_data", return_value=extracted), \
         patch("app.services.ai_service.redact_pii", return_value="r"), \
         patch("app.services.ai_service.generate_summary", return_value="s"), \
         patch("app.services.search_service.update_search_vector"), \
         patch("app.api.routes.documents.CrimeRecord") as MockRecord:
        instance = MagicMock()
        MockRecord.return_value = instance
        _process_sync(str(uuid.uuid4()))

    from datetime import date
    instance.__setattr__.assert_any_call("crime_date", date(2024, 1, 15))


def test_process_sync_ignores_invalid_date():
    from app.api.routes.documents import _process_sync

    mock_db = MagicMock()
    mock_doc = MagicMock()
    mock_doc.file_path = "/tmp/x.pdf"
    mock_db.query.return_value.filter.return_value.first.return_value = mock_doc

    extracted = {"crime_category": "X", "keywords": [], "crime_date": "bad-date"}

    with patch("app.core.database.SessionLocal", return_value=mock_db), \
         patch("app.services.ocr_service.extract_text_from_file", return_value="t"), \
         patch("app.services.ai_service.extract_structured_data", return_value=extracted), \
         patch("app.services.ai_service.redact_pii", return_value="r"), \
         patch("app.services.ai_service.generate_summary", return_value="s"), \
         patch("app.services.search_service.update_search_vector"):
        _process_sync(str(uuid.uuid4()))  # must not raise

    mock_db.close.assert_called_once()


def test_process_sync_marks_failed_and_continues_on_ocr_error():
    from app.api.routes.documents import _process_sync

    mock_db = MagicMock()
    mock_doc = MagicMock()
    mock_doc.file_path = "/tmp/x.pdf"
    mock_db.query.return_value.filter.return_value.first.return_value = mock_doc

    with patch("app.core.database.SessionLocal", return_value=mock_db), \
         patch("app.services.ocr_service.extract_text_from_file",
               side_effect=RuntimeError("OCR failed")):
        _process_sync(str(uuid.uuid4()))

    assert mock_doc.status == ProcessingStatus.FAILED
    assert "OCR failed" in mock_doc.error_message
    mock_db.close.assert_called_once()


def test_process_sync_error_handler_db_failure_is_silenced():
    """If the error-handler's DB query fails, it's silently ignored."""
    from app.api.routes.documents import _process_sync

    mock_db = MagicMock()
    call_count = 0

    def first_side_effect():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            doc = MagicMock()
            doc.file_path = "/tmp/x.pdf"
            return doc
        raise RuntimeError("DB error in handler")

    mock_db.query.return_value.filter.return_value.first.side_effect = first_side_effect

    with patch("app.core.database.SessionLocal", return_value=mock_db), \
         patch("app.services.ocr_service.extract_text_from_file",
               side_effect=RuntimeError("OCR")):
        _process_sync(str(uuid.uuid4()))  # must not raise

    mock_db.close.assert_called_once()
