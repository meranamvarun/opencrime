"""Tests for app.services.ai_service — 100% branch coverage."""
import json
from unittest.mock import MagicMock, patch, call

import pytest

import app.services.ai_service as ai_module


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_global_client():
    """Reset the module-level _client singleton between tests."""
    original = ai_module._client
    ai_module._client = None
    yield
    ai_module._client = original


def _mock_anthropic_client():
    return MagicMock()


def _make_tool_use_block(data: dict):
    block = MagicMock()
    block.type = "tool_use"
    block.name = "extract_crime_record"
    block.input = data
    return block


def _make_text_block(text: str):
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


# ---------------------------------------------------------------------------
# get_client
# ---------------------------------------------------------------------------

def test_get_client_creates_instance_on_first_call():
    mock_client = MagicMock()
    with patch("app.services.ai_service.anthropic.Anthropic", return_value=mock_client) as MockAnthropic:
        result = ai_module.get_client()
    assert result is mock_client
    MockAnthropic.assert_called_once_with(api_key=ai_module.settings.ANTHROPIC_API_KEY)


def test_get_client_returns_same_instance_on_second_call():
    mock_client = MagicMock()
    with patch("app.services.ai_service.anthropic.Anthropic", return_value=mock_client) as MockAnthropic:
        r1 = ai_module.get_client()
        r2 = ai_module.get_client()
    assert r1 is r2
    MockAnthropic.assert_called_once()  # Only constructed once


# ---------------------------------------------------------------------------
# extract_structured_data
# ---------------------------------------------------------------------------

def test_extract_no_api_key_returns_empty():
    with patch.object(ai_module.settings, "ANTHROPIC_API_KEY", ""):
        result = ai_module.extract_structured_data("some text")
    assert result == {}


def test_extract_returns_tool_use_input():
    expected = {"crime_category": "Robbery", "keywords": ["robbery"]}
    mock_client = _mock_anthropic_client()
    mock_response = MagicMock()
    mock_response.content = [_make_tool_use_block(expected)]
    mock_client.messages.create.return_value = mock_response

    with patch.object(ai_module.settings, "ANTHROPIC_API_KEY", "test-key"), \
         patch("app.services.ai_service.get_client", return_value=mock_client):
        result = ai_module.extract_structured_data("test text")

    assert result == expected


def test_extract_truncates_long_text():
    mock_client = _mock_anthropic_client()
    mock_response = MagicMock()
    mock_response.content = [_make_tool_use_block({"crime_category": "X", "keywords": []})]
    mock_client.messages.create.return_value = mock_response

    long_text = "a" * 10_000

    with patch.object(ai_module.settings, "ANTHROPIC_API_KEY", "test-key"), \
         patch("app.services.ai_service.get_client", return_value=mock_client):
        ai_module.extract_structured_data(long_text)

    call_kwargs = mock_client.messages.create.call_args
    sent_content = call_kwargs[1]["messages"][0]["content"]
    assert len(sent_content) < 10_000


def test_extract_short_text_not_truncated():
    mock_client = _mock_anthropic_client()
    short_text = "short"
    mock_response = MagicMock()
    mock_response.content = [_make_tool_use_block({"crime_category": "X", "keywords": []})]
    mock_client.messages.create.return_value = mock_response

    with patch.object(ai_module.settings, "ANTHROPIC_API_KEY", "test-key"), \
         patch("app.services.ai_service.get_client", return_value=mock_client):
        ai_module.extract_structured_data(short_text)

    sent_content = mock_client.messages.create.call_args[1]["messages"][0]["content"]
    assert short_text in sent_content


def test_extract_returns_empty_when_no_tool_use_block():
    mock_client = _mock_anthropic_client()
    mock_response = MagicMock()
    # Content has only text blocks, no tool_use
    mock_response.content = [_make_text_block("some text")]
    mock_client.messages.create.return_value = mock_response

    with patch.object(ai_module.settings, "ANTHROPIC_API_KEY", "test-key"), \
         patch("app.services.ai_service.get_client", return_value=mock_client):
        result = ai_module.extract_structured_data("text")

    assert result == {}


def test_extract_ignores_tool_use_with_wrong_name():
    mock_client = _mock_anthropic_client()
    block = MagicMock()
    block.type = "tool_use"
    block.name = "other_tool"  # wrong name
    mock_response = MagicMock()
    mock_response.content = [block]
    mock_client.messages.create.return_value = mock_response

    with patch.object(ai_module.settings, "ANTHROPIC_API_KEY", "test-key"), \
         patch("app.services.ai_service.get_client", return_value=mock_client):
        result = ai_module.extract_structured_data("text")

    assert result == {}


def test_extract_returns_empty_on_api_exception():
    mock_client = _mock_anthropic_client()
    mock_client.messages.create.side_effect = Exception("API down")

    with patch.object(ai_module.settings, "ANTHROPIC_API_KEY", "test-key"), \
         patch("app.services.ai_service.get_client", return_value=mock_client):
        result = ai_module.extract_structured_data("text")

    assert result == {}


# ---------------------------------------------------------------------------
# redact_pii
# ---------------------------------------------------------------------------

def test_redact_pii_no_api_key_uses_regex():
    text = "Phone: 9876543210"
    with patch.object(ai_module.settings, "ANTHROPIC_API_KEY", ""):
        result = ai_module.redact_pii(text)
    assert "[PHONE]" in result


def test_redact_pii_short_text_single_chunk():
    mock_client = _mock_anthropic_client()
    mock_response = MagicMock()
    mock_response.content = [_make_text_block("Redacted text")]
    mock_client.messages.create.return_value = mock_response

    with patch.object(ai_module.settings, "ANTHROPIC_API_KEY", "test-key"), \
         patch("app.services.ai_service.get_client", return_value=mock_client):
        result = ai_module.redact_pii("short text")

    assert result == "Redacted text"
    mock_client.messages.create.assert_called_once()


def test_redact_pii_long_text_splits_into_chunks():
    """Text > 6000 chars should be split and results joined."""
    mock_client = _mock_anthropic_client()
    mock_response = MagicMock()
    mock_response.content = [_make_text_block("chunk")]
    mock_client.messages.create.return_value = mock_response

    long_text = "x" * 13_000  # Two chunks

    with patch.object(ai_module.settings, "ANTHROPIC_API_KEY", "test-key"), \
         patch("app.services.ai_service.get_client", return_value=mock_client):
        result = ai_module.redact_pii(long_text)

    assert mock_client.messages.create.call_count == 3  # ceil(13000/6000) = 3 calls
    assert result == "chunk\nchunk\nchunk"


def test_redact_pii_falls_back_to_regex_on_exception():
    mock_client = _mock_anthropic_client()
    mock_client.messages.create.side_effect = Exception("Network error")

    with patch.object(ai_module.settings, "ANTHROPIC_API_KEY", "test-key"), \
         patch("app.services.ai_service.get_client", return_value=mock_client):
        result = ai_module.redact_pii("Phone 9876543210")

    assert "[PHONE]" in result


# ---------------------------------------------------------------------------
# _ai_redact_chunk
# ---------------------------------------------------------------------------

def test_ai_redact_chunk_returns_text():
    mock_client = _mock_anthropic_client()
    mock_response = MagicMock()
    mock_response.content = [_make_text_block("Redacted chunk")]
    mock_client.messages.create.return_value = mock_response

    result = ai_module._ai_redact_chunk(mock_client, "original text")

    assert result == "Redacted chunk"


# ---------------------------------------------------------------------------
# generate_summary
# ---------------------------------------------------------------------------

def test_generate_summary_no_api_key_uses_fallback():
    extracted = {"crime_category": "Robbery"}
    with patch.object(ai_module.settings, "ANTHROPIC_API_KEY", ""):
        result = ai_module.generate_summary("text", extracted)
    assert "Robbery" in result


def test_generate_summary_returns_stripped_text():
    mock_client = _mock_anthropic_client()
    mock_response = MagicMock()
    mock_response.content = [_make_text_block("  Summary sentence.  ")]
    mock_client.messages.create.return_value = mock_response

    with patch.object(ai_module.settings, "ANTHROPIC_API_KEY", "test-key"), \
         patch("app.services.ai_service.get_client", return_value=mock_client):
        result = ai_module.generate_summary("text", {})

    assert result == "Summary sentence."


def test_generate_summary_truncates_long_text():
    mock_client = _mock_anthropic_client()
    mock_response = MagicMock()
    mock_response.content = [_make_text_block("Summary")]
    mock_client.messages.create.return_value = mock_response

    long_text = "a" * 5_000

    with patch.object(ai_module.settings, "ANTHROPIC_API_KEY", "test-key"), \
         patch("app.services.ai_service.get_client", return_value=mock_client):
        ai_module.generate_summary(long_text, {})

    sent = mock_client.messages.create.call_args[1]["messages"][0]["content"]
    # truncated_text should be at most 3000 chars
    assert long_text[3001:] not in sent


def test_generate_summary_falls_back_on_exception():
    mock_client = _mock_anthropic_client()
    mock_client.messages.create.side_effect = Exception("API error")

    extracted = {"crime_category": "Murder"}
    with patch.object(ai_module.settings, "ANTHROPIC_API_KEY", "test-key"), \
         patch("app.services.ai_service.get_client", return_value=mock_client):
        result = ai_module.generate_summary("text", extracted)

    assert "Murder" in result


# ---------------------------------------------------------------------------
# _fallback_summary — all branch combinations
# ---------------------------------------------------------------------------

def test_fallback_summary_empty_dict():
    result = ai_module._fallback_summary({})
    assert result == "Crime record processed."


def test_fallback_summary_only_crime_category():
    result = ai_module._fallback_summary({"crime_category": "Robbery"})
    assert result == "A Robbery case."


def test_fallback_summary_only_crime_date():
    result = ai_module._fallback_summary({"crime_date": "2024-03-15"})
    assert result == "occurred on 2024-03-15."


def test_fallback_summary_district_without_state_omits_location():
    # district AND state both required for location part
    result = ai_module._fallback_summary({"district": "Mumbai", "state": None})
    assert "in Mumbai" not in result


def test_fallback_summary_state_without_district_omits_location():
    result = ai_module._fallback_summary({"district": None, "state": "Maharashtra"})
    assert "Maharashtra" not in result


def test_fallback_summary_district_and_state():
    result = ai_module._fallback_summary({"district": "Mumbai", "state": "Maharashtra"})
    assert "in Mumbai, Maharashtra" in result


def test_fallback_summary_police_station():
    result = ai_module._fallback_summary({"police_station": "Andheri PS"})
    assert "registered at Andheri PS" in result


def test_fallback_summary_legal_sections():
    result = ai_module._fallback_summary({"legal_sections": ["IPC 420", "IPC 406"]})
    assert "under sections IPC 420, IPC 406" in result


def test_fallback_summary_all_fields():
    extracted = {
        "crime_category": "Cyber Fraud",
        "crime_date": "2024-01-15",
        "district": "Bengaluru",
        "state": "Karnataka",
        "police_station": "Cyber PS",
        "legal_sections": ["IT Act 66C"],
    }
    result = ai_module._fallback_summary(extracted)
    assert result.endswith(".")
    assert "Cyber Fraud" in result
    assert "2024-01-15" in result
    assert "Bengaluru, Karnataka" in result
    assert "Cyber PS" in result
    assert "IT Act 66C" in result


# ---------------------------------------------------------------------------
# _regex_redact — every pattern
# ---------------------------------------------------------------------------

def test_regex_redact_phone_10digit():
    result = ai_module._regex_redact("Call 9876543210 now")
    assert "[PHONE]" in result
    assert "9876543210" not in result


def test_regex_redact_phone_plus91():
    result = ai_module._regex_redact("Contact +91 9876543210")
    assert "[PHONE]" in result


def test_regex_redact_phone_plus91_hyphen():
    result = ai_module._regex_redact("Call +91-9876543210")
    assert "[PHONE]" in result


def test_regex_redact_aadhaar():
    result = ai_module._regex_redact("Aadhaar: 1234 5678 9012")
    assert "[AADHAAR]" in result
    assert "1234 5678 9012" not in result


def test_regex_redact_pan():
    result = ai_module._regex_redact("PAN: ABCDE1234F")
    assert "[PAN]" in result
    assert "ABCDE1234F" not in result


def test_regex_redact_vehicle_reg():
    result = ai_module._regex_redact("Vehicle MH12AB1234 stolen")
    assert "[VEH-REG]" in result
    assert "MH12AB1234" not in result


def test_regex_redact_email():
    result = ai_module._regex_redact("Email user@example.com sent")
    assert "[EMAIL]" in result
    assert "user@example.com" not in result


def test_regex_redact_bank_account():
    # 14-digit number won't be caught by earlier patterns
    result = ai_module._regex_redact("Account 12345678901234 debited")
    assert "[ACCOUNT]" in result
    assert "12345678901234" not in result


def test_regex_redact_clean_text_unchanged():
    clean = "Crime occurred in Mumbai on 2024-01-15."
    result = ai_module._regex_redact(clean)
    assert result == clean
