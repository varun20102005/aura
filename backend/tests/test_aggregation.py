import pytest
from app.services.aggregation_service import normalize_components, sigmoid, get_active_weights
from app.models.core import Claim, RiskWeightConfig
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.core import Base

def test_normalization_bounds():
    # Test sigmoid squash
    assert 0.0 < sigmoid(-5.0) < 1.0
    assert 0.0 < sigmoid(5.0) < 1.0
    
def test_get_active_weights(db):
    # Empty out active weights
    db.query(RiskWeightConfig).delete()
    db.commit()

    # Should fallback to equal weights if none exist
    weights = get_active_weights(db)
    assert weights["version"] == "fallback"
    assert weights["fraud"] == 1.0 / 6.0
    
    # Insert custom weights
    db.add(RiskWeightConfig(
        version="v2.0",
        fraud_weight=0.5, anomaly_weight=0.1, duplicate_weight=0.1,
        graph_weight=0.1, cost_weight=0.1, provider_weight=0.1,
        is_active=1
    ))
    db.commit()
    
    new_weights = get_active_weights(db)
    assert new_weights["version"] == "v2.0"
    assert new_weights["fraud"] == 0.5
    
def test_put_weights_regression(client, admin_token, db):
    # Update weights via endpoint
    payload = {
        "version": "v3.0",
        "fraud_weight": 0.4,
        "anomaly_weight": 0.2,
        "duplicate_weight": 0.1,
        "graph_weight": 0.1,
        "cost_weight": 0.1,
        "provider_weight": 0.1
    }
    response = client.put("/admin/risk-aggregate/weights", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    
    # Ensure they are active
    active = db.query(RiskWeightConfig).filter_by(is_active=1).first()
    assert active.version == "v3.0"
    assert active.fraud_weight == 0.4
