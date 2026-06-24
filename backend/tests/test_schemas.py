"""Tests for app.schemas.crime_record (Pydantic v2 schemas)."""
import uuid
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.schemas.crime_record import (
    AnalyticsSummary,
    CrimeRecordCreate,
    CrimeRecordOut,
    CrimeRecordSummary,
    DocumentOut,
    SearchQuery,
    SearchResult,
)


def _record_ns(**kw):
    defaults = dict(
        id=uuid.uuid4(),
        source_url=None,
        source_type="fir",
        crime_category="Cyber Fraud",
        crime_date=date(2024, 1, 15),
        registration_date=None,
        fir_number="CR/001",
        police_station="Test PS",
        district="Test District",
        state="Test State",
        legal_sections=["IPC 420"],
        amount_involved=Decimal("50000"),
        modus_operandi="Test",
        keywords=["fraud"],
        entities={},
        summary="Summary",
        redacted_text="Redacted",
        raw_text="Raw",
        latitude=12.0,
        longitude=77.0,
        is_published=True,
        processing_status="completed",
        created_at=datetime(2024, 1, 15, 10, 0),
        updated_at=datetime(2024, 1, 15, 10, 0),
        documents=[],
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


# --- DocumentOut ---

def test_document_out_from_attributes():
    ns = SimpleNamespace(
        id=uuid.uuid4(),
        filename="a.pdf",
        original_filename="orig.pdf",
        file_type="pdf",
        file_size=1024,
        status="pending",
        error_message=None,
        created_at=datetime(2024, 1, 1),
    )
    doc = DocumentOut.model_validate(ns, from_attributes=True)
    assert doc.filename == "a.pdf"
    assert doc.status == "pending"
    assert doc.error_message is None


# --- CrimeRecordCreate ---

def test_crime_record_create_minimal():
    r = CrimeRecordCreate()
    assert r.crime_category is None
    assert r.legal_sections == []


def test_crime_record_create_with_data():
    r = CrimeRecordCreate(crime_category="Robbery", fir_number="CR/001")
    assert r.crime_category == "Robbery"
    assert r.fir_number == "CR/001"


# --- CrimeRecordOut ---

def test_crime_record_out_from_attributes():
    ns = _record_ns()
    r = CrimeRecordOut.model_validate(ns, from_attributes=True)
    assert r.crime_category == "Cyber Fraud"
    assert r.state == "Test State"
    assert r.is_published is True


def test_crime_record_out_optional_defaults():
    ns = _record_ns(
        summary=None, redacted_text=None, keywords=None,
        entities=None, latitude=None, longitude=None, updated_at=None,
    )
    r = CrimeRecordOut.model_validate(ns, from_attributes=True)
    assert r.summary is None
    assert r.keywords == []
    assert r.entities == {}


# --- CrimeRecordSummary ---

def test_crime_record_summary_from_attributes():
    ns = _record_ns()
    s = CrimeRecordSummary.model_validate(ns, from_attributes=True)
    assert s.fir_number == "CR/001"
    assert s.processing_status == "completed"


def test_crime_record_summary_keywords_default():
    ns = _record_ns(keywords=None)
    s = CrimeRecordSummary.model_validate(ns, from_attributes=True)
    assert s.keywords == []


# --- SearchQuery ---

def test_search_query_required_q():
    with pytest.raises(Exception):
        SearchQuery()


def test_search_query_defaults():
    q = SearchQuery(q="fraud")
    assert q.page == 1
    assert q.page_size == 20
    assert q.crime_category is None


def test_search_query_all_fields():
    q = SearchQuery(
        q="fraud",
        crime_category="Cyber Fraud",
        state="Maharashtra",
        date_from=date(2024, 1, 1),
        date_to=date(2024, 12, 31),
        min_amount=Decimal("1000"),
        max_amount=Decimal("1000000"),
        page=2,
        page_size=50,
    )
    assert q.state == "Maharashtra"
    assert q.page == 2


# --- SearchResult ---

def test_search_result():
    ns = _record_ns()
    s = CrimeRecordSummary.model_validate(ns, from_attributes=True)
    result = SearchResult(total=1, page=1, page_size=20, results=[s])
    assert result.total == 1
    assert len(result.results) == 1


# --- AnalyticsSummary ---

def test_analytics_summary():
    a = AnalyticsSummary(
        total_records=100,
        by_category=[{"category": "Cyber Fraud", "count": 50}],
        by_state=[{"state": "Maharashtra", "count": 30}],
        by_month=[{"month": "2024-01", "count": 10}],
        recent_count_30d=5,
        total_amount_involved=Decimal("500000"),
    )
    assert a.total_records == 100
    assert a.recent_count_30d == 5


def test_analytics_summary_optional_amount():
    a = AnalyticsSummary(
        total_records=0,
        by_category=[],
        by_state=[],
        by_month=[],
        recent_count_30d=0,
        total_amount_involved=None,
    )
    assert a.total_amount_involved is None


# --- schemas __init__ re-exports ---

def test_schemas_init_importable():
    from app.schemas import (
        CrimeRecordCreate, CrimeRecordOut, CrimeRecordSummary,
        DocumentOut, SearchQuery, SearchResult, AnalyticsSummary,
    )
    assert CrimeRecordCreate is not None
