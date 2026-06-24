"""
Seed the database with sample crime records for development/demo purposes.
Run: python seed.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.core.database import SessionLocal, init_db
from app.models.crime_record import CrimeRecord, ProcessingStatus, SourceType
from app.services.search_service import update_search_vector
from datetime import date

SAMPLES = [
    {
        "crime_category": "Cyber Fraud",
        "fir_number": "CR/2024/CYB/0421",
        "crime_date": date(2024, 3, 15),
        "police_station": "Cyber Crime PS",
        "district": "Bengaluru Urban",
        "state": "Karnataka",
        "legal_sections": ["IPC 420", "IT Act 66C", "IT Act 66D"],
        "amount_involved": 450000,
        "modus_operandi": "Victim received a call from a person claiming to be a bank official. The caller persuaded the victim to share OTP for KYC update, following which multiple unauthorized UPI transactions were made.",
        "keywords": ["UPI fraud", "OTP scam", "bank impersonation", "KYC fraud", "cyber crime"],
        "summary": "A cyber fraud case involving UPI-based financial fraud amounting to ₹4.5 lakh. The accused impersonated a bank official and obtained OTP details from the victim under the pretext of KYC verification, leading to unauthorized transactions.",
        "entities": {"payment_methods": ["UPI", "NEFT"], "organizations": ["State Bank of India"]},
        "latitude": 12.9716,
        "longitude": 77.5946,
        "source_type": SourceType.FIR,
    },
    {
        "crime_category": "Vehicle Theft",
        "fir_number": "CR/2024/VEH/0782",
        "crime_date": date(2024, 4, 2),
        "police_station": "Andheri Police Station",
        "district": "Mumbai Suburban",
        "state": "Maharashtra",
        "legal_sections": ["IPC 379"],
        "amount_involved": 185000,
        "modus_operandi": "Two-wheeler was parked outside a shopping complex. The vehicle was stolen by unknown persons during night hours by breaking the steering lock.",
        "keywords": ["vehicle theft", "two-wheeler", "steering lock", "night theft"],
        "summary": "A two-wheeler worth approximately ₹1.85 lakh was stolen from outside a shopping complex in Andheri during night hours. The steering lock was broken by unknown perpetrators.",
        "entities": {"vehicle_types": ["Two-wheeler", "Motorcycle"]},
        "latitude": 19.1136,
        "longitude": 72.8697,
        "source_type": SourceType.FIR,
    },
    {
        "crime_category": "Cheating",
        "fir_number": "CR/2024/CHT/0219",
        "crime_date": date(2024, 2, 20),
        "police_station": "Connaught Place PS",
        "district": "Central Delhi",
        "state": "Delhi",
        "legal_sections": ["IPC 420", "IPC 406", "IPC 34"],
        "amount_involved": 1200000,
        "modus_operandi": "Accused posed as a real estate broker and collected advance booking amounts from multiple buyers for properties that were not legally cleared for sale.",
        "keywords": ["real estate fraud", "property scam", "advance booking", "cheating"],
        "summary": "A cheating case involving fraudulent real estate transactions worth ₹12 lakh. The accused collected advance booking amounts from multiple buyers by misrepresenting the legal status of properties.",
        "entities": {"organizations": ["Delhi Real Estate Authority"]},
        "latitude": 28.6315,
        "longitude": 77.2167,
        "source_type": SourceType.FIR,
    },
    {
        "crime_category": "Drug Trafficking",
        "fir_number": "CR/2024/DRG/0056",
        "crime_date": date(2024, 1, 10),
        "police_station": "Anna Nagar PS",
        "district": "Chennai",
        "state": "Tamil Nadu",
        "legal_sections": ["NDPS Act 20(b)(ii)(C)", "NDPS Act 29"],
        "amount_involved": None,
        "modus_operandi": "Seized contraband substances during a vehicle checkpost. The accused were transporting controlled substances concealed inside commercial goods containers.",
        "keywords": ["NDPS", "drug trafficking", "contraband", "narcotics seizure"],
        "summary": "Contraband narcotic substances were seized during a routine vehicle checkpost operation. The accused persons were transporting narcotics concealed within commercial cargo.",
        "entities": {"vehicle_types": ["Truck", "Heavy vehicle"]},
        "latitude": 13.0827,
        "longitude": 80.2707,
        "source_type": SourceType.FIR,
    },
    {
        "crime_category": "Robbery",
        "fir_number": "CR/2024/ROB/0334",
        "crime_date": date(2024, 3, 28),
        "police_station": "Sector 29 PS",
        "district": "Gurugram",
        "state": "Haryana",
        "legal_sections": ["IPC 392", "IPC 397"],
        "amount_involved": 75000,
        "modus_operandi": "Victim was returning from ATM when two motorcycle-borne persons snatched a bag containing cash and valuables at knife-point near a residential colony.",
        "keywords": ["snatching", "knife point", "ATM robbery", "chain snatching", "motorcycle"],
        "summary": "A robbery case where the victim was waylaid near a residential colony by two motorcycle-borne accused who snatched cash and valuables at knife-point after the victim withdrew money from an ATM.",
        "entities": {"vehicle_types": ["Motorcycle"]},
        "latitude": 28.4595,
        "longitude": 77.0266,
        "source_type": SourceType.FIR,
    },
]


def seed():
    print("Initializing database...")
    init_db()

    db = SessionLocal()
    try:
        existing = db.query(CrimeRecord).count()
        if existing > 0:
            print(f"Database already has {existing} records. Skipping seed.")
            return

        print(f"Seeding {len(SAMPLES)} sample crime records...")
        for s in SAMPLES:
            record = CrimeRecord(
                source_type=s.pop("source_type"),
                processing_status=ProcessingStatus.COMPLETED,
                is_published=True,
                redacted_text=f"Sample redacted text for {s['crime_category']} case {s['fir_number']}",
                registration_date=s["crime_date"],
                **s,
            )
            db.add(record)
            db.flush()
            update_search_vector(db, record)
            print(f"  + {record.crime_category} — {record.fir_number}")

        db.commit()
        print("Seed complete.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
