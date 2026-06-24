"""Tests for app.services.search_service — 100% branch coverage."""
import uuid
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, call

import pytest


# ---------------------------------------------------------------------------
# full_text_search
# ---------------------------------------------------------------------------

def _make_db():
    """Return a MagicMock that responds to the query chain."""
    db = MagicMock()
    chain = db.query.return_value.filter.return_value
    chain.count.return_value = 0
    chain.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
    return db, chain


def test_full_text_search_returns_zero_and_empty_on_no_results():
    from app.services.search_service import full_text_search

    db, chain = _make_db()
    total, results = full_text_search(db, "fraud")

    assert total == 0
    assert results == []


def test_full_text_search_returns_results():
    from app.services.search_service import full_text_search

    db, chain = _make_db()
    mock_record = MagicMock()
    chain.count.return_value = 1
    chain.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [mock_record]

    total, results = full_text_search(db, "robbery")
    assert total == 1
    assert results == [mock_record]


def test_full_text_search_blank_query_skips_tsvector_filter():
    """A whitespace-only query must not build a ts_query filter."""
    from app.services.search_service import full_text_search
    from sqlalchemy import func

    db, chain = _make_db()
    with patch("app.services.search_service.func.to_tsquery") as mock_tsq:
        full_text_search(db, "   ")
    mock_tsq.assert_not_called()


def test_full_text_search_single_short_word_skips_tsvector():
    """Words shorter than 2 chars are stripped; empty sanitized → no filter."""
    from app.services.search_service import full_text_search

    db, chain = _make_db()
    with patch("app.services.search_service.func.to_tsquery") as mock_tsq:
        full_text_search(db, "a")  # only 1-char word → stripped
    mock_tsq.assert_not_called()


def test_full_text_search_with_crime_category_filter():
    from app.services.search_service import full_text_search

    db, chain = _make_db()
    full_text_search(db, "fraud", crime_category="Cyber Fraud")
    # Query was called — simply verify no exception and DB queried
    db.query.assert_called()


def test_full_text_search_with_state_filter():
    from app.services.search_service import full_text_search

    db, chain = _make_db()
    full_text_search(db, "theft", state="Maharashtra")
    db.query.assert_called()


def test_full_text_search_with_district_filter():
    from app.services.search_service import full_text_search

    db, chain = _make_db()
    full_text_search(db, "theft", district="Mumbai")
    db.query.assert_called()


def test_full_text_search_with_date_from_filter():
    from app.services.search_service import full_text_search

    db, chain = _make_db()
    full_text_search(db, "fraud", date_from=date(2024, 1, 1))
    db.query.assert_called()


def test_full_text_search_with_date_to_filter():
    from app.services.search_service import full_text_search

    db, chain = _make_db()
    full_text_search(db, "fraud", date_to=date(2024, 12, 31))
    db.query.assert_called()


def test_full_text_search_with_amount_filters():
    from app.services.search_service import full_text_search

    db, chain = _make_db()
    full_text_search(
        db, "fraud",
        min_amount=Decimal("1000"),
        max_amount=Decimal("1000000"),
    )
    db.query.assert_called()


def test_full_text_search_pagination_offset():
    from app.services.search_service import full_text_search

    db, chain = _make_db()
    full_text_search(db, "fraud", page=3, page_size=10)
    # offset should be (3-1)*10 = 20
    offset_call = chain.order_by.return_value.offset
    offset_call.assert_called_once_with(20)


def test_full_text_search_all_filters_combined():
    from app.services.search_service import full_text_search

    db, chain = _make_db()
    full_text_search(
        db, "cyber fraud",
        crime_category="Cyber Fraud",
        state="Karnataka",
        district="Bengaluru",
        date_from=date(2024, 1, 1),
        date_to=date(2024, 12, 31),
        min_amount=Decimal("5000"),
        max_amount=Decimal("500000"),
        page=2,
        page_size=5,
    )
    db.query.assert_called()


# ---------------------------------------------------------------------------
# update_search_vector
# ---------------------------------------------------------------------------

def _make_record(**kwargs):
    defaults = dict(
        id=uuid.uuid4(),
        redacted_text="redacted text",
        raw_text="raw text",
        crime_category="Cyber Fraud",
        summary="summary",
        police_station="Test PS",
        district="Test District",
        state="Test State",
        modus_operandi="modus",
        keywords=["fraud", "cyber"],
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_update_search_vector_executes_sql_when_text_present():
    from app.services.search_service import update_search_vector

    db = MagicMock()
    record = _make_record()
    update_search_vector(db, record)

    db.execute.assert_called_once()
    db.commit.assert_called_once()
    # Verify the SQL contains the right placeholder
    sql_arg = str(db.execute.call_args[0][0])
    assert "search_vector" in sql_arg


def test_update_search_vector_uses_redacted_text_over_raw():
    from app.services.search_service import update_search_vector

    db = MagicMock()
    record = _make_record(redacted_text="Redacted content", raw_text="Raw content")
    update_search_vector(db, record)

    params = db.execute.call_args[0][1]
    assert "Redacted content" in params["txt"]
    assert "Raw content" not in params["txt"]


def test_update_search_vector_falls_back_to_raw_when_no_redacted():
    from app.services.search_service import update_search_vector

    db = MagicMock()
    record = _make_record(redacted_text=None, raw_text="Raw content only")
    update_search_vector(db, record)

    params = db.execute.call_args[0][1]
    assert "Raw content only" in params["txt"]


def test_update_search_vector_skips_execute_when_all_fields_empty():
    from app.services.search_service import update_search_vector

    db = MagicMock()
    record = _make_record(
        redacted_text=None, raw_text=None,
        crime_category=None, summary=None,
        police_station=None, district=None,
        state=None, modus_operandi=None,
        keywords=[],
    )
    update_search_vector(db, record)

    db.execute.assert_not_called()
    db.commit.assert_not_called()


def test_update_search_vector_handles_none_keywords():
    from app.services.search_service import update_search_vector

    db = MagicMock()
    record = _make_record(keywords=None)
    update_search_vector(db, record)
    db.execute.assert_called_once()


def test_update_search_vector_truncates_very_long_text():
    from app.services.search_service import update_search_vector

    db = MagicMock()
    record = _make_record(redacted_text="x" * 100_000)
    update_search_vector(db, record)

    params = db.execute.call_args[0][1]
    assert len(params["txt"]) <= 50_000
