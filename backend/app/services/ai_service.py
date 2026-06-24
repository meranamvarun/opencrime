import json
import logging
from typing import Optional
import anthropic
from app.core.config import settings

logger = logging.getLogger(__name__)

_client: Optional[anthropic.Anthropic] = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


EXTRACTION_SYSTEM_PROMPT = """You are a legal document analyst specializing in Indian crime records and FIRs (First Information Reports).
Extract structured information from the provided document text.
Always respond with valid JSON matching the exact schema requested.
If a field cannot be determined from the text, use null.
Be precise and extract only what is explicitly stated in the document."""

EXTRACTION_TOOL = {
    "name": "extract_crime_record",
    "description": "Extract structured information from a crime record or FIR document",
    "input_schema": {
        "type": "object",
        "properties": {
            "crime_category": {
                "type": "string",
                "description": "Category of crime (e.g., Cyber Fraud, Vehicle Theft, Robbery, Murder, Assault, Kidnapping, Drug Trafficking, Property Crime, Sexual Offence, Other)"
            },
            "fir_number": {
                "type": "string",
                "description": "FIR registration number"
            },
            "crime_date": {
                "type": "string",
                "description": "Date when crime occurred in YYYY-MM-DD format"
            },
            "registration_date": {
                "type": "string",
                "description": "Date when FIR was registered in YYYY-MM-DD format"
            },
            "police_station": {
                "type": "string",
                "description": "Name of the police station"
            },
            "district": {
                "type": "string",
                "description": "District where the crime occurred"
            },
            "state": {
                "type": "string",
                "description": "State where the crime occurred"
            },
            "legal_sections": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of legal sections invoked (e.g., IPC 420, BNS 318, IT Act 66C)"
            },
            "amount_involved": {
                "type": "number",
                "description": "Amount involved in the crime in INR (if applicable)"
            },
            "modus_operandi": {
                "type": "string",
                "description": "Method/manner in which the crime was committed (max 500 chars)"
            },
            "keywords": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Key terms describing the crime (5-15 keywords)"
            },
            "entities": {
                "type": "object",
                "description": "Non-PII entities: organizations, payment methods, vehicle types, etc.",
                "properties": {
                    "organizations": {"type": "array", "items": {"type": "string"}},
                    "payment_methods": {"type": "array", "items": {"type": "string"}},
                    "vehicle_types": {"type": "array", "items": {"type": "string"}},
                    "locations": {"type": "array", "items": {"type": "string"}}
                }
            }
        },
        "required": ["crime_category", "keywords"]
    }
}

REDACTION_SYSTEM_PROMPT = """You are a privacy protection specialist. Your task is to redact all personally identifiable information (PII) from crime documents while preserving the factual and investigative value of the text.

Redact (replace with [REDACTED]):
- Full names of victims, accused, witnesses
- Phone numbers and mobile numbers
- Physical addresses (house numbers, street names, flat numbers)
- Aadhaar numbers, PAN, passport, voter ID numbers
- Bank account numbers, credit/debit card numbers
- Email addresses
- Names of minors (replace with [MINOR])
- Names of sexual assault victims (replace with [VICTIM])

Preserve (do NOT redact):
- Crime categories and types
- Police station names
- District and state names
- Date and time information
- Legal sections and case numbers
- FIR numbers
- Amounts of money
- Vehicle types (but not registration numbers → redact those)
- General descriptions of modus operandi

Return ONLY the redacted text with no explanations."""


def extract_structured_data(text: str) -> dict:
    """Use Claude to extract structured crime record data from text."""
    if not settings.ANTHROPIC_API_KEY:
        logger.warning("No Anthropic API key configured, skipping AI extraction")
        return {}

    try:
        client = get_client()
        # Truncate text to avoid token limits
        truncated = text[:8000] if len(text) > 8000 else text

        response = client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=2048,
            system=EXTRACTION_SYSTEM_PROMPT,
            tools=[EXTRACTION_TOOL],
            tool_choice={"type": "tool", "name": "extract_crime_record"},
            messages=[
                {
                    "role": "user",
                    "content": f"Extract structured information from this crime document:\n\n{truncated}"
                }
            ]
        )

        for block in response.content:
            if block.type == "tool_use" and block.name == "extract_crime_record":
                return block.input

        return {}

    except Exception as e:
        logger.error(f"AI extraction failed: {e}")
        return {}


def redact_pii(text: str) -> str:
    """Use Claude to redact PII from document text."""
    if not settings.ANTHROPIC_API_KEY:
        logger.warning("No Anthropic API key, using regex-only redaction")
        return _regex_redact(text)

    try:
        client = get_client()
        # Process in chunks if text is long
        if len(text) > 6000:
            chunks = [text[i:i+6000] for i in range(0, len(text), 6000)]
            redacted_chunks = [_ai_redact_chunk(client, chunk) for chunk in chunks]
            return "\n".join(redacted_chunks)

        return _ai_redact_chunk(client, text)

    except Exception as e:
        logger.error(f"AI redaction failed, falling back to regex: {e}")
        return _regex_redact(text)


def _ai_redact_chunk(client: anthropic.Anthropic, text: str) -> str:
    response = client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=4096,
        system=REDACTION_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Redact all PII from this document text:\n\n{text}"
            }
        ]
    )
    return response.content[0].text


def generate_summary(text: str, extracted: dict) -> str:
    """Generate a human-readable summary of the crime record."""
    if not settings.ANTHROPIC_API_KEY:
        return _fallback_summary(extracted)

    try:
        client = get_client()
        context = json.dumps(extracted, indent=2, default=str)
        truncated_text = text[:3000] if len(text) > 3000 else text

        response = client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=512,
            messages=[
                {
                    "role": "user",
                    "content": f"""Generate a concise 2-3 sentence summary of this crime record for public awareness.
Focus on: what happened, where, when, and the legal context.
Do NOT include any personal names or identifying information.

Extracted data:
{context}

Document text (excerpt):
{truncated_text}

Write only the summary, no labels or headers."""
                }
            ]
        )
        return response.content[0].text.strip()

    except Exception as e:
        logger.error(f"Summary generation failed: {e}")
        return _fallback_summary(extracted)


def _fallback_summary(extracted: dict) -> str:
    parts = []
    if extracted.get("crime_category"):
        parts.append(f"A {extracted['crime_category']} case")
    if extracted.get("crime_date"):
        parts.append(f"occurred on {extracted['crime_date']}")
    if extracted.get("district") and extracted.get("state"):
        parts.append(f"in {extracted['district']}, {extracted['state']}")
    if extracted.get("police_station"):
        parts.append(f"registered at {extracted['police_station']}")
    if extracted.get("legal_sections"):
        sections = ", ".join(extracted["legal_sections"])
        parts.append(f"under sections {sections}")
    return ". ".join(parts) + "." if parts else "Crime record processed."


def _regex_redact(text: str) -> str:
    """Basic regex-based PII redaction as fallback."""
    import re

    # Phone numbers
    text = re.sub(r'\b[6-9]\d{9}\b', '[PHONE]', text)
    text = re.sub(r'\+91[-\s]?\d{10}', '[PHONE]', text)

    # Aadhaar numbers
    text = re.sub(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[AADHAAR]', text)

    # PAN
    text = re.sub(r'\b[A-Z]{5}\d{4}[A-Z]\b', '[PAN]', text)

    # Vehicle registration numbers
    text = re.sub(r'\b[A-Z]{2}\d{2}[A-Z]{1,2}\d{4}\b', '[VEH-REG]', text)

    # Email
    text = re.sub(r'\b[\w.+-]+@[\w-]+\.[a-z]{2,}\b', '[EMAIL]', text, flags=re.IGNORECASE)

    # Bank account numbers (10-18 digits)
    text = re.sub(r'\b\d{10,18}\b', '[ACCOUNT]', text)

    return text
