import os
import sys
import pandas as pd
import pytest

# Ensure scripts directory is reachable
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts/eval')))

from dataset_adapter import DatasetAdapter
from run_eval import run_evaluation

@pytest.fixture
def sample_csv(tmp_path):
    csv_file = tmp_path / "test_fraud_claims.csv"
    
    data = {
        "patient_id": ["P1", "P2", "P3"],
        "provider_id": ["PRV1", "PRV1", "PRV2"],
        "procedure_code": ["CPT1", "CPT2", "CPT1"],
        "billed_amount": [100.0, 2500.0, 50.0],
        "ocr_text": ["Normal visit", "Expensive surgery with missing info", "Routine checkup"],
        "is_fraud": [0, 1, 0]
    }
    df = pd.DataFrame(data)
    df.to_csv(csv_file, index=False)
    return str(csv_file)

def test_dataset_adapter(sample_csv):
    adapter = DatasetAdapter(sample_csv)
    claims = adapter.load_data()
    
    assert len(claims) == 3
    
    # Check mapping
    c1 = claims[0]
    assert c1["patient_ref"] == "P1"
    assert c1["provider_ref"] == "PRV1"
    assert c1["procedure_code"] == "CPT1"
    assert c1["billed_amount"] == 100.0
    assert c1["status"] == "pending"
    assert c1["_eval_true_label"] == 0
    assert c1["_eval_ocr_text"] == "Normal visit"

def test_run_evaluation_end_to_end(sample_csv):
    # This should run perfectly without crashing and produce a markdown file.
    # It tests the complete separation since run_evaluation builds its own memory DB.
    run_evaluation(sample_csv)
    
    # Assert report was created
    assert os.path.exists("evaluation_report.md")
    
    with open("evaluation_report.md", "r") as f:
        content = f.read()
        assert "AURA Evaluation Report" in content
        assert "Records**: 3" in content
        assert "AUC-ROC" in content
        
    # Cleanup
    if os.path.exists("evaluation_report.md"):
        os.remove("evaluation_report.md")
