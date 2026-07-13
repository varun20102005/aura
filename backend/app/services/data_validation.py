import re
import json
import logging
from sqlalchemy.orm import Session
from datetime import datetime
from ..models.core import Claim, ClaimDocument

logger = logging.getLogger(__name__)

def normalize_currency(amount_str):
    try:
        # Remove anything that isn't a digit or a period
        clean_str = re.sub(r'[^\d\.]', '', str(amount_str))
        if clean_str:
            return float(clean_str)
    except:
        pass
    return None

def normalize_date(date_str):
    """
    Attempt to extract and normalize common date formats from text.
    """
    # Simple regex for mm/dd/yyyy or yyyy-mm-dd
    match = re.search(r'(\d{2,4}[-/]\d{1,2}[-/]\d{2,4})', str(date_str))
    if match:
        return match.group(1)
    return None

def run_data_validation(db: Session, claim_id: int):
    """
    Part 1: Data Validation & Cleaning Engine
    Executes immediately after OCR to validate OCR outputs, normalize fields, 
    detect missing values, and check for impossible parameters.
    """
    claim = db.query(Claim).filter_by(id=claim_id).first()
    if not claim:
        return None
        
    doc = db.query(ClaimDocument).filter_by(claim_id=claim.id).first()
    if not doc:
        return None

    ocr_text = doc.ocr_text or ""
    
    report = {
        "status": "passed",
        "normalized_fields": {},
        "missing_fields": [],
        "warnings": [],
        "errors": [],
        "duplicate_lines_detected": 0
    }

    # Normalize basic strings
    report["normalized_fields"]["provider_ref_normalized"] = str(claim.provider_ref).strip().upper() if claim.provider_ref else None
    report["normalized_fields"]["patient_ref_normalized"] = str(claim.patient_ref).strip().upper() if claim.patient_ref else None
    report["normalized_fields"]["procedure_code_normalized"] = str(claim.procedure_code).strip().upper() if claim.procedure_code else None
    
    # Currency normalization check
    clean_amount = normalize_currency(claim.billed_amount)
    if clean_amount is None or clean_amount <= 0:
        report["errors"].append("Invalid or negative billed amount.")
        report["status"] = "failed"
    else:
        report["normalized_fields"]["billed_amount_normalized"] = clean_amount

    # Mandatory field check
    mandatory = ["provider_ref", "patient_ref", "procedure_code", "billed_amount"]
    for field in mandatory:
        if not getattr(claim, field):
            report["missing_fields"].append(field)
            report["status"] = "failed"

    # OCR text checks
    lines = ocr_text.split('\n')
    unique_lines = set()
    dup_lines = 0
    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue
        if line_clean in unique_lines:
            dup_lines += 1
        else:
            unique_lines.add(line_clean)
            
    report["duplicate_lines_detected"] = dup_lines
    if dup_lines > 5:
        report["warnings"].append(f"High number of duplicate OCR lines detected ({dup_lines}). Possible scan artifact.")

    # Impossible dates/age logic (Mock implementation based on OCR text parsing)
    if "1899" in ocr_text or "1900" in ocr_text:
         report["warnings"].append("Extremely old date detected in OCR. Check patient age.")

    # Save the report
    doc.validation_report = report
    db.commit()
    
    logger.info(f"Data validation complete for claim {claim_id}. Status: {report['status']}")
    return report
