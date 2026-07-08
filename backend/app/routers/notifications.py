from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from ..database import get_db
from ..models.core import Notification, User
from ..routers.auth import require_role

router = APIRouter(prefix="/notifications", tags=["notifications"])

@router.get("")
def get_notifications(db: Session = Depends(get_db), current_user: User = Depends(require_role(["Admin", "Investigator", "Auditor", "Supervisor", "Officer"]))):
    # Returns all notifications for current user, descending
    notifs = db.query(Notification).filter_by(recipient_id=current_user.id).order_by(Notification.created_at.desc()).all()
    return notifs

@router.post("/{notif_id}/read")
def mark_read(notif_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_role(["Admin", "Investigator", "Auditor", "Supervisor", "Officer"]))):
    notif = db.query(Notification).filter_by(id=notif_id, recipient_id=current_user.id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
        
    notif.read_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Marked as read"}
