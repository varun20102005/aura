import pytest
import numpy as np
from fastapi.testclient import TestClient
from app.services.drift_service import calculate_psi
from app.models.core import ModelRegistry, DriftReport, ModelScore

def test_calculate_psi():
    # Two identical distributions should have 0 PSI
    dist1 = np.random.normal(0, 1, 1000)
    dist2 = dist1.copy()
    psi = calculate_psi(dist1, dist2)
    assert psi < 0.001
    
    # Shifted distributions should have high PSI
    dist3 = np.random.normal(1, 1, 1000)
    psi_shifted = calculate_psi(dist1, dist3)
    assert psi_shifted > 0.20

def test_drift_endpoints(client: TestClient, db, admin_token):
    # Setup model and drift report
    m = ModelRegistry(model_type="xgboost", version="v1.0.0", status="active", metrics_json={"auc": 0.9}, artifact_path="fake")
    db.add(m)
    db.commit()
    db.refresh(m)
    
    report = DriftReport(model_id=m.id, feature_or_prediction="xgb", drift_metric="PSI", value=0.25, threshold=0.20, flagged=1)
    db.add(report)
    db.commit()
    
    # Test evaluation-report
    resp = client.get("/admin/models/evaluation-report", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["models"]) >= 1
    model_data = next(md for md in data["models"] if md["model_id"] == m.id)
    assert model_data["drift_status"]["flagged"] == 1
    assert model_data["drift_status"]["value"] == 0.25
    
    # Test individual drift report
    resp2 = client.get(f"/admin/models/{m.id}/drift-report", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert len(data2) == 1
    assert data2[0]["value"] == 0.25
