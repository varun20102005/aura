import logging
from sqlalchemy.orm import Session
from ..models.core import Notification

logger = logging.getLogger(__name__)

import smtplib
from email.message import EmailMessage
from ..config import settings

def _send_email_mock(to_user_id: int, subject: str, body: str):
    """
    SMTP integration using Mailtrap (or other SMTP).
    """
    logger.info(f"Sending SMTP EMAIL to User {to_user_id}...")
    
    # We mock the recipient email based on the user id for now, 
    # since we don't have the user's email directly in this function payload.
    recipient_email = f"user{to_user_id}@aura.local"
    
    if not settings.SMTP_USER or not settings.SMTP_PASS:
        logger.warning(f"SMTP_USER or SMTP_PASS not set in config. Falling back to log: {subject}")
        return

    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg['Subject'] = subject
        msg['From'] = settings.SMTP_FROM
        msg['To'] = recipient_email

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.login(settings.SMTP_USER, settings.SMTP_PASS)
            server.send_message(msg)
        logger.info(f"Successfully sent email to {recipient_email}")
    except Exception as e:
        logger.error(f"Failed to send email to {recipient_email}: {e}")

def dispatch_notification(db: Session, recipient_id: int, notif_type: str, payload: dict):
    """
    Records a notification in the database and dispatches via email.
    """
    # 1. Save to DB
    notif = Notification(
        recipient_id=recipient_id,
        type=notif_type,
        payload=payload
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    
    # 2. Dispatch email based on type
    subject = f"AURA Alert: {notif_type}"
    body = f"You have a new {notif_type} notification.\nDetails: {payload}"
    
    if notif_type == "NEW_ASSIGNMENT":
        subject = f"New Claim Assignment: {payload.get('claim_id')}"
        body = f"You have been assigned to review Claim #{payload.get('claim_id')} by User #{payload.get('assigned_by')}."
    elif notif_type == "SLA_WARNING":
        subject = f"SLA At Risk for Claim {payload.get('claim_id')}"
        body = f"Your assignment on Claim #{payload.get('claim_id')} is at risk of breaching its SLA due at {payload.get('sla_due_at')}."
    
    _send_email_mock(recipient_id, subject, body)
    return notif

def notify_drift_breach(db: Session, model_id: int, metric: str, value: float, threshold: float):
    """
    Phase 9 integration for Phase 8 drift alerts.
    Dispatches to Admin users (we'll just use recipient_id=1 for the mock).
    """
    payload = {
        "model_id": model_id,
        "metric": metric,
        "value": value,
        "threshold": threshold,
        "message": f"DRIFT ALERT: {metric} value {value:.4f} > {threshold:.4f}"
    }
    
    dispatch_notification(db, recipient_id=1, notif_type="DRIFT_ALERT", payload=payload)
