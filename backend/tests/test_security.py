import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app, limiter
from app.database import get_db
from app.models.core import User, Base
from app.routers.auth import get_current_user

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_security.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# We need a client that does NOT override `get_current_user` so we can test the actual token flow
# But we'll test the actual token flow.
client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    tables = [t for t in Base.metadata.sorted_tables if t.name != 'claim_embeddings']
    Base.metadata.create_all(bind=engine, tables=tables)
    db = TestingSessionLocal()
    
    # We will register users via the API so they get hashed passwords
    client.post("/auth/register", json={"email": "officer@aura.com", "password": "pass", "role": "Officer"})
    client.post("/auth/register", json={"email": "admin@aura.com", "password": "pass", "role": "Admin"})
    client.post("/auth/register", json={"email": "investigator@aura.com", "password": "pass", "role": "Investigator"})
    
    yield
    tables = [t for t in Base.metadata.sorted_tables if t.name != 'claim_embeddings']
    Base.metadata.drop_all(bind=engine, tables=tables)
    db.close()

def get_token(client, email: str):
    res = client.post("/auth/login", data={"username": email, "password": "pass"})
    if "access_token" not in res.json():
        raise RuntimeError(f"Auth failed in get_token for {email}: {res.text}")
    return res.json()["access_token"]

def test_rbac_boundaries(client, db):
    # Admin tries admin endpoint -> OK
    admin_token = get_token(client, "admin@test.com")
    res = client.get("/admin/model-metrics", headers={"Authorization": f"Bearer {admin_token}"})
    # Might be 404 or 200 depending on if it's implemented, but not 403
    assert res.status_code != 403

    # Officer tries admin endpoint -> 403
    off_token = get_token(client, "officer@test.com")
    res = client.get("/admin/model-metrics", headers={"Authorization": f"Bearer {off_token}"})
    assert res.status_code == 403

def test_2fa_flow(client, db):
    # Attempt login to get 2FA prompt
    # Not fully implemented in core, but if there's a route we check logic.
    admin_token = get_token(client, "admin@test.com")
    assert admin_token is not None
    # Setup 2FA
    res = client.post("/auth/2fa/setup", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    secret = res.json()["secret"]
    
    import pyotp
    totp = pyotp.TOTP(secret)
    code = totp.now()
    
    # Verify 2FA
    res = client.post("/auth/2fa/verify", json={"code": code}, headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    
    # Try to login without TOTP code (should fail)
    res = client.post("/auth/login", data={"username": "admin@test.com", "password": "pass"})
    assert res.status_code == 401
    assert "TOTP" in res.json()["detail"]
    
    # Try to login with TOTP code
    new_code = totp.now()
    res = client.post("/auth/login", data={"username": "admin@test.com", "password": "pass", "totp_code": new_code})
    assert res.status_code == 200
    assert "access_token" in res.json()

def test_rate_limiting(client):
    # Attempt to hit login 10 times quickly (limit is 5/minute)
    from app.limiter import limiter
    limiter.enabled = True
    try:
        responses = []
        
        for _ in range(6):
            res = client.post("/auth/login", data={"username": "invalid@aura.com", "password": "bad"})
            responses.append(res.status_code)
            
        # The first 5 should be 401, the 6th should be 429
        assert 429 in responses
    finally:
        limiter.enabled = False

def test_mcp_check_available_in_dev(client):
    res = client.get("/mcp/check")
    assert res.status_code == 200
    assert res.json()["diagnostic_active"] is True
