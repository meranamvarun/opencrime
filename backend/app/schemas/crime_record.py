from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import date, datetime
from decimal import Decimal
import uuid


class DocumentOut(BaseModel):
    id: uuid.UUID
    filename: str
    original_filename: str
    file_type: Optional[str]
    file_size: Optional[int]
    status: str
    error_message: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class CrimeRecordBase(BaseModel):
    source_url: Optional[str] = None
    source_type: Optional[str] = "fir"
    crime_category: Optional[str] = None
    crime_date: Optional[date] = None
    fir_number: Optional[str] = None
    police_station: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    legal_sections: Optional[List[str]] = []
    amount_involved: Optional[Decimal] = None
    modus_operandi: Optional[str] = None


class CrimeRecordCreate(CrimeRecordBase):
    raw_text: Optional[str] = None


class CrimeRecordOut(CrimeRecordBase):
    id: uuid.UUID
    summary: Optional[str] = None
    redacted_text: Optional[str] = None
    keywords: Optional[List[str]] = []
    entities: Optional[dict] = {}
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_published: bool
    processing_status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    documents: Optional[List[DocumentOut]] = []

    class Config:
        from_attributes = True


class CrimeRecordSummary(BaseModel):
    id: uuid.UUID
    crime_category: Optional[str]
    crime_date: Optional[date]
    fir_number: Optional[str]
    police_station: Optional[str]
    district: Optional[str]
    state: Optional[str]
    summary: Optional[str]
    keywords: Optional[List[str]] = []
    amount_involved: Optional[Decimal]
    processing_status: str
    created_at: datetime

    class Config:
        from_attributes = True


class SearchQuery(BaseModel):
    q: str = Field(..., min_length=1, description="Search query")
    crime_category: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class SearchResult(BaseModel):
    total: int
    page: int
    page_size: int
    results: List[CrimeRecordSummary]


class AnalyticsSummary(BaseModel):
    total_records: int
    by_category: List[dict]
    by_state: List[dict]
    by_month: List[dict]
    recent_count_30d: int
    total_amount_involved: Optional[Decimal]
