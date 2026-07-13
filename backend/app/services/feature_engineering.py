import logging
import pandas as pd
from sqlalchemy.orm import Session
from ..models.core import Claim, ClaimDocument
from .data_validation import run_data_validation
from .validation_service import run_procedure_validation
from .duplicate_service import run_duplicate_detection
from .benchmark_service import get_claim_benchmark_features
from .risk_service import get_claim_provider_features

logger = logging.getLogger(__name__)

def build_consolidated_features(db: Session, claim_id: int):
    """
    Part 6: Feature Engineering Engine
    Executes all pre-ML engines and merges their outputs into a single feature vector.
    """
    claim = db.query(Claim).filter_by(id=claim_id).first()
    if not claim:
        return {}

    # 1. OCR Data Validation & Cleaning Features
    validation_report = run_data_validation(db, claim_id) or {}
    
    # 2. Procedure Validation Features
    procedure_features = run_procedure_validation(db, claim_id)
    
    # 3. Duplicate Detection Features
    duplicate_features = run_duplicate_detection(db, claim_id)
    
    # 4. Cost Benchmark Features
    benchmark_features = get_claim_benchmark_features(db, claim_id)
    
    # 5. Provider Risk Features
    provider_features = get_claim_provider_features(db, claim_id)
    
    # Base claim features
    base_features = {
        "billed_amount": claim.billed_amount or 0.0,
        "procedure_code": claim.procedure_code
    }
    
    # Merge all dictionaries
    consolidated_features = {
        **base_features,
        **procedure_features,
        **duplicate_features,
        **benchmark_features,
        **provider_features
    }
    
    logger.info(f"Consolidated features built for claim {claim_id}: {list(consolidated_features.keys())}")
    return consolidated_features
