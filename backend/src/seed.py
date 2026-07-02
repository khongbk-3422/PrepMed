import json
from database import get_session
from models import MedicalTemplate

def seed_universal_template():
    with next(get_session()) as db:
        # Define a single, powerful template that works for any disease/complaint
        universal_template = MedicalTemplate(
            id=1,
            title="Universal Clinical Intake Sheet",
            # 👇 FIXED: Pass the raw Python list directly! Do not use json.dumps()
            required_items=[
                "chief_complaint",
                "history_of_present_illness",
                "observed_clinical_signs",
                "suspected_conditions",
                "immediate_plan_or_tests"
            ],
            default_description="Initial unstructured clinical evaluation notes.",
            default_medicine="-",
            created_by_user_id=1
        )
        
        existing = db.get(MedicalTemplate, universal_template.id)
        if existing:
            # Overwrite the old disease-specific template with our clean universal layout
            existing.title = universal_template.title
            existing.required_items = universal_template.required_items
            existing.default_description = universal_template.default_description
            existing.default_medicine = universal_template.default_medicine
            db.add(existing)
        else:
            db.add(universal_template)
            
        db.commit()
        print("🌱 Universal Intake Template deployed successfully into PostgreSQL!")

if __name__ == "__main__":
    seed_universal_template()
