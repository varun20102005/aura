from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone
import logging
from ..models.core import Claim, ProviderRiskProfile

logger = logging.getLogger(__name__)

def utcnow():
    return datetime.now(timezone.utc)

def compute_provider_risk(db: Session, provider_id: str, as_of_time: datetime = None):
    """
    Computes the risk profile for a provider using ONLY claims where the outcome 
    was finalized BEFORE `as_of_time`. This guarantees no leakage of future outcomes
    when historically scoring a claim.
    """
    if as_of_time is None:
        as_of_time = utcnow()

    # Get claims for this provider that have a final outcome (approved or denied)
    # AND were updated (finalized) strictly BEFORE as_of_time.
    claims_query = db.query(Claim.status, func.count(Claim.id)).filter(
        Claim.provider_ref == provider_id,
        Claim.status.in_(["approved", "denied"]),
        Claim.updated_at < as_of_time
    ).group_by(Claim.status).all()

    status_counts = dict(claims_query)
    upheld = status_counts.get("denied", 0) # fraud upheld -> risk increases
    overturned = status_counts.get("approved", 0) # fraud overturned -> risk decreases
    
    total = upheld + overturned
    risk_score = 0.0
    if total > 0:
        # Simple ratio of fraud upheld to total verified outcomes
        risk_score = float(upheld) / float(total)

    return risk_score, total

def update_all_provider_risk_profiles(db: Session):
    """
    Scheduled job that iterates through all providers with final outcomes 
    and updates their ProviderRiskProfile to the current time.
    """
    providers = db.query(Claim.provider_ref).filter(
        Claim.status.in_(["approved", "denied"])
    ).distinct().all()

    count = 0
    now = utcnow()
    for (provider_id,) in providers:
        if not provider_id: continue
        
        score, total_outcomes = compute_provider_risk(db, provider_id, as_of_time=now)
        
        profile = db.query(ProviderRiskProfile).filter_by(provider_id=provider_id).first()
        if not profile:
            profile = ProviderRiskProfile(provider_id=provider_id)
            db.add(profile)
            
        profile.rolling_risk_score = score
        profile.verified_outcomes_count = total_outcomes
        profile.last_computed_at = now
        count += 1
        
    db.commit()
    logger.info(f"Updated {count} provider risk profiles.")
