import os

def test_upload_claim(client, officer_token, tmp_path):
    # Create a dummy file
    dummy_file = tmp_path / "test.pdf"
    dummy_file.write_text("dummy pdf content")

    with open(dummy_file, "rb") as f:
        response = client.post(
            "/claims/upload",
            headers={"Authorization": f"Bearer {officer_token}"},
            data={
                "patient_ref": "PAT_001",
                "provider_ref": "PRV_001",
                "procedure_code": "99213",
                "billed_amount": 150.0
            },
            files={"file": ("test.pdf", f, "application/pdf")}
        )
    assert response.status_code == 200
    assert "claim_id" in response.json()

def test_get_claims(client, officer_token):
    response = client.get(
        "/claims",
        headers={"Authorization": f"Bearer {officer_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert isinstance(data["items"], list)

def test_rbac_denies_officer(client, officer_token):
    # Officer shouldn't be able to update status
    response = client.post(
        "/claims/1/status",
        headers={"Authorization": f"Bearer {officer_token}"},
        json={"status": "approved"}
    )
    assert response.status_code == 403

def test_rbac_allows_admin(client, admin_token):
    # Admin should be able to update status
    response = client.post(
        "/claims/1/status",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"status": "approved"}
    )
    # Could be 200 or 404 (if claim 1 doesn't exist depending on execution order), but shouldn't be 403
    assert response.status_code in [200, 404]
