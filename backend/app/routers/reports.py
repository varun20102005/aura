import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from ..database import get_db
from ..models.core import Claim, AuditLog, User, Report
from ..routers.auth import require_role

router = APIRouter(prefix="/reports", tags=["reports"])
REPORTS_DIR = "reports_out"
os.makedirs(REPORTS_DIR, exist_ok=True)

@router.get("/pdf/{claim_id}")
def generate_pdf_report(claim_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_role(["Admin", "Auditor", "Investigator"]))):
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
        
    file_path = os.path.join(REPORTS_DIR, f"claim_{claim_id}_audit.pdf")
    
    # Generate PDF with ReportLab
    c = canvas.Canvas(file_path, pagesize=letter)
    c.drawString(100, 750, f"AURA Audit Report - Claim #{claim.id}")
    c.drawString(100, 730, f"Patient: {claim.patient_ref}")
    c.drawString(100, 710, f"Provider: {claim.provider_ref}")
    c.drawString(100, 690, f"Billed Amount: ${claim.billed_amount}")
    c.drawString(100, 670, f"Status: {claim.status}")
    c.save()
    
    # Log report generation
    db.add(Report(claim_id=claim_id, generated_by=current_user.id, file_path=file_path))
    audit = AuditLog(actor_id=current_user.id, action="GENERATE_REPORT", entity_type="CLAIM", entity_id=str(claim_id))
    db.add(audit)
    db.commit()
    
    return FileResponse(file_path, media_type='application/pdf', filename=f"claim_{claim_id}_audit.pdf")
