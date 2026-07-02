import json  # 1. FIXED: Moved to the very top to satisfy Ruff E402
from fastapi import Depends, FastAPI, HTTPException, Response  
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

from sqlmodel import Session, select
import numpy as np

from src.database import get_session, init_db
from src.models import Consultation, ConsultationStatus, MedicalTemplate, User, Patient
from src.schemas import PatientCreate, UserCreate, TemplateCreate

from src.services import ai_service
from src.services.gemini_service import get_gemini_models
from src.services.ollama_service import get_downloaded_models

app = FastAPI(title="PrepMed Core Engine", version="2.5")

# Open global CORS permissions so your frontend container (port 3000) can fetch data safely
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SafeJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if hasattr(obj, "tolist"):
            return obj.tolist()
        if isinstance(obj, bytes):
            return obj.decode("utf-8")
        if hasattr(obj, "__dict__"):
            return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
        return super().default(obj)
    
@app.on_event("startup")
def on_startup():
    init_db()

@app.get("/models")
async def list_models():
    local_models = get_downloaded_models()
    gemini_models = get_gemini_models()

    return {"gemini_models": gemini_models, "ollama_models": local_models}

# --- FRONTEND HISTORY TABLE DIRECT ENDPOINT ---
@app.get("/api/sessions")
def list_all_consultation_sessions(db: Session = Depends(get_session)):
    """Fetches every consultation record and strips out raw NumPy attributes."""
    statement = select(Consultation).order_by(Consultation.created_at.desc())
    records = db.exec(statement).all()
    
    clean_records = []
    for item in records:
        # Convert the consultation row instance cleanly into a standard dictionary
        # bypasses pydantic database conversion lock conflicts entirely
        row_dict = {c.name: getattr(item, c.name) for c in item.__table__.columns}
        
        # Intercept the embedding property row specifically
        emb = row_dict.get("embedding")
        if isinstance(emb, np.ndarray):
            row_dict["embedding"] = emb.tolist()
        elif hasattr(emb, "tolist"):
            row_dict["embedding"] = emb.tolist()
            
        clean_records.append(row_dict)
        
    return clean_records


# --- GENERAL USER PATH ROUTERS ---
@app.get("/api/users", response_model=list[User])
def list_system_users(db: Session = Depends(get_session)):
    return db.exec(select(User)).all()

@app.post("/api/users", response_model=User)
def create_user(payload: UserCreate, db: Session = Depends(get_session)):
    existing_user = db.exec(
        select(User).where(User.username == payload.username)
    ).first()

    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    user = User(
        username=payload.username,
        full_name=payload.full_name,
        role=payload.role,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user

# --- GENERAL TEMPLATE PATH ROUTERS ---

@app.get("/api/templates", response_model=list[MedicalTemplate])
def list_available_templates(db: Session = Depends(get_session)):
    return db.exec(select(MedicalTemplate)).all()

@app.post("/api/templates", response_model=MedicalTemplate)
def create_template(payload: TemplateCreate, db: Session = Depends(get_session)):
    user = db.get(User, payload.user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    template = MedicalTemplate(
        title=payload.title,
        required_items=payload.required_items,
        default_description=payload.default_description,
        default_medicine=payload.default_medicine,
        created_by_user_id=payload.user_id,
    )

    db.add(template)
    db.commit()
    db.refresh(template)

    return template


# --- MEDICAL RECORDING VOICE PROCESSING API LOOP ---
@app.post("/api/sessions/process")
async def register_and_process_voice_session(
    patient_id: int = 101,
    user_id: int = 1,
    template_id: int = 1,
    model_name: str = "llama3.1",
    transcript: str = "",
    db: Session = Depends(get_session)
):
    """Processes transcript text using the user's chosen text model."""

    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    template = db.get(MedicalTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Selected layout template missing")

    raw_transcript = transcript.strip()

    if not raw_transcript:
        raise HTTPException(status_code=400, detail="Transcript cannot be empty")

    if len(raw_transcript.split()) < 10:
        raise HTTPException(
            status_code=400,
            detail="Transcript is too short. Please record or enter more details.",
        )

    items_list = template.required_items
    if isinstance(items_list, str):
        try:
            items_list = json.loads(items_list)
        except Exception:
            items_list = [items_list]

    ai_raw_output = ai_service.process_clinical_audio(
        db=db,
        raw_text=raw_transcript,
        required_keys=list(items_list),
        d_desc=template.default_description or "-",
        d_med=template.default_medicine or "-",
        model_name=model_name,
    )

    extracted_desc = ai_raw_output.pop("description", "-")
    extracted_med = ai_raw_output.pop("medicine", "-")

    consultation = Consultation(
        patient_id=patient_id,
        template_id=template_id,
        status=ConsultationStatus.PENDING_REVIEW,
        recorded_by_user_id=user_id,
        raw_transcript=raw_transcript,
        extracted_structured_data=ai_raw_output,
        extracted_description=extracted_desc,
        extracted_medicine=extracted_med,
        embedding=None,
    )

    db.add(consultation)
    db.commit()
    db.refresh(consultation)

    json_str = json.dumps(consultation, cls=SafeJSONEncoder)
    return Response(content=json_str, media_type="application/json")

@app.post("/api/sessions/{consultation_id}/review")
def review_and_modify_consultation_data(
    consultation_id: int, payload: dict, db: Session = Depends(get_session)
):
    """Saves edits from doctors or nurses and updates verification status flags."""
    consultation = db.get(Consultation, consultation_id)
    if not consultation:
        raise HTTPException(
            status_code=404, detail="Target consultation session missing"
        )

    consultation.extracted_structured_data = payload.get(
        "extracted_structured_data", {}
    )
    consultation.extracted_description = payload.get("extracted_description", "-")
    consultation.extracted_medicine = payload.get("extracted_medicine", "-")

    if payload.get("mark_confirmed", False):
        consultation.status = ConsultationStatus.CONFIRMED
        # ⭐ FIXED: Removed the ai_service.generate_text_embedding call completely!
        consultation.embedding = None 
    else:
        consultation.status = ConsultationStatus.PENDING_REVIEW

    db.add(consultation)
    db.commit()
    
    json_str = json.dumps(
        {"status": "Updated", "current_state": consultation.status}, 
        cls=SafeJSONEncoder
    )
    return Response(content=json_str, media_type="application/json")

@app.get("/api/sessions/{consultation_id}")
def fetch_consultation_historical_record(
    consultation_id: int, db: Session = Depends(get_session)
):
    consultation = db.get(Consultation, consultation_id)
    if not consultation:
        raise HTTPException(
            status_code=404, detail="Consultation data profile absent"
        )
    return consultation

# --- GENERAL PATIENT PATH ROUTERS ---
@app.get("/api/patients", response_model=list[Patient])
def list_patients(db: Session = Depends(get_session)):
    return db.exec(select(Patient)).all()

@app.post("/api/patients", response_model=Patient)
def create_patient(payload: PatientCreate, db: Session = Depends(get_session)):
    patient = Patient(
        full_name=payload.full_name,
        age=payload.age,
        gender=payload.gender,
        current_sickness=payload.current_sickness,
    )

    db.add(patient)
    db.commit()
    db.refresh(patient)

    return patient

@app.get("/api/patients/{patient_id}", response_model=Patient)
def get_patient(patient_id: int, db: Session = Depends(get_session)):
    patient = db.get(Patient, patient_id)

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    return patient