import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone
import json

from app.main import app
from app.database import get_db
from app.models.core import User, Claim, CaseAssignment, RiskAggregate, RiskThresholdConfig, ModelRegistry, DriftReport
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.core import Base
from app.routers.auth import get_current_user

# Test DB Setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_consistency.db"
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
    c1 = Claim(id=1, patient_ref="P001", provider_ref="PR001", status="action_required")
    c2 = Claim(id=2, patient_ref="P002", provider_ref="PR002", status="processing")
    c3 = Claim(id=3, patient_ref="P003", provider_ref="PR003", status="uploaded")
    
    db.add_all([admin, investigator, c1, c2, c3])
    db.commit()
    
    # Add aggregates
    db.add(RiskAggregate(claim_id=1, aggregate_score=0.85, weighting_version="v1")) # High
    db.add(RiskAggregate(claim_id=2, aggregate_score=0.45, weighting_version="v1")) # Medium
    db.add(RiskAggregate(claim_id=3, aggregate_score=0.10, weighting_version="v1")) # Low
    db.commit()
    
    yield
    tables = [t for t in Base.metadata.sorted_tables if t.name != 'claim_embeddings']
    Base.metadata.drop_all(bind=engine, tables=tables)
    db.close()

def test_dashboard_analytics_endpoints():
    # Fetch dashboard analytics
    response = client.get("/admin/dashboard/analytics")
    assert response.status_code == 200
    data = response.json()
    
    # Total claims = 3
    assert data["total_claims"] == 3
    
    # High Risk claims (claim 1 has score 0.85 >= 0.71) = 1
    assert data["high_risk_claims"] == 1
    
    # No assignments yet, so open investigations should be 0
    assert data["open_investigations"] == 0

def test_case_assignment_uniqueness_and_workload():
    db = TestingSessionLocal()
    
    # Assign claim 1 to investigator 2
    res = client.post("/claims/1/assign", json={"investigator_id": 2})
    assert res.status_code == 200
    
    # Re-assign same claim 1 to investigator 2
    res2 = client.post("/claims/1/assign", json={"investigator_id": 2})
    assert res2.status_code == 200
    
    # Verify only 1 CaseAssignment record exists for claim 1
    count = db.query(CaseAssignment).filter_by(claim_id=1, investigator_id=2).count()
    assert count == 1
    
    # Verify open investigations on dashboard equals 1 (claim 1 has status 'action_required' and is assigned)
    res_dash = client.get("/admin/dashboard/analytics")
    assert res_dash.json()["open_investigations"] == 1
    
    # Verify investigator workload returns exactly 1 item for claim 1 (no duplicates)
    res_work = client.get("/investigators/2/workload")
    assert res_work.status_code == 200
    workload = res_work.json()
    assert len(workload) == 1
    assert workload[0]["id"] == 1
    
    db.close()

def test_model_telemetry_reporting():
    db = TestingSessionLocal()
    
    # Insert test models in registry
    m1 = ModelRegistry(
        id=10, 
        model_type="xgboost", 
        version="v1.0.0", 
        status="active", 
        artifact_path="backend/ml_models/xgboost_fraud.json", # will check if exists (might be offline/operational depending on context)
        metrics_json={"accuracy": 0.98}
    )
    m2 = ModelRegistry(
        id=11, 
        model_type="isolation_forest", 
        version="v1.0.0", 
        status="active", 
        artifact_path="nonexistent.joblib", 
        metrics_json=None # UNAVAILABLE
    )
    
    db.add_all([m1, m2])
    db.commit()
    
    # Add drift report for model 10
    d1 = DriftReport(
        model_id=10,
        feature_or_prediction="pred",
        drift_metric="PSI",
        value=0.08,
        threshold=0.1,
        flagged=0
    )
    db.add(d1)
    db.commit()
    
    # Fetch report
    res = client.get("/admin/models/evaluation-report")
    assert res.status_code == 200
    report = res.json()["models"]
    
    # Find xgboost
    xgb_rep = next(m for m in report if m["model_id"] == 10)
    assert xgb_rep["evaluation_status"] == "AVAILABLE"
    assert xgb_rep["metrics"]["accuracy"] == 0.98
    assert xgb_rep["drift_monitoring_status"] == "MONITORED"
    assert xgb_rep["drift_status"]["flagged"] is False
    
    # Find isolation_forest
    iso_rep = next(m for m in report if m["model_id"] == 11)
    assert iso_rep["evaluation_status"] == "UNAVAILABLE"
    assert iso_rep["metrics"] is None
    assert iso_rep["drift_monitoring_status"] == "UNAVAILABLE"
    assert iso_rep["runtime_status"] == "OFFLINE" # artifact path is nonexistent
    
    # Clean up test registry models
    db.delete(d1)
    db.delete(m1)
    db.delete(m2)
    db.commit()
    db.close()
