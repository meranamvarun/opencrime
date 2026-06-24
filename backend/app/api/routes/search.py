from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date
from decimal import Decimal
from app.core.database import get_db
from app.schemas.crime_record import SearchResult, CrimeRecordSummary
from app.services.search_service import full_text_search

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResult)
def search_records(
    q: str = Query(..., min_length=1, description="Search query"),
    crime_category: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    min_amount: Optional[Decimal] = Query(None),
    max_amount: Optional[Decimal] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Search crime records with full-text and faceted filtering."""
    total, records = full_text_search(
        db=db,
        query=q,
        crime_category=crime_category,
        state=state,
        district=district,
        date_from=date_from,
        date_to=date_to,
        min_amount=min_amount,
        max_amount=max_amount,
        page=page,
        page_size=page_size,
    )

    return SearchResult(
        total=total,
        page=page,
        page_size=page_size,
        results=[CrimeRecordSummary.model_validate(r) for r in records],
    )


@router.get("/suggestions")
def get_suggestions(
    q: str = Query(..., min_length=2),
    db: Session = Depends(get_db),
):
    """Return autocomplete suggestions for crime categories and locations."""
    from sqlalchemy import func
    from app.models.crime_record import CrimeRecord, ProcessingStatus

    categories = (
        db.query(CrimeRecord.crime_category)
        .filter(
            CrimeRecord.crime_category.ilike(f"%{q}%"),
            CrimeRecord.is_published == True,
        )
        .distinct()
        .limit(5)
        .all()
    )

    states = (
        db.query(CrimeRecord.state)
        .filter(
            CrimeRecord.state.ilike(f"%{q}%"),
            CrimeRecord.is_published == True,
        )
        .distinct()
        .limit(5)
        .all()
    )

    return {
        "categories": [c[0] for c in categories if c[0]],
        "states": [s[0] for s in states if s[0]],
    }
