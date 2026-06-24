"""Tests for app.core.database."""
from unittest.mock import MagicMock, patch, call
import pytest


def test_get_db_yields_session():
    from app.core.database import get_db

    mock_session = MagicMock()
    with patch("app.core.database.SessionLocal", return_value=mock_session):
        gen = get_db()
        db = next(gen)
        assert db is mock_session


def test_get_db_closes_session_in_finally():
    from app.core.database import get_db

    mock_session = MagicMock()
    with patch("app.core.database.SessionLocal", return_value=mock_session):
        gen = get_db()
        next(gen)
        with pytest.raises(StopIteration):
            next(gen)
        mock_session.close.assert_called_once()


def test_get_db_closes_even_on_exception():
    from app.core.database import get_db

    mock_session = MagicMock()
    with patch("app.core.database.SessionLocal", return_value=mock_session):
        gen = get_db()
        next(gen)
        gen.throw(RuntimeError("boom"))  # generator's finally still runs
    mock_session.close.assert_called_once()


def test_init_db_creates_extensions_and_tables():
    from app.core.database import init_db

    mock_conn = MagicMock()
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)

    mock_engine = MagicMock()
    mock_engine.connect.return_value = mock_conn

    with patch("app.core.database.engine", mock_engine), \
         patch("app.core.database.Base") as MockBase:
        init_db()

    # Should have executed two SQL statements and called create_all
    assert mock_conn.execute.call_count == 2
    mock_conn.commit.assert_called_once()
    MockBase.metadata.create_all.assert_called_once_with(bind=mock_engine)
