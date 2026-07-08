import pandas as pd
from typing import List, Dict, Any

class DatasetAdapter:
    def __init__(self, file_path: str):
        self.file_path = file_path
        
    def load_data(self) -> List[Dict[str, Any]]:
        """
        Reads a generic CSV dataset and maps it to AURA Claim fields.
        Expected CSV columns:
        - claim_id (optional)
        - patient_id
        - provider_id
        - procedure_code
        - billed_amount
        - ocr_text (optional)
        - is_fraud (0 or 1, for evaluation labels)
        """
        df = pd.read_csv(self.file_path)
        
        claims = []
        for idx, row in df.iterrows():
            claim = {
                "patient_ref": str(row.get("patient_id", f"PAT_{idx}")),
                "provider_ref": str(row.get("provider_id", f"PRV_{idx}")),
                "procedure_code": str(row.get("procedure_code", "UNKNOWN")),
                "billed_amount": float(row.get("billed_amount", 0.0)),
                "status": "pending",
                # Eval specific fields not strictly in Claim model, but useful for mapping
                "_eval_true_label": int(row.get("is_fraud", 0)),
                "_eval_ocr_text": str(row.get("ocr_text", ""))
            }
            claims.append(claim)
            
        return claims
