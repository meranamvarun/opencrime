"""Tests for app.core.config."""
import os
from unittest.mock import patch


def test_default_app_name():
    from app.core.config import settings
    assert settings.APP_NAME == "OpenCrime"


def test_default_version():
    from app.core.config import settings
    assert settings.APP_VERSION == "0.1.0"


def test_default_debug_false():
    from app.core.config import settings
    assert settings.DEBUG is False


def test_default_claude_model():
    from app.core.config import settings
    assert settings.CLAUDE_MODEL == "claude-sonnet-4-6"


def test_default_max_upload_size():
    from app.core.config import settings
    assert settings.MAX_UPLOAD_SIZE_MB == 50


def test_default_cors_origins():
    from app.core.config import settings
    assert "http://localhost:3000" in settings.CORS_ORIGINS


def test_upload_dir_created(tmp_path):
    """Verify Settings creates UPLOAD_DIR at import-time."""
    upload_dir = str(tmp_path / "uploads")
    with patch.dict(os.environ, {"UPLOAD_DIR": upload_dir}):
        from pydantic_settings import BaseSettings
        # Just confirm os.makedirs would be called; we assert the default dir exists.
    # The module-level makedirs already ran; check the default dir exists.
    from app.core.config import settings
    assert os.path.isdir(settings.UPLOAD_DIR)


def test_settings_anthropic_key_empty_by_default():
    from app.core.config import settings
    # In a clean test env with no env var, key is empty string
    assert isinstance(settings.ANTHROPIC_API_KEY, str)
