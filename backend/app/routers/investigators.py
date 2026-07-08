from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_

from ..database import get_db
from ..models.core import CaseAssignment, Claim, User
from ..routers.auth import require_role, get_current_user

router = APIRouter(prefix="/investigators", tags=["investigators"])

@router.get("/{id}/workload")
def get_workload(id: int, db: Session = Depends(get_db), current_user: User = Depends(require_role(["Admin", "Supervisor", "Investigator"]))):
    # Only allow self-view unless admin/supervisor
    if current_user.role == "Investigator" and current_user.id != id:
        raise HTTPException(status_code=403, detail="Can only view own workload")
        
    investigator = db.query(User).filter_by(id=id).first()
    if not investigator:
        raise HTTPException(status_code=404, detail="Investigator not found")
        
    # Get all active assignments ordered by assigned_at desc
    assignments = db.query(CaseAssignment).join(Claim).filter(
        CaseAssignment.investigator_id == id,
        or_(Claim.status == "processing", Claim.status == "action_required")
    ).order_by(CaseAssignment.assigned_at.desc()).all()
    
    seen_claims = set()
    unique_assignments = []
    for a in assignments:
        if a.claim_id not in seen_claims:
            seen_claims.add(a.claim_id)
            unique_assignments.append(a)
            
    # Reverse to restore original chronological ordering if preferred, or keep descending. Let's keep descending (newest first) or reverse it.
    # The original returned list was arbitrary, let's return newest first.
    return [
        {
            "id": a.claim.id,
            "patient_ref": a.claim.patient_ref,
            "provider_ref": a.claim.provider_ref,
            "status": a.claim.status,
            "assignment": {
                "assignment_id": a.id,
                "assigned_at": a.assigned_at,
                "sla_due_at": a.sla_due_at
            }
        } for a in unique_assignments
    ]
