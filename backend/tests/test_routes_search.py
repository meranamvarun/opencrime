"""Tests for app.api.routes.search — 100% branch coverage."""
import uuid
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from tests.conftest import make_record_ns


# ---------------------------------------------------------------------------
# GET /search
# ---------------------------------------------------------------------------

def test_search_basic_query(client_db):
    client, mock_db = client_db
    record = make_record_ns()

    with patch("app.api.routes.search.full_text_search", return_value=(1, [record])):
        response = client.get("/api/v1/search", params={"q": "cyber fraud"})

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["page"] == 1
    assert len(data["results"]) == 1
    assert data["results"][0]["crime_category"] == "Cyber Fraud"


def test_search_returns_empty_results(client_db):
    client, mock_db = client_db
    with patch("app.api.routes.search.full_text_search", return_value=(0, [])):
        response = client.get("/api/v1/search", params={"q": "nothing"})

    assert response.status_code == 200
    assert response.json()["total"] == 0
    assert response.json()["results"] == []


def test_search_with_all_filters(client_db):
    client, mock_db = client_db
    record = make_record_ns()

    with patch("app.api.routes.search.full_text_search", return_value=(1, [record])) as mock_fts:
        response = client.get("/api/v1/search", params={
            "q": "robbery",
            "crime_category": "Robbery",
            "state": "Maharashtra",
            "district": "Mumbai",
            "date_from": "2024-01-01",
            "date_to": "2024-12-31",
            "min_amount": "5000",
            "max_amount": "500000",
            "page": "2",
            "page_size": "10",
        })

    assert response.status_code == 200
    call_kwargs = mock_fts.call_args[1]
    assert call_kwargs["page"] == 2
    assert call_kwargs["page_size"] == 10
    assert call_kwargs["crime_category"] == "Robbery"
    assert call_kwargs["state"] == "Maharashtra"


def test_search_missing_q_returns_422(client_db):
    client, mock_db = client_db
    response = client.get("/api/v1/search")
    assert response.status_code == 422


def test_search_pagination_reflected_in_response(client_db):
    client, mock_db = client_db
    with patch("app.api.routes.search.full_text_search", return_value=(50, [])):
        response = client.get("/api/v1/search", params={"q": "fraud", "page": "3", "page_size": "5"})

    data = response.json()
    assert data["page"] == 3
    assert data["page_size"] == 5


# ---------------------------------------------------------------------------
# GET /search/suggestions
# ---------------------------------------------------------------------------

def test_suggestions_returns_categories_and_states(client_db):
    client, mock_db = client_db
    mock_db.query.return_value.filter.return_value.distinct.return_value.limit.return_value.all.side_effect = [
        [("Cyber Fraud",)],  # categories
        [("Maharashtra",)],  # states
    ]
    response = client.get("/api/v1/search/suggestions", params={"q": "cyber"})

    assert response.status_code == 200
    data = response.json()
    assert "Cyber Fraud" in data["categories"]
    assert "Maharashtra" in data["states"]


def test_suggestions_filters_none_values(client_db):
    """None entries in query results must be excluded."""
    client, mock_db = client_db
    mock_db.query.return_value.filter.return_value.distinct.return_value.limit.return_value.all.side_effect = [
        [(None,), ("Cyber Fraud",)],  # first has None
        [(None,)],
    ]
    response = client.get("/api/v1/search/suggestions", params={"q": "cy"})

    assert response.status_code == 200
    data = response.json()
    assert None not in data["categories"]
    assert None not in data["states"]
    assert "Cyber Fraud" in data["categories"]


def test_suggestions_q_too_short_returns_422(client_db):
    client, mock_db = client_db
    response = client.get("/api/v1/search/suggestions", params={"q": "x"})
    assert response.status_code == 422
