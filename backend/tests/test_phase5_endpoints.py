import pytest
from app.models.core import Claim, RiskAggregate, RiskThresholdConfig

def test_get_risk_aggregate_happy(client, admin_token, db):
    claim1 = Claim(id=1, submitted_by=1, patient_ref="PAT_01", provider_ref="PROV_01", procedure_code="123", billed_amount=100.0)
    db.merge(claim1)
    
    # Needs risk bands
    if not db.query(RiskThresholdConfig).first():
        db.add_all([
            RiskThresholdConfig(risk_band="Low", lower_bound=0.0, upper_bound=0.3),
            RiskThresholdConfig(risk_band="Medium", lower_bound=0.3, upper_bound=0.7),
            RiskThresholdConfig(risk_band="High", lower_bound=0.7, upper_bound=1.0)
        ])
    
    agg = RiskAggregate(claim_id=1, aggregate_score=0.8, fraud_score=0.9, anomaly_score=0.1, duplicate_score=0.1, graph_score=0.1, cost_score=0.1, provider_score=0.1, weighting_version="1.0")
    db.merge(agg)
    db.commit()

    res = client.get("/claims/1/risk-aggregate", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["claim_id"] == 1
    assert data["aggregate_score"] == 0.8
    assert data["risk_band"] == "High"

def test_get_risk_aggregate_not_found(client, admin_token):
    res = client.get("/claims/999/risk-aggregate", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 404

def test_get_risk_aggregate_unauth(client):
    res = client.get("/claims/1/risk-aggregate")
    assert res.status_code == 401

def test_get_risk_aggregate_rbac(client, officer_token):
    res = client.get("/claims/1/risk-aggregate", headers={"Authorization": f"Bearer {officer_token}"})
    # Officer role might be allowed? The route says:
    # ["Admin", "Investigator", "Auditor", "Supervisor", "Officer"]
    # So Officer is allowed. Wait, we need an unauthorized role.
    # Let's test with a fake role or without token.
    # The requirement is to test RBAC. Since Officer IS allowed here, we could expect 200.
    # Wait, the prompt says "RBAC: request from a role that shouldn't have access -> 403".
    # I'll create a user with "Provider" role or something not in the list.
    pass

def test_get_risk_aggregate_rbac_forbidden(client, db):
    from app.models.core import User
    from app.services.auth_service import get_password_hash, create_access_token
    # Create a user with a role not in the allowed list
    forbidden_user = User(email="forbidden@test.com", hashed_password=get_password_hash("pass"), role="UnknownRole")
    db.add(forbidden_user)
    db.commit()
    db.refresh(forbidden_user)
    token = create_access_token(data={"sub": forbidden_user.email, "role": forbidden_user.role})
    
    res = client.get("/claims/1/risk-aggregate", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403
