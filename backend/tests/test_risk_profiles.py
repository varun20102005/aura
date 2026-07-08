import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.core import Base, Claim
from app.services.risk_service import compute_provider_risk

def utcnow():
    return datetime.now(timezone.utc)

@pytest.fixture(scope="function")
def test_db():
    engine = create_engine("sqlite:///:memory:")
    tables = [t for t in Base.metadata.sorted_tables if t.name != 'claim_embeddings']
    Base.metadata.create_all(bind=engine, tables=tables)
    Session = sessionmaker(bind=engine)
    db = Session()
    yield db
    db.close()

def test_leakage_safety_rule(test_db):
    """
    CRITICAL: Enforce the leakage-safety rule from TRD §6.2: 
    only outcomes finalized BEFORE the timestamp of the claim being scored 
    may be included in that claim's provider-risk feature.
    """
    time_T = utcnow()
    time_T_minus_1 = time_T - timedelta(days=1)
    time_T_plus_1 = time_T + timedelta(days=1)
    
    # 1. Outcome finalized BEFORE T (Should be included)
    test_db.add(Claim(
        provider_ref="PRV_LEAK",
        status="denied",
        updated_at=time_T_minus_1
    ))
    
    # 2. Outcome finalized AFTER T (Should NOT be included when scoring at T)
    test_db.add(Claim(
        provider_ref="PRV_LEAK",
        status="approved",
        updated_at=time_T_plus_1
    ))
    test_db.commit()
    
    # Score the claim at time T
    risk_score, total = compute_provider_risk(test_db, "PRV_LEAK", as_of_time=time_T)
    
    # Prove that ONLY the claim at T-1 was included (total=1, risk_score=1.0 because it was denied)
    # The claim at T+1 (approved) was ignored, otherwise risk_score would be 0.5 and total 2.
    assert total == 1
    assert risk_score == 1.0
    
    # If we score as of T+2, it SHOULD include the future claim
    risk_score_future, total_future = compute_provider_risk(test_db, "PRV_LEAK", as_of_time=time_T_plus_1 + timedelta(seconds=1))
    assert total_future == 2
    assert risk_score_future == 0.5

def test_get_risk_profile_endpoint(client, admin_token, test_db):
    # This requires mocking the DB state or running the scheduled job.
    # In integration we can just verify the 200 behavior for empty DB.
    response = client.get("/providers/UNKNOWN/risk-profile", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    assert response.json().get("status") == "INSUFFICIENT_HISTORY"
    
def test_admin_bulk_risk_profiles_rbac(client, officer_token):
    # Admin bulk view requires Admin role, officer should be denied 403
    response = client.get("/admin/providers/risk-profiles", headers={"Authorization": f"Bearer {officer_token}"})
    assert response.status_code == 403
