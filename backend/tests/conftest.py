import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
# Import all models to ensure they are registered with Base metadata
from app.models.core import *
from app.services.auth_service import get_password_hash
from app.limiter import limiter

# Disable rate limiting for tests to prevent 429 errors on /auth/login
limiter.enabled = False

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="module")
def db():
    tables = [t for t in Base.metadata.sorted_tables if t.name != "claim_embeddings"]
    Base.metadata.create_all(bind=engine, tables=tables)
    db = TestingSessionLocal()
    
    # Create test users
    admin = User(email="admin@test.com", hashed_password=get_password_hash("pass"), role="Admin")
    officer = User(email="officer@test.com", hashed_password=get_password_hash("pass"), role="Officer")
    db.add(admin)
    db.add(officer)
    db.commit()
    
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine, tables=tables)

@pytest.fixture(scope="module")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    del app.dependency_overrides[get_db]

@pytest.fixture(scope="module")
def admin_token(client):
    response = client.post("/auth/login", data={"username": "admin@test.com", "password": "pass"})
    if "access_token" not in response.json():
        raise RuntimeError(f"Auth failed: {response.text}")
    return response.json()["access_token"]

@pytest.fixture(scope="module")
def officer_token(client):
    response = client.post("/auth/login", data={"username": "officer@test.com", "password": "pass"})
    if "access_token" not in response.json():
        raise RuntimeError(f"Auth failed: {response.text}")
    return response.json()["access_token"]
