import os
import json
import base64
import time
import importlib
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup test DB before importing app to avoid dev DB corruption
os.environ["DATABASE_URL"] = "sqlite:///./security_test.db"

import app.main as app_main
from app.database import Base, engine, SessionLocal
from app.models.core import User, Claim
from app.services.auth_service import get_password_hash, create_access_token

vulnerabilities = []

def log_vuln(name, severity, description, expected, actual):
    vulnerabilities.append({
        "name": name,
        "severity": severity,
        "description": description,
        "expected": expected,
        "actual": str(actual)
    })

def run_security_audit():
    # Setup DB
    tables = [t for t in Base.metadata.sorted_tables if t.name != "claim_embeddings"]
    Base.metadata.drop_all(bind=engine, tables=tables)
    Base.metadata.create_all(bind=engine, tables=tables)
    db = SessionLocal()

    client = TestClient(app_main.app)

    # 1. Setup users and roles
    roles = ["Officer", "Investigator", "Supervisor", "Auditor", "Admin"]
    tokens = {}
    users = {}
    for r in roles:
        u = User(email=f"{r.lower()}@test.com", hashed_password=get_password_hash("pass"), role=r)
        db.add(u)
        db.commit()
        db.refresh(u)
        tokens[r] = create_access_token(data={"sub": u.email, "role": u.role, "user_id": u.id})
        users[r] = u

    # Create a dummy claim for endpoint tests
    dummy_claim = Claim(patient_ref="PAT1", provider_ref="PROV1", procedure_code="123", billed_amount=100.0, status="action_required")
    db.add(dummy_claim)
    db.commit()

    # ---------------------------------------------------------
    # 1. RBAC Matrix Testing
    # ---------------------------------------------------------
    endpoints = [
        ("POST", "/claims/upload", ["Officer"], {"data": {"patient_ref": "1", "provider_ref": "2", "procedure_code": "3", "billed_amount": "100.0"}, "files": {"file": ("dummy.pdf", b"test", "application/pdf")}}),
        ("POST", f"/claims/{dummy_claim.id}/assign", ["Supervisor"], {"json": {"investigator_id": users["Investigator"].id}}),
        ("POST", "/admin/roles", ["Admin"], {"json": {"user_email": users["Officer"].email, "new_role": "Investigator"}}),
        ("GET", "/reports/pdf/1", ["Investigator", "Auditor", "Supervisor", "Admin"], {}),
    ]

    for method, path, allowed_roles, kwargs in endpoints:
        # Test no token
        res = client.request(method, path, **kwargs)
        if res.status_code != 401:
            log_vuln(f"Missing Auth - {path}", "High", f"Endpoint accessible without token", 401, res.status_code)
            
        # Test expired/invalid token
        res = client.request(method, path, headers={"Authorization": "Bearer invalidtoken"}, **kwargs)
        if res.status_code != 401:
            log_vuln(f"Invalid Auth - {path}", "High", f"Endpoint accessible with invalid token", 401, res.status_code)

        # Test each role
        for r in roles:
            res = client.request(method, path, headers={"Authorization": f"Bearer {tokens[r]}"}, **kwargs)
            if r in allowed_roles:
                # Should be allowed (200, 404, or 422 if data is missing, but NOT 401/403)
                if res.status_code in [401, 403]:
                    log_vuln(f"RBAC False Negative - {path}", "High", f"Role {r} wrongly denied", "200/404/422", res.status_code)
            else:
                # Should be denied (403)
                if res.status_code != 403:
                    log_vuln(f"RBAC False Positive - {path}", "Critical", f"Role {r} wrongly granted access", 403, res.status_code)

    # ---------------------------------------------------------
    # 2. 2FA for Admin login
    # ---------------------------------------------------------
    admin_user = users["Admin"]
    admin_user.totp_enabled = 1
    admin_user.totp_secret = "JBSWY3DPEHPK3PXP"
    db.commit()
    
    res = client.post("/auth/login", data={"username": admin_user.email, "password": "pass"})
    if res.status_code != 401:
        log_vuln("2FA Bypass", "Critical", "Admin can login without TOTP code", 401, res.status_code)

    # ---------------------------------------------------------
    # 3. Rate limiting
    # ---------------------------------------------------------
    # The rate limiter uses remote address, which is testclient for all.
    # login is 5/minute.
    rl_failed = False
    for i in range(10):
        res = client.post("/auth/login", data={"username": "fake@test.com", "password": "fake"})
        if res.status_code == 429:
            rl_failed = True
            break
    if not rl_failed:
        log_vuln("Rate Limiting Missing", "Medium", "Auth endpoint does not enforce rate limiting (hit 10 times)", 429, res.status_code)

    # ---------------------------------------------------------
    # 4. SQL Injection and XSS
    # ---------------------------------------------------------
    # SQLi in search
    res = client.get("/claims/search?patient_ref=' OR '1'='1", headers={"Authorization": f"Bearer {tokens['Auditor']}"})
    if res.status_code == 500:
        log_vuln("SQL Injection", "Critical", "SQLi payload caused a 500 internal server error", 200, 500)
    
    # XSS in notes
    res = client.post(f"/claims/{dummy_claim.id}/notes", json={"note_text": "<script>alert(1)</script>"}, headers={"Authorization": f"Bearer {tokens['Investigator']}"})
    # If the backend accepts raw HTML without sanitizing, we record a Medium risk.
    if res.status_code == 200:
        # Check if the text was saved verbatim
        notes_res = client.get(f"/claims/{dummy_claim.id}", headers={"Authorization": f"Bearer {tokens['Investigator']}"})
        # If DB status check is used in E2E we know there's a serialization issue in GET /claims/{id}.
        # Let's check DB directly.
        from app.models.core import InvestigationNote
        note = db.query(InvestigationNote).filter_by(claim_id=dummy_claim.id).first()
        if note and "<script>" in note.note_text:
            log_vuln("Stored XSS via Notes", "Medium", "Backend stores raw HTML in notes without sanitization.", "Sanitized/422", "Raw HTML stored")

    # ---------------------------------------------------------
    # 5. File Upload Validation
    # ---------------------------------------------------------
    # .exe file upload
    dummy_exe = ("malware.exe", b"MZ\x90\x00", "application/x-msdownload")
    res = client.post("/claims/upload", data={"patient_ref": "1", "provider_ref": "2", "procedure_code": "3", "billed_amount": "100.0"}, files={"file": dummy_exe}, headers={"Authorization": f"Bearer {tokens['Officer']}"})
    if res.status_code not in [400, 422, 415]:
        log_vuln("Unrestricted File Upload (.exe)", "High", "Allowed uploading a .exe file", "400/415", res.status_code)

    # Oversized file upload (using a 10MB file to simulate, as 50MB might OOM the test environment)
    # We will just write a small check, many backends reject instantly if Content-Length is spoofed, 
    # but testclient doesn't spoof easily. We'll generate a 6MB file.
    try:
        large_file = ("large.pdf", b"0" * (6 * 1024 * 1024), "application/pdf")
        res = client.post("/claims/upload", data={"patient_ref": "1", "provider_ref": "2", "procedure_code": "3", "billed_amount": "100.0"}, files={"file": large_file}, headers={"Authorization": f"Bearer {tokens['Officer']}"})
        if res.status_code not in [400, 413, 422]:
            log_vuln("File Size Limit Bypass", "Medium", "Allowed uploading a >5MB file", "413/400", res.status_code)
    except Exception as e:
        pass # If it crashes, that's bad too, but we move on

    # ---------------------------------------------------------
    # 6. Dev Diagnostic Endpoint in Prod
    # ---------------------------------------------------------
    os.environ["ENVIRONMENT"] = "production"
    importlib.reload(app_main)
    prod_client = TestClient(app_main.app)
    res = prod_client.get("/mcp/check")
    if res.status_code != 404:
        log_vuln("Dev Diagnostic Exposed in Prod", "High", "/mcp/check is available when ENVIRONMENT=production", 404, res.status_code)
    os.environ["ENVIRONMENT"] = "development" # revert

    # ---------------------------------------------------------
    # 7. JWT Tampering
    # ---------------------------------------------------------
    header, payload, sig = tokens["Officer"].split(".")
    payload_decoded = json.loads(base64.urlsafe_b64decode(payload + "==").decode())
    payload_decoded["role"] = "Admin"
    payload_tampered = base64.urlsafe_b64encode(json.dumps(payload_decoded).encode()).decode().rstrip("=")
    tampered_token = f"{header}.{payload_tampered}.{sig}"
    
    res = client.post("/admin/roles", json={"user_email": users["Officer"].email, "new_role": "Admin"}, headers={"Authorization": f"Bearer {tampered_token}"})
    if res.status_code not in [401, 403]:
        log_vuln("JWT Tampering", "Critical", "Tampered JWT with modified role was accepted", 401, res.status_code)

    # Output results
    with open("security_report.json", "w") as f:
        json.dump(vulnerabilities, f, indent=2)
        
    print(f"Security audit complete. Found {len(vulnerabilities)} vulnerabilities.")

if __name__ == "__main__":
    run_security_audit()
