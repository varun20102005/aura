import pytest
from fastapi.testclient import TestClient
from datetime import datetime
import io
import csv
import json

from app.main import app
from app.database import get_db
from app.models.core import User, Claim, AuditLog, CaseAssignment, RiskAggregate, RiskThresholdConfig, ClaimDocument
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.core import Base
from app.routers.auth import get_current_user

# Test DB Setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_workflow.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

def override_get_current_user():
    return User(id=1, email="admin@aura.com", role="Admin")

@pytest.fixture(scope="module", autouse=True)
def override_deps():
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    yield
    app.dependency_overrides.clear()

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    tables = [t for t in Base.metadata.sorted_tables if t.name != 'claim_embeddings']
    Base.metadata.create_all(bind=engine, tables=tables)
    db = TestingSessionLocal()
    
    # Create test users
    admin = User(id=1, email="admin@aura.com", role="Admin", hashed_password="pw")
    investigator = User(id=2, email="inv@aura.com", role="Investigator", hashed_password="pw")
    
    # Create risk configs
    db.add_all([
        RiskThresholdConfig(risk_band="Low", lower_bound=0.0, upper_bound=0.3),
        RiskThresholdConfig(risk_band="Medium", lower_bound=0.31, upper_bound=0.7),
        RiskThresholdConfig(risk_band="High", lower_bound=0.71, upper_bound=1.0),
    ])
    
    # Create test claims
    c1 = Claim(id=1, patient_ref="P001", provider_ref="PR001", status="processing")
    c2 = Claim(id=2, patient_ref="P002", provider_ref="PR002", status="uploaded")
    
    db.add_all([admin, investigator, c1, c2])
    db.commit()
    
    # Add aggregates
    db.add(RiskAggregate(claim_id=1, aggregate_score=0.9, weighting_version="v1")) # High
    db.add(RiskAggregate(claim_id=2, aggregate_score=0.2, weighting_version="v1")) # Low
    db.commit()
    
    yield
    tables = [t for t in Base.metadata.sorted_tables if t.name != 'claim_embeddings']
    Base.metadata.drop_all(bind=engine, tables=tables)
    db.close()

def test_assign_claim():
    # Assign High risk claim to investigator 2
    res = client.post("/claims/1/assign", json={"investigator_id": 2})
    assert res.status_code == 200
    data = res.json()
    assert "assignment_id" in data
    
    # Assign Low risk claim
    res = client.post("/claims/2/assign", json={"investigator_id": 2})
    assert res.status_code == 200
    
    # Verify SLA
    db = TestingSessionLocal()
    a1 = db.query(CaseAssignment).filter_by(claim_id=1).first()
    a2 = db.query(CaseAssignment).filter_by(claim_id=2).first()
    
    diff_h = (a1.sla_due_at - a1.assigned_at).total_seconds() / 3600
    diff_l = (a2.sla_due_at - a2.assigned_at).total_seconds() / 3600
    
    assert abs(diff_h - 24) < 1.0 # High risk = 24h
    assert abs(diff_l - 168) < 1.0 # Low risk = 168h
    db.close()

def test_investigator_workload():
    res = client.get("/investigators/2/workload")
    assert res.status_code == 200
    assert len(res.json()) >= 1 # Claim 1 is 'processing', Claim 2 is 'uploaded' (not processing/action_required)

def test_search_claims():
    # Search by patient_ref
    res = client.get("/claims/search?query=P001")
    if res.status_code != 200:
        print("SEARCH CLAIMS 422 ERROR:", res.json())
    assert res.status_code == 200
    assert len(res.json()["items"]) == 1
    assert res.json()["items"][0]["id"] == 1
    
    # Search by status
    res = client.get("/claims/search?status=uploaded")
    assert len(res.json()["items"]) == 1
    assert res.json()["items"][0]["id"] == 2
    
    # Search by risk band (requires memory filtering)
    res = client.get("/claims/search?risk_band=High")
    assert len(res.json()["items"]) == 1
    assert res.json()["items"][0]["id"] == 1
    
def test_bulk_upload():
    # Prepare CSV
    csv_content = "patient_ref,provider_ref,procedure_code,billed_amount,document_filename\n"
    csv_content += "PT_BULK1,PR_B1,C100,500.0,doc1.pdf\n"
    csv_content += "PT_BULK2,PR_B2,C101,600.0,doc2.pdf\n" # Missing file
    
    files = [
        ("manifest", ("manifest.csv", csv_content, "text/csv")),
        ("documents", ("doc1.pdf", b"%PDF-dummy", "application/pdf")),
    ]
    
    res = client.post("/claims/bulk-upload", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["successful_records"] == 1
    assert data["failed_records"] == 1
    assert "not found" in data["errors"][0]["error"]

def test_audit_export_csv():
    res = client.get("/admin/audit-logs/export?format=csv")
    assert res.status_code == 200
    assert res.headers["content-type"] == "text/csv; charset=utf-8"
    assert "attachment; filename=audit_export.csv" in res.headers["content-disposition"]
    
def test_audit_export_pdf():
    res = client.get("/admin/audit-logs/export?format=pdf")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert "attachment; filename=audit_export.pdf" in res.headers["content-disposition"]
    assert res.content.startswith(b"%PDF-")
