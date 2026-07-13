import json
import os
import logging
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..models.core import Claim, ClaimDocument, ProcedureValidationFlag

logger = logging.getLogger(__name__)

import csv

# Load reference code list
REFERENCE_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'reference-codes', 'hcpcs_icd10.csv')
REFERENCE_CODES = {}
try:
    with open(REFERENCE_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = row['code']
            keywords = row['keywords'].split('|') if row['keywords'] else []
            REFERENCE_CODES[code] = {
                "type": row['type'],
                "description": row['description'],
                "keywords": keywords
            }
except Exception as e:
    logger.error(f"Failed to load reference codes from {REFERENCE_FILE}: {e}")

def check_invalid_code(db: Session, claim: Claim) -> ProcedureValidationFlag:
    code = claim.procedure_code
    if not code:
        return None
        
    if code not in REFERENCE_CODES:
        return ProcedureValidationFlag(
            claim_id=claim.id,
            code=code,
            flag_type="invalid_code",
            description=f"Procedure code '{code}' not found in reference list."
        )
    return None

def check_description_mismatch(db: Session, claim: Claim) -> ProcedureValidationFlag:
    code = claim.procedure_code
    if not code or code not in REFERENCE_CODES:
        return None
        
    doc = db.query(ClaimDocument).filter_by(claim_id=claim.id).first()
    if not doc or not doc.ocr_text:
        return None # Can't check without text
        
    keywords = REFERENCE_CODES[code].get("keywords", [])
    if not keywords:
        return None
        
    text_lower = doc.ocr_text.lower()
    
    # Lightweight semantic check: see if at least one keyword is present in OCR
    matched = [kw for kw in keywords if kw.lower() in text_lower]
    if len(matched) == 0:
        return ProcedureValidationFlag(
            claim_id=claim.id,
            code=code,
            flag_type="description_mismatch",
            description=f"None of the expected keywords for code '{code}' were found in the OCR document."
        )
    return None

def check_rare_combination(db: Session, claim: Claim) -> ProcedureValidationFlag:
    # Frequency-based flag for statistically rare code combinations
    # We check if this provider has billed this code historically
    # We use a 1% threshold or simply a count check. 
    # If the provider has > 10 historical claims but this code represents 0% of them (this is the first), flag it.
    code = claim.procedure_code
    provider = claim.provider_ref
    
    if not code or not provider:
        return None
        
    total_provider_claims = db.query(func.count(Claim.id)).filter_by(provider_ref=provider).scalar()
    
    # Needs a minimum history to establish a baseline
    if total_provider_claims > 10:
        provider_code_count = db.query(func.count(Claim.id)).filter_by(provider_ref=provider, procedure_code=code).scalar()
        
        # We include the current claim, so count will be at least 1.
        # If it's exactly 1 out of >10 claims, it's rare.
        if provider_code_count == 1:
             return ProcedureValidationFlag(
                claim_id=claim.id,
                code=code,
                flag_type="rare_combination",
                description=f"Statistically rare: Provider '{provider}' has billed this code for the first time out of {total_provider_claims} claims."
            )
    return None

def run_procedure_validation(db: Session, claim_id: int):
    claim = db.query(Claim).filter_by(id=claim_id).first()
    if not claim:
        return {}

    # Clear any existing flags for this claim to prevent duplicates on re-processing
    db.query(ProcedureValidationFlag).filter_by(claim_id=claim_id).delete()
    
    flags = []
    
    # Rule 1: Reference Validity
    f1 = check_invalid_code(db, claim)
    if f1: flags.append(f1)
    
    # Rule 2: Description consistency
    f2 = check_description_mismatch(db, claim)
    if f2: flags.append(f2)
    
    # Rule 3: Frequency / Rare combination
    f3 = check_rare_combination(db, claim)
    if f3: flags.append(f3)
    
    for flag in flags:
        db.add(flag)
    
    db.commit()
    logger.info(f"Procedure validation generated {len(flags)} flags for claim {claim_id}.")
    
    # Return structured ML features
    features = {
        "procedure_valid": 1 if not f1 else 0,
        "procedure_match_score": 1.0 if not f2 else 0.0, # Could be improved by partial match logic
        "procedure_confidence": 1.0 if not f1 and not f2 else 0.5,
        "rare_provider_combination": 1 if f3 else 0
    }
    
    return features
