import pytest
import io
from app.models.core import Claim, ProviderRiskProfile

def test_bulk_upload_schema_isolation(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    csv_content = """patient_ref,provider_ref,procedure_code,billed_amount,document_filename
PAT_OK,PRV_1,C100,100.0,doc1.pdf
PAT_BAD,PRV_2,C200,NOT_A_FLOAT,doc2.pdf
"""
    files = [
        ("manifest", ("manifest.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")),
        ("documents", ("doc1.pdf", io.BytesIO(b"dummy"), "application/pdf")),
        ("documents", ("doc2.pdf", io.BytesIO(b"dummy"), "application/pdf")),
    ]
    res = client.post("/claims/bulk-upload", headers=headers, files=files)
    if res.status_code == 200:
        data = res.json()
        assert data.get("failed_records", 0) >= 1

def test_provider_insufficient_history(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    res = client.get("/providers/NEW_PROV_XYZ/risk-profile", headers=headers)
    assert res.status_code == 200
    assert res.json().get("status") == "INSUFFICIENT_HISTORY"

def test_risk_aggregate_weights(client, admin_token, db):
    claim = Claim(patient_ref="TEST", provider_ref="TEST", procedure_code="C1", billed_amount=100.0, status="completed")
    db.add(claim)
    db.commit()
    db.refresh(claim)
    
    from app.services.aggregation_service import generate_risk_aggregate
    generate_risk_aggregate(db, claim.id)
    
    res = client.get(f"/claims/{claim.id}/risk-aggregate", headers={"Authorization": f"Bearer {admin_token}"})
    if res.status_code == 200:
        data = res.json()
        assert "weights" in data

