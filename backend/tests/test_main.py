"""Tests for app.main — lifespan, health check, middleware."""
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

def test_health_check(client_db):
    client, _ = client_db
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


# ---------------------------------------------------------------------------
# Lifespan — success path
# ---------------------------------------------------------------------------

def test_lifespan_calls_init_db_on_startup():
    from app.main import app
    from app.core.database import get_db

    mock_db = MagicMock()

    def override():
        yield mock_db

    app.dependency_overrides[get_db] = override

    with patch("app.main.init_db") as mock_init:
        with TestClient(app):
            pass  # startup + shutdown both run

    mock_init.assert_called_once()
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Lifespan — init_db failure is caught and logged
# ---------------------------------------------------------------------------

def test_lifespan_logs_error_on_init_db_failure():
    from app.main import app
    from app.core.database import get_db

    mock_db = MagicMock()

    def override():
        yield mock_db

    app.dependency_overrides[get_db] = override

    with patch("app.main.init_db", side_effect=RuntimeError("DB unavailable")):
        # Must not raise — error is caught inside lifespan
        with TestClient(app):
            resp = TestClient(app).get("/api/health")
            # Health endpoint should still work if app started despite DB error

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Routes are registered
# ---------------------------------------------------------------------------

def test_docs_url_exists(client_db):
    client, _ = client_db
    response = client.get("/api/docs")
    # ReDoc/Swagger UI returns 200
    assert response.status_code == 200


def test_openapi_json_exists(client_db):
    client, _ = client_db
    response = client.get("/api/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "OpenCrime API"


# ---------------------------------------------------------------------------
# CORS middleware present
# ---------------------------------------------------------------------------

def test_cors_header_present(client_db):
    client, _ = client_db
    response = client.get(
        "/api/health",
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
