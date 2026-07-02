from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict, Any
from sqlmodel import Field, SQLModel
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, JSON as SIGN_JSON

class UserRole(str, Enum):
    DOCTOR = "doctor"
    NURSE = "nurse"

class ConsultationStatus(str, Enum):
    DRAFT = "Draft"
    PENDING_REVIEW = "Pending Review"
    CONFIRMED = "Confirmed"

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    full_name: str
    role: UserRole = Field(default=UserRole.DOCTOR)
    is_active: bool = True

class MedicalTemplate(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    required_items: List[str] = Field(default=[], sa_column=Column(SIGN_JSON))
    default_description: Optional[str] = "-"
    default_medicine: Optional[str] = "-"
    created_by_user_id: int

class Consultation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    patient_id: int

    template_id: Optional[int] = None
    status: ConsultationStatus = Field(default=ConsultationStatus.DRAFT)

    recorded_by_user_id: int
    reviewed_by_user_id: Optional[int] = None

    raw_transcript: Optional[str] = None
    extracted_structured_data: Dict[str, Any] = Field(default={}, sa_column=Column(SIGN_JSON))
    extracted_description: str = "-"
    extracted_medicine: str = "-"

    embedding: Optional[List[float]] = Field(default=None, sa_column=Column(Vector(768)))

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None
