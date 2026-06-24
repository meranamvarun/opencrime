import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, DateTime, Date, Numeric,
    Enum, Float, JSON, ForeignKey, Boolean, Integer
)
from sqlalchemy.dialects.postgresql import UUID, TSVECTOR
from sqlalchemy.orm import relationship
from sqlalchemy import event
from app.core.database import Base
import enum


class ProcessingStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class SourceType(str, enum.Enum):
    FIR = "fir"
    NOTICE = "notice"
    REPORT = "report"
    OTHER = "other"


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(500), nullable=False)
    original_filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_type = Column(String(50))
    file_size = Column(Integer)
    status = Column(
        Enum(ProcessingStatus, name="processing_status"),
        default=ProcessingStatus.PENDING,
        nullable=False,
    )
    error_message = Column(Text)
    crime_record_id = Column(UUID(as_uuid=True), ForeignKey("crime_records.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    crime_record = relationship("CrimeRecord", back_populates="documents")


class CrimeRecord(Base):
    __tablename__ = "crime_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_url = Column(String(2000))
    source_type = Column(Enum(SourceType, name="source_type"), default=SourceType.FIR)

    raw_text = Column(Text)
    redacted_text = Column(Text)
    summary = Column(Text)

    crime_category = Column(String(200))
    crime_date = Column(Date)
    registration_date = Column(Date)
    fir_number = Column(String(100))

    police_station = Column(String(300))
    district = Column(String(200))
    state = Column(String(200))
    latitude = Column(Float)
    longitude = Column(Float)

    legal_sections = Column(JSON, default=list)
    amount_involved = Column(Numeric(20, 2))
    modus_operandi = Column(Text)
    keywords = Column(JSON, default=list)
    entities = Column(JSON, default=dict)

    # Full-text search vector (populated by trigger or service)
    search_vector = Column(TSVECTOR)

    is_published = Column(Boolean, default=False)
    processing_status = Column(
        Enum(ProcessingStatus, name="processing_status_record"),
        default=ProcessingStatus.PENDING,
    )

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    documents = relationship("Document", back_populates="crime_record")
