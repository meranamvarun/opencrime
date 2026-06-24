from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import Optional
from datetime import date, timedelta, datetime
from app.core.database import get_db
from app.models.crime_record import CrimeRecord, ProcessingStatus
from app.schemas.crime_record import AnalyticsSummary

router = APIRouter(prefix="/analytics", tags=["analytics"])

PUBLISHED = [
    CrimeRecord.is_published == True,
    CrimeRecord.processing_status == ProcessingStatus.COMPLETED,
]


@router.get("/summary", response_model=AnalyticsSummary)
def get_analytics_summary(
    state: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """High-level statistics for the dashboard."""
    filters = list(PUBLISHED)
    if state:
        filters.append(CrimeRecord.state.ilike(f"%{state}%"))

    total = db.query(func.count(CrimeRecord.id)).filter(and_(*filters)).scalar() or 0

    by_category = (
        db.query(CrimeRecord.crime_category, func.count(CrimeRecord.id).label("count"))
        .filter(and_(*filters), CrimeRecord.crime_category.isnot(None))
        .group_by(CrimeRecord.crime_category)
        .order_by(func.count(CrimeRecord.id).desc())
        .limit(10)
        .all()
    )

    by_state = (
        db.query(CrimeRecord.state, func.count(CrimeRecord.id).label("count"))
        .filter(and_(*filters), CrimeRecord.state.isnot(None))
        .group_by(CrimeRecord.state)
        .order_by(func.count(CrimeRecord.id).desc())
        .limit(10)
        .all()
    )

    # Monthly trend (last 12 months)
    twelve_months_ago = datetime.utcnow().date() - timedelta(days=365)
    by_month = (
        db.query(
            func.to_char(CrimeRecord.crime_date, "YYYY-MM").label("month"),
            func.count(CrimeRecord.id).label("count"),
        )
        .filter(
            and_(*filters),
            CrimeRecord.crime_date >= twelve_months_ago,
            CrimeRecord.crime_date.isnot(None),
        )
        .group_by(func.to_char(CrimeRecord.crime_date, "YYYY-MM"))
        .order_by(func.to_char(CrimeRecord.crime_date, "YYYY-MM"))
        .all()
    )

    thirty_days_ago = datetime.utcnow().date() - timedelta(days=30)
    recent = (
        db.query(func.count(CrimeRecord.id))
        .filter(and_(*filters), CrimeRecord.created_at >= thirty_days_ago)
        .scalar()
        or 0
    )

    total_amount = (
        db.query(func.sum(CrimeRecord.amount_involved))
        .filter(and_(*filters))
        .scalar()
    )

    return AnalyticsSummary(
        total_records=total,
        by_category=[{"category": r[0], "count": r[1]} for r in by_category],
        by_state=[{"state": r[0], "count": r[1]} for r in by_state],
        by_month=[{"month": r[0], "count": r[1]} for r in by_month],
        recent_count_30d=recent,
        total_amount_involved=total_amount,
    )


@router.get("/records")
def list_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    state: Optional[str] = Query(None),
    crime_category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Paginated list of published crime records."""
    from app.schemas.crime_record import CrimeRecordSummary

    filters = list(PUBLISHED)
    if state:
        filters.append(CrimeRecord.state.ilike(f"%{state}%"))
    if crime_category:
        filters.append(CrimeRecord.crime_category.ilike(f"%{crime_category}%"))

    total = db.query(func.count(CrimeRecord.id)).filter(and_(*filters)).scalar() or 0
    records = (
        db.query(CrimeRecord)
        .filter(and_(*filters))
        .order_by(CrimeRecord.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "results": [CrimeRecordSummary.model_validate(r) for r in records],
    }


@router.get("/records/{record_id}")
def get_record(record_id: str, db: Session = Depends(get_db)):
    """Get a single published crime record by ID."""
    import uuid
    from fastapi import HTTPException
    from app.schemas.crime_record import CrimeRecordOut

    try:
        rid = uuid.UUID(record_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid record ID")

    record = (
        db.query(CrimeRecord)
        .filter(CrimeRecord.id == rid, CrimeRecord.is_published == True)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return CrimeRecordOut.model_validate(record)


@router.get("/map")
def get_map_data(
    state: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Return crime records with geo coordinates for map visualization."""
    filters = list(PUBLISHED) + [
        CrimeRecord.latitude.isnot(None),
        CrimeRecord.longitude.isnot(None),
    ]
    if state:
        filters.append(CrimeRecord.state.ilike(f"%{state}%"))

    records = (
        db.query(
            CrimeRecord.id,
            CrimeRecord.crime_category,
            CrimeRecord.district,
            CrimeRecord.state,
            CrimeRecord.latitude,
            CrimeRecord.longitude,
            CrimeRecord.crime_date,
        )
        .filter(and_(*filters))
        .limit(1000)
        .all()
    )

    return {
        "points": [
            {
                "id": str(r[0]),
                "category": r[1],
                "district": r[2],
                "state": r[3],
                "lat": r[4],
                "lng": r[5],
                "date": str(r[6]) if r[6] else None,
            }
            for r in records
        ]
    }
