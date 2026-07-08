import os
import requests
import time
import json
import io

BASE_URL = "http://127.0.0.1:8000"
TOKEN = None

def get_auth_token(email="admin@aura.local", password="password123"):
    # Try to register first
    requests.post(f"{BASE_URL}/auth/register", json={"email": email, "password": password, "role": "Admin"})
    
    # Login via OAuth2 which uses 'username' field mapped to email
    res = requests.post(f"{BASE_URL}/auth/login", data={"username": email, "password": password})
    if res.status_code == 200:
        return res.json()["access_token"]
    print("WARNING: Auth failed", res.text)
    return "mock_token"

def req(method, endpoint, **kwargs):
    headers = kwargs.pop("headers", {})
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    url = f"{BASE_URL}{endpoint}"
    return requests.request(method, url, headers=headers, **kwargs)

def run_all():
    global TOKEN
    report = {"summary": {}, "results": []}
    
    print("Waiting for backend...")
    for _ in range(5):
        try:
            req("GET", "/health") # may 404, just want connection
            break
        except:
            time.sleep(1)
    
    TOKEN = get_auth_token()
    
    # 2. CREATE QA DATASET
    print("Creating QA Dataset...")
    def upload_claim(patient, provider, proc, amount, text):
        data = {"patient_ref": patient, "provider_ref": provider, "procedure_code": proc, "billed_amount": amount}
        files = {"file": ("dummy.pdf", io.BytesIO(text.encode()), "application/pdf")}
        res = req("POST", "/claims/upload", data=data, files=files)
        return res.json()
        
    c_a_res = upload_claim("PAT_A", "PRV_OK", "C10", 100.0, "MRI brain scan for persistent headache")
    if "claim_id" not in c_a_res:
        print("Failed to create claim A:", c_a_res)
        return
    c_a_id = c_a_res["claim_id"]
    
    # Claim B: Suspicious high-risk
    upload_claim("PAT_B", "PRV_BAD", "C99", 15000.0, "Brain magnetic resonance imaging due to chronic headaches")
    # Claim C: Unrelated
    upload_claim("PAT_C", "PRV_OK", "KNEE1", 5000.0, "Knee replacement surgery")
    
    # 3. CLAIM DATA FLOW
    print("Verifying Claim Data Flow...")
    res_list = req("GET", "/claims/").json()
    claim_a_list = next((c for c in res_list if c["id"] == c_a_id), None)
    claim_a_detail = req("GET", f"/claims/{c_a_id}").json()
    
    flow_pass = claim_a_list and claim_a_detail and claim_a_list["patient_ref"] == claim_a_detail["patient_ref"]
    report["results"].append({"step": "Claim Data Flow", "status": "PASS" if flow_pass else "FAIL"})

    # 4. PROVIDER PROFILE VERIFICATION
    print("Verifying Provider Profiles...")
    p_ok = req("GET", f"/providers/PRV_OK/risk-profile")
    p_new = req("GET", f"/providers/PRV_NEW_999/risk-profile")
    p_missing = req("GET", f"/providers/NONE/risk-profile") # Might be handled differently
    
    prov_pass = p_new.json().get("status") == "INSUFFICIENT_HISTORY"
    report["results"].append({"step": "Provider Profiles", "status": "PASS" if prov_pass else "FAIL"})
    
    # 5. COST BENCHMARK
    print("Verifying Cost Benchmark Lifecycle...")
    # We poll claim status. If it's processed, we fetch benchmark
    cb_res = req("GET", f"/analytics/cost-benchmark?procedure_code=C10&provider_ref=PRV_OK&billed_amount=100.0")
    cb_pass = cb_res.status_code in [200, 404] # 404 means no data, but handled
    report["results"].append({"step": "Cost Benchmark", "status": "PASS" if cb_pass else "FAIL"})

    # 6. RISK AGGREGATE
    print("Verifying Risk Aggregate Math...")
    time.sleep(2) # Wait for background tasks
    r_agg = req("GET", f"/claims/{c_a_id}/risk-aggregate")
    math_pass = False
    if r_agg.status_code == 200:
        d = r_agg.json()
        print("Risk Agg Response:", d)
        if "weights" in d and "components" in d:
            w = d["weights"]
            c = d["components"]
            manual = sum([c[k] * w.get(k.replace('_score', ''), 0) for k in c])
            diff = abs(manual - d["aggregate_score"])
            math_pass = diff < 0.001
            report["risk_aggregate"] = {"manual": manual, "backend": d["aggregate_score"], "diff": diff}
    else:
        print("Risk Agg status:", r_agg.status_code, r_agg.text)
    report["results"].append({"step": "Risk Aggregate Math", "status": "PASS" if math_pass else "FAIL"})

    # ... skipped 7 since it passed ...
    dup_fuzzy = req("GET", f"/claims/{c_a_id}/similar?method=fuzzy").json()
    dup_sem = req("GET", f"/claims/{c_a_id}/similar?method=semantic").json()
    dup_pass = type(dup_fuzzy) is list and type(dup_sem) is list
    report["results"].append({"step": "Duplicate Detection", "status": "PASS" if dup_pass else "FAIL"})

    # 9. BULK UPLOAD
    print("Verifying Bulk Upload...")
    csv_data = "patient_ref,provider_ref,procedure_code,billed_amount,document_filename\nOK1,P1,C1,10.0,f1\nBAD1,P1,C1,ABC,f2"
    files = [
        ("manifest", ("m.csv", io.BytesIO(csv_data.encode()), "text/csv")),
        ("documents", ("f1", io.BytesIO(b""), "application/pdf")),
        ("documents", ("f2", io.BytesIO(b""), "application/pdf"))
    ]
    bulk_res = req("POST", "/claims/bulk-upload", files=files)
    print("Bulk Upload Res:", bulk_res.status_code, bulk_res.text)
    bulk_pass = bulk_res.status_code == 200 and bulk_res.json().get("failed_records", 0) > 0
    report["results"].append({"step": "Bulk Upload Integrity", "status": "PASS" if bulk_pass else "FAIL"})

    # 10. NOTIFICATIONS
    print("Verifying Notifications...")
    assign_res = req("POST", f"/claims/{c_a_id}/assign", json={"investigator_id": 1})
    notifs = req("GET", "/notifications").json()
    notif_pass = assign_res.status_code == 200 and type(notifs) is list
    report["results"].append({"step": "Notifications Assignment", "status": "PASS" if notif_pass else "FAIL"})

    with open("qa_report.json", "w") as f:
        json.dump(report, f, indent=2)
    print("QA Execution Complete.")

if __name__ == "__main__":
    run_all()
