"""Tests for app.models.crime_record."""
import uuid
from datetime import datetime

import pytest


def test_processing_status_values():
    from app.models.crime_record import ProcessingStatus
    assert ProcessingStatus.PENDING == "pending"
    assert ProcessingStatus.PROCESSING == "processing"
    assert ProcessingStatus.COMPLETED == "completed"
    assert ProcessingStatus.FAILED == "failed"


def test_source_type_values():
    from app.models.crime_record import SourceType
    assert SourceType.FIR == "fir"
    assert SourceType.NOTICE == "notice"
    assert SourceType.REPORT == "report"
    assert SourceType.OTHER == "other"


def test_crime_record_tablename():
    from app.models.crime_record import CrimeRecord
    assert CrimeRecord.__tablename__ == "crime_records"


def test_document_tablename():
    from app.models.crime_record import Document
    assert Document.__tablename__ == "documents"


def test_crime_record_default_is_published_false():
    from app.models.crime_record import CrimeRecord
    col = CrimeRecord.__table__.c["is_published"]
    assert col.default.arg is False


def test_crime_record_default_processing_status_pending():
    from app.models.crime_record import CrimeRecord, ProcessingStatus
    col = CrimeRecord.__table__.c["processing_status"]
    assert col.default.arg == ProcessingStatus.PENDING


def test_document_default_processing_status_pending():
    from app.models.crime_record import Document, ProcessingStatus
    col = Document.__table__.c["status"]
    assert col.default.arg == ProcessingStatus.PENDING


def test_crime_record_has_relationships():
    from app.models.crime_record import CrimeRecord
    assert hasattr(CrimeRecord, "documents")


def test_document_has_relationship():
    from app.models.crime_record import Document
    assert hasattr(Document, "crime_record")


def test_models_importable():
    from app.models import CrimeRecord, Document, ProcessingStatus, SourceType
    assert CrimeRecord is not None
    assert Document is not None
