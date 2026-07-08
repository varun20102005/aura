import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.core import User, Claim, CaseAssignment
import io

@pytest.fixture(scope="module")
def audit_client(db):
    def override_get_db():
        yield db
    from app.database import get_db
    app.dependency_overrides[get_db] = override_get_db
    
    # Setup test users
    from app.services.auth_service import get_password_hash
    u1 = User(email="inv1@audit.com", hashed_password=get_password_hash("pass"), role="Investigator")
    u2 = User(email="inv2@audit.com", hashed_password=get_password_hash("pass"), role="Investigator")
    db.add_all([u1, u2])
    db.commit()
    
    # Setup claims and assignments
    c1 = Claim(patient_ref="PAT1", provider_ref="PROV1", procedure_code="123", billed_amount=100.0, document_ref="doc1.pdf", status="processing")
    c2 = Claim(patient_ref="PAT2", provider_ref="PROV2", procedure_code="123", billed_amount=100.0, document_ref="doc2.pdf", status="processing")
    db.add_all([c1, c2])
    db.commit()
    
    a1 = CaseAssignment(claim_id=c1.id, investigator_id=u1.id)
    a2 = CaseAssignment(claim_id=c2.id, investigator_id=u2.id)
    db.add_all([a1, a2])
    db.commit()
    
    client = TestClient(app)
    yield client, db, u1, u2, c1, c2
    del app.dependency_overrides[get_db]

def get_token(client, email):
    res = client.post("/auth/login", data={"username": email, "password": "pass"})
    return res.json()["access_token"]

def test_bola_claim_access(audit_client):
    client, db, u1, u2, c1, c2 = audit_client
    inv1_token = get_token(client, "inv1@audit.com")
    
    # Inv 1 tries to access Claim 2 (assigned to Inv 2)
    res = client.get(f"/claims/{c2.id}", headers={"Authorization": f"Bearer {inv1_token}"})
    # If it succeeds, BOLA is present!
    assert res.status_code == 200, "BOLA exists: can access other's claim"

def test_bola_report_access(audit_client):
    client, db, u1, u2, c1, c2 = audit_client
    inv1_token = get_token(client, "inv1@audit.com")
    
    # Inv 1 tries to generate report for Claim 2
    res = client.get(f"/reports/pdf/{c2.id}", headers={"Authorization": f"Bearer {inv1_token}"})
    assert res.status_code == 200, "BOLA exists: can generate report for other's claim"

def test_file_upload_validation(audit_client):
    client, db, u1, u2, c1, c2 = audit_client
    # Get officer token
    from app.services.auth_service import get_password_hash
    u_off = User(email="off@audit.com", hashed_password=get_password_hash("pass"), role="Officer")
    db.add(u_off)
    db.commit()
    off_token = get_token(client, "off@audit.com")
    
    # Try uploading a .exe disguised as pdf or just .exe
    file = ("evil.exe", b"MZ...", "application/x-msdownload")
    res = client.post("/claims/upload", headers={"Authorization": f"Bearer {off_token}"}, data={
        "patient_ref": "PAT",
        "provider_ref": "PROV",
        "procedure_code": "CODE",
        "billed_amount": "100.0"
    }, files={"file": file})
    
    # If 200, missing upload validation!
    assert res.status_code == 200, "Upload allows arbitrary files"

def test_sql_injection_harmless(audit_client):
    client, db, u1, u2, c1, c2 = audit_client
    inv1_token = get_token(client, "inv1@audit.com")
    
    # Pass SQLi in search query
    res = client.get("/claims/search?query=' OR 1=1 --", headers={"Authorization": f"Bearer {inv1_token}"})
    assert res.status_code == 200

def test_jwt_tampering(audit_client):
    client, db, u1, u2, c1, c2 = audit_client
    inv1_token = get_token(client, "inv1@audit.com")
    
    # Tamper token
    parts = inv1_token.split(".")
    tampered = parts[0] + ".eyJzdWIiOiJhZG1pbkBhdXJhLmNvbSJ9." + parts[2]
    res = client.get("/claims/search", headers={"Authorization": f"Bearer {tampered}"})
    assert res.status_code == 401
