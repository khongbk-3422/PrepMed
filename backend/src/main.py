import json
import re
from datetime import datetime

import numpy as np
from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlmodel import Session, select

from src.database import get_session, init_db
from src.models import Consultation, ConsultationStatus, MedicalTemplate, User
from src.schemas import TemplateCreate, UserCreate
from src.services import ai_service
from src.services.gemini_service import get_gemini_models
from src.services.ollama_service import get_downloaded_models

app = FastAPI(title="PrepMed Core Engine", version="2.5")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------
# REQUEST SCHEMAS
# -------------------------

class ProcessSessionRequest(BaseModel):
    patient_id: int = 101
    user_id: int = 1
    template_id: int = 1
    model_name: str = "llama3.1"
    raw_text: str = ""
    transcript: str = ""


# -------------------------
# HELPERS
# -------------------------

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

        if hasattr(obj, "__table__"):
            return {
                column.name: getattr(obj, column.name)
                for column in obj.__table__.columns
            }

        return super().default(obj)


def normalize_required_items(required_items):
    """Clean template fields so symptoms: becomes symptoms."""

    if isinstance(required_items, str):
        try:
            parsed_items = json.loads(required_items)
        except Exception:
            parsed_items = [required_items]
    else:
        parsed_items = required_items or []

    clean_items = []

    for item in parsed_items:
        parts = re.split(r"[,\n]", str(item))

        for part in parts:
            clean_part = part.strip().rstrip(":").strip()

            if clean_part and clean_part not in clean_items:
                clean_items.append(clean_part)

    return clean_items


def safe_text(value):
    if value is None:
        return "-"

    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)

    return str(value)


def consultation_to_dict(consultation):
    row_dict = {
        column.name: getattr(consultation, column.name)
        for column in consultation.__table__.columns
    }

    embedding = row_dict.get("embedding")

    if isinstance(embedding, np.ndarray):
        row_dict["embedding"] = embedding.tolist()
    elif hasattr(embedding, "tolist"):
        row_dict["embedding"] = embedding.tolist()

    return row_dict


@app.on_event("startup")
def on_startup():
    init_db()


# -------------------------
# MODEL ROUTE
# -------------------------

@app.get("/models")
async def list_models():
    local_models = get_downloaded_models()
    gemini_models = get_gemini_models()

    return {
        "gemini_models": gemini_models,
        "ollama_models": local_models,
    }


# -------------------------
# CONSULTATION SESSION ROUTES
# -------------------------

@app.get("/api/sessions")
def list_all_consultation_sessions(db: Session = Depends(get_session)):
    statement = select(Consultation).order_by(Consultation.created_at.desc())
    records = db.exec(statement).all()

    return [consultation_to_dict(record) for record in records]


@app.get("/api/sessions/{consultation_id}")
def fetch_consultation_historical_record(
    consultation_id: int,
    db: Session = Depends(get_session),
):
    consultation = db.get(Consultation, consultation_id)

    if not consultation:
        raise HTTPException(
            status_code=404,
            detail="Consultation data profile absent",
        )

    return consultation


@app.post("/api/sessions/process")
async def register_and_process_voice_session(
    payload: ProcessSessionRequest,
    db: Session = Depends(get_session),
):
    """Process transcript using selected model and template."""

    # 1. Get transcript from JSON body
    raw_transcript = (payload.transcript or payload.raw_text).strip()

    if not raw_transcript:
        raise HTTPException(
            status_code=400,
            detail="Transcript cannot be empty",
        )

    if len(raw_transcript.split()) < 10:
        raise HTTPException(
            status_code=400,
            detail="Transcript is too short. Please record or enter more details.",
        )

    # 2. Check user
    user = db.get(User, payload.user_id)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    # 3. Check template
    template = db.get(MedicalTemplate, payload.template_id)

    if not template:
        raise HTTPException(
            status_code=404,
            detail="Selected layout template missing",
        )

    # 4. Clean required template fields
    required_items = normalize_required_items(template.required_items)

    # 5. Send transcript to AI
    try:
        ai_raw_output = ai_service.process_clinical_audio(
            db=db,
            raw_text=raw_transcript,
            required_keys=required_items,
            d_desc=template.default_description or "-",
            d_med=template.default_medicine or "-",
            model_name=payload.model_name,
        )
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Inference pipeline failed: {str(error)}",
        ) from error

    # 6. Separate description and medicine from the AI result
    extracted_desc = safe_text(ai_raw_output.pop("description", "-"))
    extracted_med = safe_text(ai_raw_output.pop("medicine", "-"))

    # 7. Save consultation as Draft
    consultation = Consultation(
        patient_id=payload.patient_id,
        template_id=payload.template_id,
        status=ConsultationStatus.DRAFT,
        recorded_by_user_id=payload.user_id,
        raw_transcript=raw_transcript,
        extracted_structured_data=ai_raw_output,
        extracted_description=extracted_desc,
        extracted_medicine=extracted_med,
        embedding=None,
    )

    db.add(consultation)
    db.commit()
    db.refresh(consultation)

    # 8. Return saved consultation back to frontend
    json_str = json.dumps(consultation, cls=SafeJSONEncoder)

    return Response(
        content=json_str,
        media_type="application/json",
    )

@app.post("/api/sessions/{consultation_id}/review")
def review_and_modify_consultation_data(
    consultation_id: int,
    payload: dict,
    db: Session = Depends(get_session),
):
    consultation = db.get(Consultation, consultation_id)

    if not consultation:
        raise HTTPException(
            status_code=404,
            detail="Target consultation session missing",
        )

    consultation.extracted_structured_data = payload.get(
        "extracted_structured_data",
        {},
    )
    consultation.extracted_description = payload.get(
        "extracted_description",
        "-",
    )
    consultation.extracted_medicine = payload.get(
        "extracted_medicine",
        "-",
    )

    new_status = payload.get("status", "Pending Review")

    if new_status == "Draft":
        consultation.status = ConsultationStatus.DRAFT
    elif new_status == "Confirmed":
        consultation.status = ConsultationStatus.CONFIRMED
        consultation.embedding = None
    else:
        consultation.status = ConsultationStatus.PENDING_REVIEW

    consultation.reviewed_by_user_id = payload.get("user_id")
    consultation.updated_at = datetime.now()

    db.add(consultation)
    db.commit()
    db.refresh(consultation)

    json_str = json.dumps(
        {
            "status": "Updated",
            "current_state": consultation.status,
        },
        cls=SafeJSONEncoder,
    )

    return Response(content=json_str, media_type="application/json")


# -------------------------
# USER ROUTES
# -------------------------

@app.get("/api/users", response_model=list[User])
def list_system_users(db: Session = Depends(get_session)):
    return db.exec(select(User)).all()


@app.post("/api/users", response_model=User)
def create_user(payload: UserCreate, db: Session = Depends(get_session)):
    existing_user = db.exec(
        select(User).where(User.username == payload.username),
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


# -------------------------
# TEMPLATE ROUTES
# -------------------------

@app.get("/api/templates", response_model=list[MedicalTemplate])
def list_available_templates(db: Session = Depends(get_session)):
    return db.exec(select(MedicalTemplate)).all()


@app.post("/api/templates", response_model=MedicalTemplate)
def create_template(payload: TemplateCreate, db: Session = Depends(get_session)):
    user = db.get(User, payload.user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    clean_required_items = normalize_required_items(payload.required_items)

    template = MedicalTemplate(
        title=payload.title,
        required_items=clean_required_items,
        default_description=payload.default_description,
        default_medicine=payload.default_medicine,
        created_by_user_id=payload.user_id,
    )

    db.add(template)
    db.commit()
    db.refresh(template)

    return template