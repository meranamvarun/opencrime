import os
import uuid
import shutil
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.config import settings
from app.models.crime_record import Document, CrimeRecord, ProcessingStatus
from app.schemas.crime_record import DocumentOut, CrimeRecordOut, CrimeRecordSummary

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_TYPES = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/tiff": ".tiff",
}


@router.post("/upload", response_model=DocumentOut, status_code=202)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload a crime document (PDF or image) for processing."""
    content_type = file.content_type or ""
    if content_type not in ALLOWED_TYPES and not file.filename.lower().endswith(
        (".pdf", ".jpg", ".jpeg", ".png", ".tiff")
    ):
        raise HTTPException(status_code=400, detail="Unsupported file type. Use PDF or image.")

    # Size check
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    if size > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit")

    ext = Path(file.filename).suffix.lower() or ".pdf"
    saved_name = f"{uuid.uuid4()}{ext}"
    save_path = os.path.join(settings.UPLOAD_DIR, saved_name)

    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    doc = Document(
        filename=saved_name,
        original_filename=file.filename,
        file_path=save_path,
        file_type=ext.lstrip("."),
        file_size=size,
        status=ProcessingStatus.PENDING,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Kick off async processing
    background_tasks.add_task(_process_document_bg, str(doc.id))

    return doc


def _process_document_bg(document_id: str):
    """Background task: try Celery first, fall back to in-process."""
    try:
        from app.workers.processing import process_document
        process_document.delay(document_id)
    except Exception:
        # If Celery/Redis unavailable, process synchronously
        _process_sync(document_id)


def _process_sync(document_id: str):
    from app.core.database import SessionLocal
    from app.models.crime_record import CrimeRecord, SourceType
    from app.services import ocr_service, ai_service, search_service
    import logging
    logger = logging.getLogger(__name__)

    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == uuid.UUID(document_id)).first()
        if not doc:
            return
        doc.status = ProcessingStatus.PROCESSING
        db.commit()

        raw_text = ocr_service.extract_text_from_file(doc.file_path)
        extracted = ai_service.extract_structured_data(raw_text)
        redacted_text = ai_service.redact_pii(raw_text)
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

        for field in ("crime_date", "registration_date"):
            val = extracted.get(field)
            if val:
                try:
                    from datetime import datetime
                    setattr(record, field, datetime.strptime(val, "%Y-%m-%d").date())
                except Exception:
                    pass

        db.add(record)
        db.flush()
        doc.status = ProcessingStatus.COMPLETED
        doc.crime_record_id = record.id
        db.commit()
        search_service.update_search_vector(db, record)

    except Exception as e:
        logger.error(f"Sync processing failed: {e}", exc_info=True)
        try:
            doc = db.query(Document).filter(Document.id == uuid.UUID(document_id)).first()
            if doc:
                doc.status = ProcessingStatus.FAILED
                doc.error_message = str(e)[:500]
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: uuid.UUID, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.get("/{document_id}/record", response_model=CrimeRecordOut)
def get_document_record(document_id: uuid.UUID, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not doc.crime_record_id:
        raise HTTPException(status_code=404, detail="Record not yet processed")
    record = db.query(CrimeRecord).filter(CrimeRecord.id == doc.crime_record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Crime record not found")
    return record
