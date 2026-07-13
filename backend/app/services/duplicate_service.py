import logging
import rapidfuzz
from sqlalchemy.orm import Session
from ..models.core import Claim, DuplicateMatch
from datetime import datetime

logger = logging.getLogger(__name__)

def run_duplicate_detection(db: Session, claim_id: int):
    claim = db.query(Claim).filter_by(id=claim_id).first()
    if not claim:
        return {}

    features = {
        "duplicate_similarity": 0.0,
        "duplicate_count": 0,
        "duplicate_recent": 0,
        "duplicate_same_provider": 0,
        "duplicate_same_patient": 0
    }

    try:
        past_claims = db.query(Claim).filter(Claim.id != claim_id).limit(100).all()
        matches = []
        for pc in past_claims:
            if claim.procedure_code == pc.procedure_code:
                sim = rapidfuzz.fuzz.ratio(str(claim.billed_amount), str(pc.billed_amount))
                if sim > 95:
                    db.add(DuplicateMatch(claim_id=claim_id, matched_claim_id=pc.id, similarity_score=sim, method="fuzzy"))
                    matches.append(pc)
                    features["duplicate_similarity"] = max(features["duplicate_similarity"], sim)
                    
        db.commit()
        
        features["duplicate_count"] = len(matches)
        
        for m in matches:
            # Check if it was recent (within 7 days)
            if (claim.created_at - m.created_at).days <= 7:
                features["duplicate_recent"] = 1
            if m.provider_ref == claim.provider_ref:
                features["duplicate_same_provider"] = 1
            if m.patient_ref == claim.patient_ref:
                features["duplicate_same_patient"] = 1

    except Exception as e:
        logger.error(f"Duplicate step failed: {e}")

    return features
