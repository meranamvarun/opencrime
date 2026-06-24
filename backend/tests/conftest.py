"""Shared pytest fixtures for all tests."""
import uuid
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.models.crime_record import Document, ProcessingStatus, SourceType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_record_ns(**overrides):
    """SimpleNamespace that satisfies CrimeRecordSummary / CrimeRecordOut."""
    defaults = dict(
        id=uuid.uuid4(),
        source_url=None,
        source_type="fir",
        crime_category="Cyber Fraud",
        crime_date=date(2024, 3, 15),
        registration_date=None,
        fir_number="CR/2024/001",
        police_station="Test PS",
        district="Test District",
        state="Test State",
        legal_sections=["IPC 420"],
        amount_involved=Decimal("50000"),
        modus_operandi="Test modus operandi",
        keywords=["fraud", "cyber"],
        entities={"organizations": []},
        summary="Test summary",
        redacted_text="Redacted text",
        raw_text="Raw text",
        latitude=12.97,
        longitude=77.59,
        is_published=True,
        processing_status="completed",
        created_at=datetime(2024, 3, 15, 10, 0, 0),
        updated_at=datetime(2024, 3, 15, 10, 0, 0),
        documents=[],
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def make_doc_ns(**overrides):
    """SimpleNamespace that satisfies DocumentOut."""
    defaults = dict(
        id=uuid.uuid4(),
        filename="saved_abc.pdf",
        original_filename="test.pdf",
        file_type="pdf",
        file_size=1024,
        status="pending",
        error_message=None,
        crime_record_id=None,
        created_at=datetime(2024, 3, 15, 10, 0, 0),
        updated_at=datetime(2024, 3, 15, 10, 0, 0),
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


# ---------------------------------------------------------------------------
# Core DB mock
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_db():
    """Return a fresh MagicMock session for each test."""
    return MagicMock()


# ---------------------------------------------------------------------------
# FastAPI TestClient with mocked DB and mocked init_db
# ---------------------------------------------------------------------------

@pytest.fixture
def client_db():
    """Return (TestClient, mock_db) with get_db and init_db overridden."""
    from app.main import app
    from app.core.database import get_db

    db = MagicMock()

    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db

    with patch("app.main.init_db"):
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c, db

    app.dependency_overrides.clear()
