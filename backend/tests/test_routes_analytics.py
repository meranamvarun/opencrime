"""Tests for app.api.routes.analytics — 100% branch coverage."""
import uuid
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from tests.conftest import make_record_ns


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _setup_summary_mock(mock_db, total=10, by_cat=None, by_state=None, by_month=None,
                         recent=3, total_amount=Decimal("500000")):
    """Configure mock_db to satisfy get_analytics_summary's query chain."""
    by_cat = by_cat or [("Cyber Fraud", 5)]
    by_state = by_state or [("Maharashtra", 3)]
    by_month = by_month or [("2024-01", 2)]

    filt = mock_db.query.return_value.filter.return_value

    # scalar() calls: total, recent, total_amount (3 calls, in that order)
    filt.scalar.side_effect = [total, recent, total_amount]

    # .all() via .group_by().order_by().limit() — for by_category and by_state
    filt.group_by.return_value.order_by.return_value.limit.return_value.all.side_effect = [
        by_cat, by_state
    ]
    # .all() via .group_by().order_by() — for by_month (no limit)
    filt.group_by.return_value.order_by.return_value.all.return_value = by_month


# ---------------------------------------------------------------------------
# GET /analytics/summary
# ---------------------------------------------------------------------------

def test_summary_returns_aggregate_stats(client_db):
    client, mock_db = client_db
    _setup_summary_mock(mock_db)
    response = client.get("/api/v1/analytics/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["total_records"] == 10
    assert data["recent_count_30d"] == 3
    assert len(data["by_category"]) == 1
    assert data["by_category"][0]["category"] == "Cyber Fraud"


def test_summary_with_state_filter(client_db):
    client, mock_db = client_db
    _setup_summary_mock(mock_db)
    response = client.get("/api/v1/analytics/summary", params={"state": "Karnataka"})
    assert response.status_code == 200


def test_summary_null_scalar_becomes_zero(client_db):
    """scalar() returning None → OR 0 produces 0 in response."""
    client, mock_db = client_db
    filt = mock_db.query.return_value.filter.return_value
    filt.scalar.side_effect = [None, None, None]
    filt.group_by.return_value.order_by.return_value.limit.return_value.all.side_effect = [[], []]
    filt.group_by.return_value.order_by.return_value.all.return_value = []
    response = client.get("/api/v1/analytics/summary")
    assert response.status_code == 200
    assert response.json()["total_records"] == 0
    assert response.json()["recent_count_30d"] == 0


def test_summary_total_amount_none_is_ok(client_db):
    client, mock_db = client_db
    _setup_summary_mock(mock_db, total_amount=None)
    response = client.get("/api/v1/analytics/summary")
    assert response.status_code == 200
    assert response.json()["total_amount_involved"] is None


# ---------------------------------------------------------------------------
# GET /analytics/records
# ---------------------------------------------------------------------------

def test_list_records_no_filters(client_db):
    client, mock_db = client_db
    record = make_record_ns()

    filt = mock_db.query.return_value.filter.return_value
    filt.scalar.return_value = 1
    filt.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [record]

    response = client.get("/api/v1/analytics/records")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["results"]) == 1


def test_list_records_with_state_and_category(client_db):
    client, mock_db = client_db
    filt = mock_db.query.return_value.filter.return_value
    filt.scalar.return_value = 0
    filt.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []

    response = client.get("/api/v1/analytics/records", params={
        "state": "Maharashtra",
        "crime_category": "Robbery",
        "page": "2",
        "page_size": "5",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 2
    assert data["page_size"] == 5


def test_list_records_null_count_returns_zero(client_db):
    client, mock_db = client_db
    filt = mock_db.query.return_value.filter.return_value
    filt.scalar.return_value = None
    filt.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []

    response = client.get("/api/v1/analytics/records")
    assert response.json()["total"] == 0


# ---------------------------------------------------------------------------
# GET /analytics/records/{record_id}
# ---------------------------------------------------------------------------

def test_get_record_valid_uuid(client_db):
    client, mock_db = client_db
    record_id = uuid.uuid4()
    record = make_record_ns(id=record_id)
    mock_db.query.return_value.filter.return_value.first.return_value = record

    response = client.get(f"/api/v1/analytics/records/{record_id}")
    assert response.status_code == 200
    assert response.json()["crime_category"] == "Cyber Fraud"


def test_get_record_invalid_uuid_returns_400(client_db):
    client, mock_db = client_db
    response = client.get("/api/v1/analytics/records/not-a-uuid")
    assert response.status_code == 400
    assert "Invalid record ID" in response.json()["detail"]


def test_get_record_not_found_returns_404(client_db):
    client, mock_db = client_db
    mock_db.query.return_value.filter.return_value.first.return_value = None
    response = client.get(f"/api/v1/analytics/records/{uuid.uuid4()}")
    assert response.status_code == 404
    assert "Record not found" in response.json()["detail"]


# ---------------------------------------------------------------------------
# GET /analytics/map
# ---------------------------------------------------------------------------

def _make_map_row(record_id=None, cat="Cyber Fraud", district="Test",
                  state="Karnataka", lat=12.97, lng=77.59, dt=None):
    return (record_id or uuid.uuid4(), cat, district, state, lat, lng, dt)


def test_map_data_with_results(client_db):
    client, mock_db = client_db
    row = _make_map_row(dt=date(2024, 1, 15))
    mock_db.query.return_value.filter.return_value.limit.return_value.all.return_value = [row]

    response = client.get("/api/v1/analytics/map")
    assert response.status_code == 200
    points = response.json()["points"]
    assert len(points) == 1
    assert points[0]["lat"] == 12.97
    assert points[0]["date"] == "2024-01-15"


def test_map_data_none_date_becomes_null(client_db):
    client, mock_db = client_db
    row = _make_map_row(dt=None)
    mock_db.query.return_value.filter.return_value.limit.return_value.all.return_value = [row]

    response = client.get("/api/v1/analytics/map")
    assert response.json()["points"][0]["date"] is None


def test_map_data_with_state_filter(client_db):
    client, mock_db = client_db
    mock_db.query.return_value.filter.return_value.limit.return_value.all.return_value = []
    response = client.get("/api/v1/analytics/map", params={"state": "Karnataka"})
    assert response.status_code == 200
    assert response.json()["points"] == []


def test_map_data_empty_results(client_db):
    client, mock_db = client_db
    mock_db.query.return_value.filter.return_value.limit.return_value.all.return_value = []
    response = client.get("/api/v1/analytics/map")
    assert response.status_code == 200
    assert response.json()["points"] == []
