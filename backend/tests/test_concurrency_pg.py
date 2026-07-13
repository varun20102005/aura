import os
import pytest
import concurrent.futures
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.core import Claim, InvestigationNote, CaseAssignment
from app.config import settings

pytestmark = pytest.mark.skipif(
    settings.DATABASE_URL.startswith("sqlite"),
    reason="NOT EXECUTED — POSTGRESQL ENVIRONMENT REQUIRED. SQLite cannot handle high-concurrency writes reliably without locking."
)

def create_claim_concurrently(patient_ref, procedure_code):
    db = SessionLocal()
    try:
        new_claim = Claim(
            patient_ref=patient_ref,
            provider_ref="PRV_CONCUR",
            procedure_code=procedure_code,
            billed_amount=150.0,
            status="uploaded"
        )
        db.add(new_claim)
        db.commit()
        db.refresh(new_claim)
        return new_claim.id
    finally:
        db.close()

def test_concurrent_claim_submissions():
    """Verify that multiple users submitting claims at the same exact time does not deadlock PostgreSQL."""
    num_claims = 50
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(create_claim_concurrently, f"PAT_CON_{i}", f"PROC_{i}")
            for i in range(num_claims)
        ]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
    assert len(results) == num_claims
    
def add_note_concurrently(claim_id, note_text):
    db = SessionLocal()
    try:
        new_note = InvestigationNote(claim_id=claim_id, author_id=1, note_text=note_text)
        db.add(new_note)
        db.commit()
        return True
    finally:
        db.close()

def test_concurrent_note_creation():
    """Verify concurrent inserts to child tables avoid race conditions."""
    db = SessionLocal()
    
    from app.models.core import User
    u = db.query(User).filter_by(id=1).first()
    if not u:
        u = User(id=1, email="test_author@test.com", hashed_password="pw", role="Officer")
        db.add(u)
    
    c = Claim(patient_ref="PAT_NOTE", provider_ref="PRV", procedure_code="123", billed_amount=100)
    db.add(c)
    db.commit()
    db.refresh(c)
    claim_id = c.id
    db.close()

    num_notes = 20
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(add_note_concurrently, claim_id, f"Note {i}")
            for i in range(num_notes)
        ]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
    assert len(results) == num_notes
