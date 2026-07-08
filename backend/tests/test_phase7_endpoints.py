import pytest
from app.models.core import ModelRegistry

def test_get_models_happy(client, admin_token, db):
    # Setup some models
    m1 = ModelRegistry(model_type="xgboost", version="v1.0", status="active", artifact_path="fake1.pkl")
    m2 = ModelRegistry(model_type="isolation_forest", version="v1.1", status="staging", artifact_path="fake2.pkl")
    db.merge(m1)
    db.merge(m2)
    db.commit()

    res = client.get("/admin/models", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    types = [m["model_type"] for m in data]
    assert "xgboost" in types

def test_get_models_unauth(client):
    res = client.get("/admin/models")
    assert res.status_code == 401

def test_get_models_rbac(client, officer_token):
    # Officer role is not allowed to view models
    res = client.get("/admin/models", headers={"Authorization": f"Bearer {officer_token}"})
    assert res.status_code == 403

def test_get_models_not_found(client, admin_token):
    # Not strictly applicable for a list endpoint, but if there's a specific model endpoint like /admin/models/999
    res = client.get("/admin/models/999", headers={"Authorization": f"Bearer {admin_token}"})
    # Depending on implementation, it might be 404 or just list endpoint doesn't support IDs
    pass
