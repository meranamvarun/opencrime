from sqlalchemy.orm import Session
from sqlalchemy import text, func, and_, cast, String
from sqlalchemy.dialects.postgresql import TSVECTOR
from typing import Optional, List
from datetime import date
from decimal import Decimal
from app.models.crime_record import CrimeRecord, ProcessingStatus


def full_text_search(
    db: Session,
    query: str,
    crime_category: Optional[str] = None,
    state: Optional[str] = None,
    district: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    min_amount: Optional[Decimal] = None,
    max_amount: Optional[Decimal] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[int, List[CrimeRecord]]:
    """Search crime records using PostgreSQL full-text search."""

    filters = [
        CrimeRecord.is_published == True,
        CrimeRecord.processing_status == ProcessingStatus.COMPLETED,
    ]

    # Full-text search using tsvector
    if query.strip():
        # Build tsquery from user input — sanitize and convert to prefix search
        sanitized = " & ".join(
            word.strip() + ":*"
            for word in query.split()
            if word.strip() and len(word.strip()) >= 2
        )
        ts_query = func.to_tsquery("english", sanitized)
        filters.append(
            CrimeRecord.search_vector.op("@@")(ts_query)
        )

    if crime_category:
        filters.append(CrimeRecord.crime_category.ilike(f"%{crime_category}%"))
    if state:
        filters.append(CrimeRecord.state.ilike(f"%{state}%"))
    if district:
        filters.append(CrimeRecord.district.ilike(f"%{district}%"))
    if date_from:
        filters.append(CrimeRecord.crime_date >= date_from)
    if date_to:
        filters.append(CrimeRecord.crime_date <= date_to)
    if min_amount is not None:
        filters.append(CrimeRecord.amount_involved >= min_amount)
    if max_amount is not None:
        filters.append(CrimeRecord.amount_involved <= max_amount)

    base_query = db.query(CrimeRecord).filter(and_(*filters))

    total = base_query.count()
    results = (
        base_query
        .order_by(CrimeRecord.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return total, results


def update_search_vector(db: Session, record: CrimeRecord):
    """Update the tsvector search index for a crime record."""
    text_parts = filter(None, [
        record.redacted_text or record.raw_text,
        record.crime_category,
        record.summary,
        record.police_station,
        record.district,
        record.state,
        record.modus_operandi,
        " ".join(record.keywords or []),
    ])
    combined_text = " ".join(text_parts)

    if combined_text.strip():
        db.execute(
            text(
                "UPDATE crime_records SET search_vector = to_tsvector('english', :txt) WHERE id = :id"
            ),
            {"txt": combined_text[:50000], "id": str(record.id)},
        )
        db.commit()
