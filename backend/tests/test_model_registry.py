import pytest
from fastapi.testclient import TestClient
from app.models.core import ModelRegistry, AuditLog
from app.services.model_registry import register_model

def test_register_model(db, admin_token):
    metrics = {"auc": 0.95, "precision": 0.88}
    model = register_model(db, "xgboost", "v2.0.0", metrics, "ml_models/xgboost/v2.0.0.json", actor_id=1)
    
    assert model.id is not None
    assert model.status == "candidate"
    assert model.model_type == "xgboost"
    
    # Check audit log
    log = db.query(AuditLog).filter_by(action="MODEL_REGISTERED", entity_id=str(model.id)).first()
    assert log is not None

def test_promote_model(client: TestClient, db, admin_token):
    # Register an active model first
    active_m = register_model(db, "isolation_forest", "v1.0.0", {"auc": 0.90}, "path1", actor_id=1)
    active_m.status = "active"
    db.commit()
    
    # Register candidate
    cand_m = register_model(db, "isolation_forest", "v1.1.0", {"auc": 0.96}, "path2", actor_id=1)
    
    response = client.post(
        f"/admin/models/{cand_m.id}/promote",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "comparison" in data
    assert data["comparison"]["metrics_diff"]["auc"]["improvement"] > 0
    
    db.refresh(active_m)
    db.refresh(cand_m)
    
    assert active_m.status == "retired"
    assert cand_m.status == "active"
    
    # Check audit log
    log = db.query(AuditLog).filter_by(action="MODEL_PROMOTED", entity_id=str(cand_m.id)).first()
    assert log is not None
    assert log.metadata_json["retired_version"] == "v1.0.0"

def test_rollback_model(client: TestClient, db, admin_token):
    # Setup state: v1.1.0 is active, v1.0.0 is retired
    m_retired = register_model(db, "xgboost", "v1.0.0", {"auc": 0.9}, "path1", actor_id=1)
    m_retired.status = "retired"
    
    m_active = register_model(db, "xgboost", "v1.1.0", {"auc": 0.92}, "path2", actor_id=1)
    m_active.status = "active"
    db.commit()
    
    response = client.post(
        f"/admin/models/{m_retired.id}/rollback",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    
    db.refresh(m_retired)
    db.refresh(m_active)
    assert m_active.status == "retired"
    assert m_retired.status == "active"
    
    log = db.query(AuditLog).filter_by(action="MODEL_ROLLED_BACK", entity_id=str(m_retired.id)).first()
    assert log is not None
    assert log.metadata_json["rolled_back_to"] == "v1.0.0"
    
def test_non_admin_cannot_promote(client: TestClient, db, officer_token):
    cand_m = register_model(db, "xgboost", "v9.9.9", {"auc": 0.99}, "path9", actor_id=1)
    
    response = client.post(
        f"/admin/models/{cand_m.id}/promote",
        headers={"Authorization": f"Bearer {officer_token}"}
    )
    assert response.status_code == 403
    assert "Not enough permissions" in response.text
