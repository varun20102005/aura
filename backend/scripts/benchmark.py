import time
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models.core import User
from app.services.auth_service import create_access_token

def run_benchmark():
    client = TestClient(app)
    db = SessionLocal()
    
    # Get an admin user or create one
    admin = db.query(User).filter_by(email="admin@test.com").first()
    if not admin:
        from app.services.auth_service import get_password_hash
        admin = User(email="admin@test.com", hashed_password=get_password_hash("pass"), role="Admin")
        db.add(admin)
        db.commit()
        db.refresh(admin)
        
    token = create_access_token({"sub": admin.email, "role": "Admin", "user_id": admin.id})
    headers = {"Authorization": f"Bearer {token}"}
    
    print("--- PERFORMANCE BASELINE ---")
    
    # 1. Claims List
    start = time.time()
    res = client.get("/claims/search", headers=headers)
    t_claims = time.time() - start
    print(f"Claims List (/claims/search): {t_claims:.4f} s")
    
    # 2. Analytics Dashboard
    start = time.time()
    res = client.get("/analytics/dashboard", headers=headers)
    t_dash = time.time() - start
    print(f"Dashboard Analytics (/analytics/dashboard): {t_dash:.4f} s")
    
    # Get a claim ID
    claims = client.get("/claims/search", headers=headers).json()
    if not claims:
        print("No claims found for detailed benchmarks.")
        return
    claim_id = claims[0]["id"]
    provider_id = claims[0].get("provider_ref", "PRV_0000")
    
    # 3. Claim Details
    start = time.time()
    res = client.get(f"/claims/{claim_id}", headers=headers)
    t_detail = time.time() - start
    print(f"Claim Details (/claims/{claim_id}): {t_detail:.4f} s")
    
    # 4. Procedure Validation
    start = time.time()
    res = client.get(f"/claims/{claim_id}/procedure-validation", headers=headers)
    t_proc = time.time() - start
    print(f"Procedure Validation (/claims/{claim_id}/procedure-validation): {t_proc:.4f} s")
    
    # 5. Provider Profile
    start = time.time()
    res = client.get(f"/providers/{provider_id}/profile", headers=headers)
    t_prov = time.time() - start
    print(f"Provider Profile (/providers/{provider_id}/profile): {t_prov:.4f} s")

if __name__ == "__main__":
    run_benchmark()
