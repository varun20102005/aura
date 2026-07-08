import pytest
from app.models.core import Claim, ClaimDocument

def test_get_similar_happy(client, admin_token, db):
    # Setup claims and documents
    claim1 = Claim(id=1, submitted_by=1, patient_ref="PAT_01", provider_ref="PROV_01", procedure_code="123", billed_amount=100.0)
    claim2 = Claim(id=2, submitted_by=1, patient_ref="PAT_02", provider_ref="PROV_01", procedure_code="123", billed_amount=100.0)
    db.merge(claim1)
    db.merge(claim2)
    db.commit()

    doc1 = ClaimDocument(claim_id=1, file_path="test1.pdf", ocr_text="Medical claim for patient 01")
    doc2 = ClaimDocument(claim_id=2, file_path="test2.pdf", ocr_text="Medical claim for patient 02")
    db.merge(doc1)
    db.merge(doc2)
    db.commit()

    res = client.get("/claims/1/similar?method=fuzzy", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    # claim 2 should be in results
    assert any(c["claim_id"] == 2 for c in data)

def test_get_similar_not_found(client, admin_token):
    res = client.get("/claims/999/similar", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 404

def test_get_similar_unauth(client):
    res = client.get("/claims/1/similar")
    assert res.status_code == 401

def test_get_similar_rbac(client, officer_token):
    # Depending on RBAC, if Officer is not allowed
    # Note: TRD says Officer usually has limited access, but let's see if it's 403.
    # From routers/claims.py: require_role(["Admin", "Investigator", "Auditor", "Supervisor"])
    res = client.get("/claims/1/similar", headers={"Authorization": f"Bearer {officer_token}"})
    assert res.status_code == 403

def test_get_similar_validation(client, admin_token):
    # method isn't strictly validated to an enum in the endpoint definition (it's just a str with default "hybrid")
    # but let's test a bad limit type
    res = client.get("/claims/1/similar?limit=notanumber", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 422
