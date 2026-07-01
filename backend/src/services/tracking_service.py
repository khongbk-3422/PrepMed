from sqlmodel import Session
from src.models import AILearningLog, Consultation


def check_and_log_deviations(
    db: Session,
    consultation: Consultation,
    corrected_illness: str,
    corrected_medicine: str,
) -> None:
    has_illness_gap = consultation.extracted_illness != corrected_illness
    has_med_gap = consultation.extracted_medicine != corrected_medicine

    if has_illness_gap or has_med_gap:
        learning_entry = AILearningLog(
            original_transcript=consultation.raw_transcript or "",
            ai_extracted_illness=consultation.extracted_illness or "",
            ai_extracted_medicine=consultation.extracted_medicine or "",
            user_corrected_illness=corrected_illness,
            user_corrected_medicine=corrected_medicine,
        )
        db.add(learning_entry)
        db.commit()
