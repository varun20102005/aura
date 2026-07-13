import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import csv
import io
from datetime import datetime, timedelta, timezone
from sqlalchemy import or_, and_

from ..database import get_db
from ..models.core import Claim, ClaimDocument, InvestigationNote, AuditLog, User
from ..routers.auth import get_current_user, require_role
from ..services.pipeline import process_claim_pipeline_task
from ..limiter import limiter

router = APIRouter(prefix="/claims", tags=["claims"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class NoteCreate(BaseModel):
    note_text: str

class StatusUpdate(BaseModel):
    status: str

@router.post("/upload")
@limiter.limit("10/minute")
def upload_claim(
    request: Request,
    background_tasks: BackgroundTasks,
    patient_ref: str = Form(...),
    provider_ref: str = Form(...),
    procedure_code: str = Form(...),
    billed_amount: float = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Officer", "Admin"]))
):
    # Save file
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Create Claim
    new_claim = Claim(
        submitted_by=current_user.id,
        patient_ref=patient_ref,
        provider_ref=provider_ref,
        procedure_code=procedure_code,
        billed_amount=billed_amount,
        document_ref=file.filename,
        status="processing"
    )
    db.add(new_claim)
    db.commit()
    db.refresh(new_claim)
    
    # Create Document record
    doc = ClaimDocument(claim_id=new_claim.id, file_path=file_path)
    db.add(doc)
    
    # Audit log
    audit = AuditLog(actor_id=current_user.id, action="UPLOAD_CLAIM", entity_type="CLAIM", entity_id=str(new_claim.id))
    db.add(audit)
    db.commit()
    
    # Trigger async pipeline
    background_tasks.add_task(process_claim_pipeline_task, new_claim.id)
    
    return {"message": "Claim uploaded and processing started", "claim_id": new_claim.id}

@router.get("")
def list_claims(
    skip: int = 0, 
    limit: int = 50, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(require_role(["Admin", "Investigator", "Auditor", "Supervisor", "Officer"]))
):
    total = db.query(Claim).count()
    claims = db.query(Claim).offset(skip).limit(limit).all()
    return {"items": claims, "total": total}

@router.get("/search")
def search_claims(
    query: Optional[str] = None,
    status: Optional[str] = None,
    risk_band: Optional[str] = None,
    assigned_to: Optional[int] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Supervisor", "Investigator", "Auditor"]))
):
    from ..models.core import CaseAssignment, RiskAggregate, RiskThresholdConfig
    
    q = db.query(Claim)
    
    if query:
        q = q.filter(or_(Claim.patient_ref.ilike(f"%{query}%"), Claim.provider_ref.ilike(f"%{query}%")))
        
    if status:
        q = q.filter(Claim.status == status)
        
    if assigned_to:
        q = q.join(CaseAssignment).filter(CaseAssignment.investigator_id == assigned_to)
        
    if risk_band:
        # Pre-fetch the bounds for the requested band
        band_conf = db.query(RiskThresholdConfig).filter(RiskThresholdConfig.risk_band.ilike(risk_band)).first()
        if band_conf:
            q = q.join(RiskAggregate).filter(
                RiskAggregate.aggregate_score >= band_conf.lower_bound,
                RiskAggregate.aggregate_score <= band_conf.upper_bound
            )
        else:
            # If invalid band, return empty
            q = q.filter(Claim.id == -1)
            
    if date_from:
        q = q.filter(Claim.created_at >= date_from)
        
    if date_to:
        q = q.filter(Claim.created_at <= date_to)
        
    total = q.count()
    results = q.order_by(Claim.created_at.desc()).offset(skip).limit(limit).all()
    
    return {"items": results, "total": total}

@router.get("/{claim_id}")
def get_claim(claim_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_role(["Admin", "Investigator", "Auditor", "Supervisor", "Officer"]))):
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
        
    audit = AuditLog(actor_id=current_user.id, action="VIEW_CLAIM", entity_type="CLAIM", entity_id=str(claim_id))
    db.add(audit)
    db.commit()
    db.refresh(claim)
    return claim

@router.post("/{claim_id}/notes")
def add_note(claim_id: int, note: NoteCreate, db: Session = Depends(get_db), current_user: User = Depends(require_role(["Investigator", "Supervisor", "Admin"]))):
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
        
    new_note = InvestigationNote(claim_id=claim_id, author_id=current_user.id, note_text=note.note_text)
    db.add(new_note)
    
    audit = AuditLog(actor_id=current_user.id, action="ADD_NOTE", entity_type="CLAIM", entity_id=str(claim_id))
    db.add(audit)
    db.commit()
    return {"message": "Note added"}

@router.post("/{claim_id}/status")
def update_status(claim_id: int, status_update: StatusUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_role(["Investigator", "Supervisor", "Admin"]))):
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
        
    claim.status = status_update.status
    
    audit = AuditLog(actor_id=current_user.id, action="UPDATE_STATUS", entity_type="CLAIM", entity_id=str(claim_id), metadata_json={"new_status": status_update.status})
    db.add(audit)
    db.commit()
    return {"message": "Status updated"}

@router.get("/{claim_id}/procedure-validation")
def get_procedure_validation(claim_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_role(["Admin", "Investigator", "Auditor", "Supervisor", "Officer"]))):
    from ..models.core import ProcedureValidationFlag
    flags = db.query(ProcedureValidationFlag).filter_by(claim_id=claim_id).all()
    
    return [
        {
            "code": f.code,
            "flag_type": f.flag_type,
            "description": f.description
        } for f in flags
    ]

@router.get("/{claim_id}/similar")
def get_similar_claims(
    claim_id: int, 
    method: str = "hybrid", 
    limit: int = 5,
    db: Session = Depends(get_db), 
    current_user: User = Depends(require_role(["Admin", "Investigator", "Auditor", "Supervisor"]))
):
    from ..models.core import ClaimEmbedding, ClaimDocument
    from ..config import settings
    from rapidfuzz import fuzz
    
    target_claim = db.query(Claim).filter_by(id=claim_id).first()
    if not target_claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    target_doc = db.query(ClaimDocument).filter_by(claim_id=claim_id).first()
    target_text = target_doc.ocr_text if target_doc else ""
    
    # 1. Gather fuzzy scores
    fuzzy_scores = {}
    if method in ["fuzzy", "hybrid"]:
        all_docs = db.query(ClaimDocument).filter(ClaimDocument.claim_id != claim_id).all()
        for d in all_docs:
            if not d.ocr_text: continue
            score = fuzz.token_sort_ratio(target_text, d.ocr_text) / 100.0
            fuzzy_scores[d.claim_id] = score
            
    # 2. Gather semantic scores (Cosine Similarity via pgvector)
    semantic_scores = {}
    if method in ["semantic", "hybrid"]:
        target_embedding = db.query(ClaimEmbedding).filter_by(claim_id=claim_id).first()
        if target_embedding:
            try:
                # Cosine distance: <=>
                # Similarity = 1 - distance
                similar_embs = db.query(
                    ClaimEmbedding.claim_id,
                    ClaimEmbedding.embedding.cosine_distance(target_embedding.embedding).label('distance')
                ).filter(ClaimEmbedding.claim_id != claim_id).all()
                
                for emb in similar_embs:
                    semantic_scores[emb.claim_id] = 1.0 - float(emb.distance)
            except Exception as e:
                # If DB is not Postgres (e.g. tests using sqlite), this might crash.
                pass
                
    # 3. Combine scores
    results = []
    # Collect all unique candidate IDs
    all_candidates = set(fuzzy_scores.keys()).union(set(semantic_scores.keys()))
    
    weight = settings.HYBRID_SEMANTIC_WEIGHT
    
    for cid in all_candidates:
        f_score = fuzzy_scores.get(cid, 0.0)
        s_score = semantic_scores.get(cid, 0.0)
        
        if method == "fuzzy":
            final = f_score
        elif method == "semantic":
            final = s_score
        else: # hybrid
            final = (weight * s_score) + ((1.0 - weight) * f_score)
            
        results.append({
            "claim_id": cid,
            "method": method,
            "score": final,
            "fuzzy_component": f_score if method == "hybrid" else None,
            "semantic_component": s_score if method == "hybrid" else None
        })
        
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]

@router.get("/{claim_id}/risk-aggregate")
def get_risk_aggregate(claim_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_role(["Admin", "Investigator", "Auditor", "Supervisor"]))):
    from ..models.core import RiskAggregate, RiskThresholdConfig
    from ..services.aggregation_service import get_active_weights
    
    agg = db.query(RiskAggregate).filter_by(claim_id=claim_id).first()
    if not agg:
        raise HTTPException(status_code=404, detail="Risk aggregate not found")
        
    bands = db.query(RiskThresholdConfig).all()
    assigned_band = "Unknown"
    for b in bands:
        if b.lower_bound <= agg.aggregate_score <= b.upper_bound:
            assigned_band = b.risk_band
            break
            
    weights = get_active_weights(db)
            
    return {
        "claim_id": agg.claim_id,
        "aggregate_score": agg.aggregate_score,
        "risk_band": assigned_band,
        "weighting_version": agg.weighting_version,
        "components": {
            "fraud_score": agg.fraud_score,
            "anomaly_score": agg.anomaly_score,
            "duplicate_score": agg.duplicate_score,
            "graph_score": agg.graph_score,
            "cost_score": agg.cost_score,
            "provider_score": agg.provider_score
        },
        "weights": weights
    }

class AssignRequest(BaseModel):
    investigator_id: int

@router.post("/{claim_id}/assign")
def assign_claim(claim_id: int, req: AssignRequest, db: Session = Depends(get_db), current_user: User = Depends(require_role(["Supervisor", "Admin"]))):
    from ..models.core import CaseAssignment, RiskAggregate, RiskThresholdConfig
    from ..services.notification_service import dispatch_notification
    
    claim = db.query(Claim).filter_by(id=claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
        
    investigator = db.query(User).filter_by(id=req.investigator_id).first()
    if not investigator:
        raise HTTPException(status_code=404, detail="Investigator not found")
        
    # Determine SLA based on Risk
    agg = db.query(RiskAggregate).filter_by(claim_id=claim_id).first()
    bands = db.query(RiskThresholdConfig).all()
    assigned_band = "Medium" # Default
    if agg:
        for b in bands:
            if b.lower_bound <= agg.aggregate_score <= b.upper_bound:
                assigned_band = b.risk_band
                break
                
    # Default SLA Windows
    sla_hours = 72
    if assigned_band == "High":
        sla_hours = 24
    elif assigned_band == "Low":
        sla_hours = 168 # 7 days
        
    sla_due_at = datetime.now(timezone.utc) + timedelta(hours=sla_hours)
    
    # Check if an assignment for this claim_id and investigator_id already exists
    assignment = db.query(CaseAssignment).filter(
        CaseAssignment.claim_id == claim_id,
        CaseAssignment.investigator_id == req.investigator_id
    ).first()
    
    if assignment:
        # Update existing assignment
        assignment.sla_due_at = sla_due_at
        assignment.assigned_at = datetime.now(timezone.utc)
        assignment.assigned_by = current_user.id
    else:
        assignment = CaseAssignment(
            claim_id=claim_id,
            investigator_id=req.investigator_id,
            assigned_by=current_user.id,
            sla_due_at=sla_due_at
        )
        db.add(assignment)
    
    audit = AuditLog(actor_id=current_user.id, action="ASSIGN_CLAIM", entity_type="CLAIM", entity_id=str(claim_id), metadata_json={"investigator_id": req.investigator_id, "sla_due_at": sla_due_at.isoformat()})
    db.add(audit)
    db.commit()
    db.refresh(assignment)
    
    # Notify investigator
    dispatch_notification(
        db, 
        recipient_id=req.investigator_id, 
        notif_type="NEW_ASSIGNMENT", 
        payload={"claim_id": claim_id, "assigned_by": current_user.id, "sla_due_at": sla_due_at.isoformat(), "risk_band": assigned_band}
    )
    
    # Optional SLA warning notification immediately if high risk (as requested by TRD spec sometimes)
    if assigned_band == "High":
        dispatch_notification(
            db, 
            recipient_id=req.investigator_id, 
            notif_type="SLA_WARNING", 
            payload={"claim_id": claim_id, "sla_due_at": sla_due_at.isoformat()}
        )
        
    return {"message": "Claim assigned", "assignment_id": assignment.id, "sla_due_at": sla_due_at}

class BulkClaimRow(BaseModel):
    patient_ref: str
    provider_ref: str
    procedure_code: str
    billed_amount: float
    document_filename: str

@router.post("/bulk-upload")
@limiter.limit("10/minute")
def bulk_upload_claims(
    request: Request,
    background_tasks: BackgroundTasks,
    manifest: UploadFile = File(...),
    documents: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Officer", "Admin"]))
):
    # Read manifest CSV
    content = manifest.file.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(content))
    
    successes = []
    errors = []
    
    # Map document filenames to actual file objects
    doc_map = {d.filename: d for d in documents}
    
    for row_num, row in enumerate(reader, start=1):
        try:
            row_data = BulkClaimRow(**row)
            patient_ref = row_data.patient_ref
            provider_ref = row_data.provider_ref
            procedure_code = row_data.procedure_code
            billed_amount = row_data.billed_amount
            doc_filename = row_data.document_filename
            
            if doc_filename not in doc_map:
                errors.append({"row": row_num, "error": f"Document {doc_filename} not found in upload files"})
                continue
                
            file = doc_map[doc_filename]
            
            # Save file
            file_path = os.path.join(UPLOAD_DIR, file.filename)
            file.file.seek(0)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
                
            # Create Claim
            new_claim = Claim(
                submitted_by=current_user.id,
                patient_ref=patient_ref,
                provider_ref=provider_ref,
                procedure_code=procedure_code,
                billed_amount=billed_amount,
                document_ref=file.filename,
                status="processing"
            )
            db.add(new_claim)
            db.commit()
            db.refresh(new_claim)
            
            # Create Document record
            doc = ClaimDocument(claim_id=new_claim.id, file_path=file_path)
            db.add(doc)
            
            # Audit log
            audit = AuditLog(actor_id=current_user.id, action="BULK_UPLOAD_CLAIM", entity_type="CLAIM", entity_id=str(new_claim.id))
            db.add(audit)
            db.commit()
            
            # Trigger async pipeline
            background_tasks.add_task(process_claim_pipeline_task, new_claim.id)
            
            successes.append({"row": row_num, "claim_id": new_claim.id})
            
        except Exception as e:
            errors.append({"row": row_num, "error": str(e)})
            db.rollback()
            
    return {
        "message": "Bulk upload complete",
        "successful_records": len(successes),
        "failed_records": len(errors),
        "successes": successes,
        "errors": errors
    }
