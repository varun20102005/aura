from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.core import User, ProviderRiskProfile
from ..routers.auth import require_role

router = APIRouter(prefix="", tags=["providers"])

@router.get("/providers/{provider_id}/risk-profile")
def get_provider_risk(provider_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_role(["Admin", "Auditor", "Investigator", "Supervisor"]))):
    profile = db.query(ProviderRiskProfile).filter_by(provider_id=provider_id).first()
    if not profile:
        return {"status": "INSUFFICIENT_HISTORY"}
        
    return {
        "provider_id": profile.provider_id,
        "rolling_risk_score": profile.rolling_risk_score,
        "verified_outcomes_count": profile.verified_outcomes_count,
        "last_computed_at": profile.last_computed_at,
        "status": "AVAILABLE"
    }

@router.get("/admin/providers/risk-profiles")
def list_risk_profiles(db: Session = Depends(get_db), current_user: User = Depends(require_role(["Admin"]))):
    profiles = db.query(ProviderRiskProfile).order_by(ProviderRiskProfile.rolling_risk_score.desc()).all()
    
    return [
        {
            "provider_id": p.provider_id,
            "rolling_risk_score": p.rolling_risk_score,
            "verified_outcomes_count": p.verified_outcomes_count,
            "last_computed_at": p.last_computed_at
        } for p in profiles
    ]
