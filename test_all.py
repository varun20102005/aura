import subprocess
import os
import sys
import re

def run_command(cmd, cwd, env=None):
    print(f"Running: {cmd} in {cwd}")
    process = subprocess.Popen(
        cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, shell=True, encoding="utf-8"
    )
    
    output = ""
    for line in process.stdout:
        print(line.encode(sys.stdout.encoding, errors='replace').decode(sys.stdout.encoding), end="")
        output += line
        
    process.wait()
    return process.returncode, output

def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(root_dir, "backend")
    frontend_dir = os.path.join(root_dir, "frontend")
    
    overall_success = True
    results = {}
    
    # 1. Backend Pytest
    print("\n--- Running Backend Tests (pytest) ---")
    env = os.environ.copy()
    env["DATABASE_URL"] = "sqlite:///./test_all.db"
    
    code_be, out_be = run_command("python -m pytest --cov=app tests/", backend_dir, env=env)
    
    # Parse pytest coverage
    cov_match = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", out_be)
    be_cov = f"{cov_match.group(1)}%" if cov_match else "N/A"
    
    results["Backend Unit & Integration"] = {
        "status": "PASS" if code_be == 0 else "FAIL",
        "coverage": be_cov
    }
    if code_be != 0: overall_success = False
    
    # 2. Backend Security Script
    print("\n--- Running Backend Security Audit ---")
    code_sec, out_sec = run_command("python -m tests.security_audit_script", backend_dir, env=env)
    
    if "Security audit complete" in out_sec and code_sec == 0:
        results["Backend Security Audit"] = {"status": "PASS", "coverage": "N/A"}
    else:
        results["Backend Security Audit"] = {"status": "FAIL", "coverage": "N/A"}
        overall_success = False
        
    # 3. Frontend Vitest
    print("\n--- Running Frontend Component Tests (vitest) ---")
    code_fe, out_fe = run_command("cmd /c npm run test:coverage", frontend_dir)
    
    # Parse vitest coverage (usually the first 'All files' line, first number)
    fe_cov_match = re.search(r"All files\s+\|\s+([\d.]+)", out_fe)
    fe_cov = f"{fe_cov_match.group(1)}%" if fe_cov_match else "N/A"
    
    results["Frontend Component & E2E"] = {
        "status": "PASS" if code_fe == 0 else "FAIL",
        "coverage": fe_cov
    }
    if code_fe != 0: overall_success = False
    
    # --- Summary ---
    print("\n========================================")
    print("      UNIFIED QA PIPELINE SUMMARY")
    print("========================================")
    for name, data in results.items():
        print(f"{name:.<30} {data['status']:<6} (Coverage: {data['coverage']})")
        
    print("\nOVERALL STATUS: " + ("PASS" if overall_success else "FAIL"))
    
    if not overall_success:
        sys.exit(1)

if __name__ == "__main__":
    main()
