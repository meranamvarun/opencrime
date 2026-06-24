"""Tests for app.workers.processing — 100% branch coverage."""
import uuid
from unittest.mock import MagicMock, patch, call

import pytest

from app.models.crime_record import ProcessingStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_task(document_id: str, mock_db, mock_ocr_text="raw text",
              extracted=None, redacted="redacted", summary="summary",
              ocr_side_effect=None, extracted_dates=None):
    """Run process_document.apply() with all dependencies mocked."""
    if extracted is None:
        extracted = {"crime_category": "Robbery", "keywords": ["rob"]}
    if extracted_dates:
        extracted.update(extracted_dates)

    mock_doc = MagicMock()
    mock_doc.file_path = "/tmp/test.pdf"
    mock_db.query.return_value.filter.return_value.first.return_value = mock_doc
    mock_db.query.return_value.filter.return_value.first.return_value = mock_doc

    with patch("app.workers.processing.SessionLocal", return_value=mock_db), \
         patch("app.workers.processing.ocr_service.extract_text_from_file",
               side_effect=ocr_side_effect or None,
               return_value=mock_ocr_text if not ocr_side_effect else None), \
         patch("app.workers.processing.ai_service.extract_structured_data",
               return_value=extracted), \
         patch("app.workers.processing.ai_service.redact_pii",
               return_value=redacted), \
         patch("app.workers.processing.ai_service.generate_summary",
               return_value=summary), \
         patch("app.workers.processing.search_service.update_search_vector") as mock_sv:
        from app.workers.processing import process_document
        result = process_document.apply(args=[document_id])
        return result, mock_doc, mock_sv


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_process_document_success():
    mock_db = MagicMock()
    doc_id = str(uuid.uuid4())

    result, mock_doc, mock_sv = _run_task(doc_id, mock_db)

    # Document status should be updated
    assert mock_doc.status == ProcessingStatus.COMPLETED
    mock_sv.assert_called_once()
    mock_db.close.assert_called_once()


def test_process_document_sets_processing_status_before_ocr():
    """Status should be set to PROCESSING immediately after finding the document."""
    statuses = []

    mock_db = MagicMock()
    mock_doc = MagicMock()
    mock_doc.file_path = "/tmp/test.pdf"

    def capture_commit():
        statuses.append(mock_doc.status)

    mock_db.query.return_value.filter.return_value.first.return_value = mock_doc
    mock_db.commit.side_effect = capture_commit

    with patch("app.workers.processing.SessionLocal", return_value=mock_db), \
         patch("app.workers.processing.ocr_service.extract_text_from_file",
               return_value="text"), \
         patch("app.workers.processing.ai_service.extract_structured_data",
               return_value={}), \
         patch("app.workers.processing.ai_service.redact_pii", return_value="r"), \
         patch("app.workers.processing.ai_service.generate_summary", return_value="s"), \
         patch("app.workers.processing.search_service.update_search_vector"):
        from app.workers.processing import process_document
        process_document.apply(args=[str(uuid.uuid4())])

    # First commit should have seen PROCESSING
    assert ProcessingStatus.PROCESSING in statuses


def test_process_document_not_found_returns_early():
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None

    with patch("app.workers.processing.SessionLocal", return_value=mock_db), \
         patch("app.workers.processing.ocr_service.extract_text_from_file") as mock_ocr:
        from app.workers.processing import process_document
        process_document.apply(args=[str(uuid.uuid4())])

    mock_ocr.assert_not_called()
    mock_db.close.assert_called_once()


def test_process_document_parses_valid_crime_date():
    mock_db = MagicMock()
    doc_id = str(uuid.uuid4())
    extracted = {
        "crime_category": "Robbery",
        "keywords": [],
        "crime_date": "2024-03-15",
        "registration_date": "2024-03-16",
    }

    mock_doc = MagicMock()
    mock_doc.file_path = "/tmp/test.pdf"
    mock_db.query.return_value.filter.return_value.first.return_value = mock_doc

    with patch("app.workers.processing.SessionLocal", return_value=mock_db), \
         patch("app.workers.processing.ocr_service.extract_text_from_file",
               return_value="text"), \
         patch("app.workers.processing.ai_service.extract_structured_data",
               return_value=extracted), \
         patch("app.workers.processing.ai_service.redact_pii", return_value="r"), \
         patch("app.workers.processing.ai_service.generate_summary", return_value="s"), \
         patch("app.workers.processing.search_service.update_search_vector"), \
         patch("app.workers.processing.CrimeRecord") as MockRecord:
        instance = MagicMock()
        MockRecord.return_value = instance
        from app.workers.processing import process_document
        process_document.apply(args=[doc_id])

    # setattr should have been called for the dates
    from datetime import date
    instance.__setattr__.assert_any_call("crime_date", date(2024, 3, 15))
    instance.__setattr__.assert_any_call("registration_date", date(2024, 3, 16))


def test_process_document_ignores_invalid_date():
    mock_db = MagicMock()
    doc_id = str(uuid.uuid4())
    extracted = {
        "crime_category": "Robbery",
        "keywords": [],
        "crime_date": "not-a-date",
    }

    mock_doc = MagicMock()
    mock_doc.file_path = "/tmp/test.pdf"
    mock_db.query.return_value.filter.return_value.first.return_value = mock_doc

    with patch("app.workers.processing.SessionLocal", return_value=mock_db), \
         patch("app.workers.processing.ocr_service.extract_text_from_file",
               return_value="text"), \
         patch("app.workers.processing.ai_service.extract_structured_data",
               return_value=extracted), \
         patch("app.workers.processing.ai_service.redact_pii", return_value="r"), \
         patch("app.workers.processing.ai_service.generate_summary", return_value="s"), \
         patch("app.workers.processing.search_service.update_search_vector"):
        from app.workers.processing import process_document
        # Should not raise despite bad date
        process_document.apply(args=[doc_id])


def test_process_document_sets_failed_status_on_ocr_exception():
    mock_db = MagicMock()
    doc_id = str(uuid.uuid4())

    mock_doc = MagicMock()
    mock_doc.file_path = "/tmp/test.pdf"
    # First call (in try block) returns doc; second call (in except block) also returns doc
    mock_db.query.return_value.filter.return_value.first.return_value = mock_doc

    with patch("app.workers.processing.SessionLocal", return_value=mock_db), \
         patch("app.workers.processing.ocr_service.extract_text_from_file",
               side_effect=RuntimeError("OCR failed")):
        from app.workers.processing import process_document
        from celery.exceptions import Retry
        with pytest.raises((Retry, RuntimeError)):
            process_document.apply(args=[doc_id], throw=True)

    # Status set to FAILED in exception handler
    assert mock_doc.status == ProcessingStatus.FAILED
    mock_db.close.assert_called_once()


def test_process_document_handles_exception_in_error_handler():
    """If the error-handler's DB query also fails, it's silently swallowed."""
    mock_db = MagicMock()
    doc_id = str(uuid.uuid4())

    mock_doc = MagicMock()
    mock_doc.file_path = "/tmp/test.pdf"

    call_count = 0

    def first_side_effect():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return mock_doc
        raise RuntimeError("DB also failed")

    mock_db.query.return_value.filter.return_value.first.side_effect = first_side_effect

    with patch("app.workers.processing.SessionLocal", return_value=mock_db), \
         patch("app.workers.processing.ocr_service.extract_text_from_file",
               side_effect=RuntimeError("OCR failed")):
        from app.workers.processing import process_document
        from celery.exceptions import Retry
        with pytest.raises((Retry, RuntimeError)):
            process_document.apply(args=[doc_id], throw=True)

    # Should still close the session
    mock_db.close.assert_called_once()


def test_celery_app_configured():
    from app.workers.processing import celery_app
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.timezone == "UTC"
    assert celery_app.conf.enable_utc is True
