import logging
import uuid
from celery import Celery
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.crime_record import Document, CrimeRecord, ProcessingStatus, SourceType
from app.services import ocr_service, ai_service, search_service
from datetime import date

logger = logging.getLogger(__name__)

celery_app = Celery(
    "opencrime",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def process_document(self, document_id: str):
    """Process an uploaded document: OCR → AI extraction → PII redaction → store."""
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == uuid.UUID(document_id)).first()
        if not doc:
            logger.error(f"Document {document_id} not found")
            return

        doc.status = ProcessingStatus.PROCESSING
        db.commit()

        logger.info(f"Starting OCR for document {document_id}")
        raw_text = ocr_service.extract_text_from_file(doc.file_path)

        logger.info(f"Running AI extraction for document {document_id}")
        extracted = ai_service.extract_structured_data(raw_text)

        logger.info(f"Redacting PII for document {document_id}")
        redacted_text = ai_service.redact_pii(raw_text)

        logger.info(f"Generating summary for document {document_id}")
        summary = ai_service.generate_summary(redacted_text, extracted)

        record = CrimeRecord(
            source_type=SourceType.FIR,
            raw_text=raw_text,
            redacted_text=redacted_text,
            summary=summary,
            crime_category=extracted.get("crime_category"),
            fir_number=extracted.get("fir_number"),
            police_station=extracted.get("police_station"),
            district=extracted.get("district"),
            state=extracted.get("state"),
            legal_sections=extracted.get("legal_sections", []),
            amount_involved=extracted.get("amount_involved"),
            modus_operandi=extracted.get("modus_operandi"),
            keywords=extracted.get("keywords", []),
            entities=extracted.get("entities", {}),
            processing_status=ProcessingStatus.COMPLETED,
            is_published=True,
        )

        # Parse dates safely
        for field in ("crime_date", "registration_date"):
            val = extracted.get(field)
            if val:
                try:
                    from datetime import datetime
                    setattr(record, field, datetime.strptime(val, "%Y-%m-%d").date())
                except (ValueError, TypeError):
                    pass

        db.add(record)
        db.flush()

        doc.status = ProcessingStatus.COMPLETED
        doc.crime_record_id = record.id
        db.commit()

        # Update full-text search vector
        search_service.update_search_vector(db, record)

        logger.info(f"Document {document_id} processed → record {record.id}")

    except Exception as exc:
        logger.error(f"Document processing failed: {exc}", exc_info=True)
        try:
            doc = db.query(Document).filter(Document.id == uuid.UUID(document_id)).first()
            if doc:
                doc.status = ProcessingStatus.FAILED
                doc.error_message = str(exc)[:500]
                db.commit()
        except Exception:
            pass
        raise self.retry(exc=exc)
    finally:
        db.close()
