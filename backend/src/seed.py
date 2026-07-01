import os
from sqlmodel import Session, create_engine, select
# Added database module init_db import
from database import init_db
from models import User, UserRole, Consultation, ConsultationStatus

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://prepmed:predmed12345@postgres-db:5432/prepmed"
)

engine = create_engine(DATABASE_URL)


def seed_system_users_and_patients():
    # 1. Force table creations to instantiate missing tables cleanly
    print("⏳ Running database table schema initializations...")
    init_db()

    print("🚀 Seeding User roles and baseline testing channels...")
    with Session(engine) as session:
        if session.exec(select(User)).first():
            print("✨ Accounts are already configured. Skipping seed sequence.")
            return

        doc = User(username="dr_ahmad", full_name="Dr. Ahmad Razak", role=UserRole.DOCTOR)
        nurse = User(username="nurse_sarah", full_name="Nurse Sarah Connor", role=UserRole.NURSE)
        
        session.add(doc)
        session.add(nurse)
        session.commit()
        session.refresh(doc)
        
        initial_case = Consultation(
            patient_id=101,
            recorded_by_user_id=doc.id,
            status=ConsultationStatus.CONFIRMED,
            raw_transcript="Patient presents with severe migration headaches and general fatigue.",
            extracted_description="Migraine attack with structural fatigue clusters.",
            extracted_medicine="Ibuprofen 400mg tabs as required",
            embedding=[0.01] * 768 
        )
        session.add(initial_case)
        session.commit()
        
        print("✅ Success! Users (Doctor/Nurse) and Initial Cases initialized seamlessly into PostgreSQL.")


if __name__ == "__main__":
    seed_system_users_and_patients()
