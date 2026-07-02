from typing import List, Dict, Optional
from pydantic import BaseModel
from src.models import UserRole

class UserCreate(BaseModel):
    username: str
    full_name: str
    role: UserRole

class TemplateCreate(BaseModel):
    title: str
    required_items: List[str]
    default_description: Optional[str] = "-"
    default_medicine: Optional[str] = "-"
    user_id: int  # ID of the doctor/nurse saving this template

class ConsultationUploadRequest(BaseModel):
    patient_id: int
    user_id: int  # ID of the person executing the recording
    template_id: int

class ConsultationAdjustmentRequest(BaseModel):
    user_id: int  # ID of the doctor/nurse reviewing the results
    extracted_structured_data: Dict[str, str]
    extracted_description: str
    extracted_medicine: str
    mark_confirmed: bool = False

#add patient create schema
class PatientCreate(BaseModel):
    full_name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    current_sickness: Optional[str] = None
    current_medications: Optional[str] = None