from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import List, Dict, Optional
import csv
import io
from datetime import datetime
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from ..database import get_db
from ..models.core import Claim, AuditLog, User, ModelScore, RiskWeightConfig, ModelRegistry, CaseAssignment, RiskThresholdConfig, RiskAggregate
from ..routers.auth import require_role

router = APIRouter(prefix="/admin", tags=["admin"])

class WeightUpdate(BaseModel):
    version: str
    fraud_weight: float
    anomaly_weight: float
    duplicate_weight: float
    graph_weight: float
    cost_weight: float
    provider_weight: float

@router.put("/risk-aggregate/weights")
def update_risk_weights(weights: WeightUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_role(["Admin"]))):
    
    # Deactivate current
    db.query(RiskWeightConfig).update({"is_active": 0})
    
    # Insert new
    new_config = RiskWeightConfig(
        version=weights.version,
        fraud_weight=weights.fraud_weight,
        anomaly_weight=weights.anomaly_weight,
        duplicate_weight=weights.duplicate_weight,
        graph_weight=weights.graph_weight,
        cost_weight=weights.cost_weight,
        provider_weight=weights.provider_weight,
        is_active=1,
        created_by=str(current_user.id)
    )
    db.add(new_config)
    
    audit = AuditLog(actor_id=current_user.id, action="UPDATE_RISK_WEIGHTS", entity_type="SYSTEM", entity_id="risk_weight_configs", metadata_json={"new_version": weights.version})
    db.add(audit)
    db.commit()
    return {"message": "Weights updated successfully", "active_version": weights.version}

@router.get("/dashboard/analytics")
def get_analytics(db: Session = Depends(get_db), current_user: User = Depends(require_role(["Admin", "Supervisor", "Investigator", "Auditor"]))):
    from sqlalchemy import or_
    
    # 1. Total claims
    total_claims = db.query(Claim).count()
    
    # 2. High risk flagged count matching actual risk-band criteria
    high_band = db.query(RiskThresholdConfig).filter(RiskThresholdConfig.risk_band.ilike("High")).first()
    if high_band:
        high_risk_claims = db.query(Claim).join(RiskAggregate).filter(
            RiskAggregate.aggregate_score >= high_band.lower_bound,
            RiskAggregate.aggregate_score <= high_band.upper_bound
        ).count()
    else:
        high_risk_claims = db.query(Claim).join(RiskAggregate).filter(
            RiskAggregate.aggregate_score >= 0.7
        ).count()
        
    # 3. Open investigations matching active case assignment criteria (status is processing or action_required, and has assignment)
    open_investigations = db.query(CaseAssignment.claim_id).join(Claim).filter(
        or_(Claim.status == "processing", Claim.status == "action_required")
    ).distinct().count()
    
    status_counts = db.query(Claim.status, func.count(Claim.id)).group_by(Claim.status).all()
    status_dict = {k: v for k, v in status_counts}
    
    return {
        "total_claims": total_claims,
        "high_risk_claims": high_risk_claims,
        "open_investigations": open_investigations,
        "status_distribution": status_dict
    }

@router.get("/model-metrics")
def get_model_metrics(db: Session = Depends(get_db), current_user: User = Depends(require_role(["Admin"]))):
    # Retrieve some basic model score distributions
    avg_fraud_score = db.query(func.avg(ModelScore.score)).filter(ModelScore.model_type == "xgboost").scalar()
    
    return {
        "active_models": ["xgboost_fraud", "isolation_forest"],
        "avg_fraud_score_produced": float(avg_fraud_score) if avg_fraud_score else 0.0
    }

@router.get("/audit-logs")
def get_audit_logs(db: Session = Depends(get_db), current_user: User = Depends(require_role(["Admin", "Auditor"]))):
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(100).all()
    return logs

@router.get("/models")
def list_models(db: Session = Depends(get_db), current_user: User = Depends(require_role(["Admin", "Auditor"]))):
    models = db.query(ModelRegistry).order_by(ModelRegistry.created_at.desc()).all()
    return models

@router.post("/models/{id}/promote")
def promote_candidate_model(id: int, db: Session = Depends(get_db), current_user: User = Depends(require_role(["Admin"]))):
    try:
        from ..services.model_registry import promote_model
        model, diff = promote_model(db, id, current_user.id)
        return {"message": "Model promoted successfully.", "model": model, "comparison": diff}
    except ValueError as e:
        return {"error": str(e)}

@router.post("/models/{id}/rollback")
def rollback_active_model(id: int, db: Session = Depends(get_db), current_user: User = Depends(require_role(["Admin"]))):
    try:
        from ..services.model_registry import rollback_model
        model = rollback_model(db, id, current_user.id)
        return {"message": "Model rolled back successfully.", "model": model}
    except ValueError as e:
        return {"error": str(e)}

@router.get("/models/{id}/drift-report")
def get_model_drift_report(id: int, db: Session = Depends(get_db), current_user: User = Depends(require_role(["Admin", "Auditor"]))):
    from ..models.core import DriftReport
    reports = db.query(DriftReport).filter_by(model_id=id).order_by(DriftReport.computed_at.desc()).all()
    return reports

@router.get("/models/evaluation-report")
def get_evaluation_report(db: Session = Depends(get_db), current_user: User = Depends(require_role(["Admin", "Auditor"]))):
    from ..models.core import ModelRegistry, DriftReport
    import os
    active_models = db.query(ModelRegistry).filter_by(status="active").all()
    
    report = []
    for m in active_models:
        latest_drift = db.query(DriftReport).filter_by(model_id=m.id).order_by(DriftReport.computed_at.desc()).first()
        
        # Check runtime status
        runtime_status = "OFFLINE"
        if m.artifact_path and os.path.exists(m.artifact_path):
            runtime_status = "OPERATIONAL"
            
        report.append({
            "model_id": m.id,
            "model_type": m.model_type,
            "version": m.version,
            "metrics": m.metrics_json,
            "runtime_status": runtime_status,
            "evaluation_status": "AVAILABLE" if m.metrics_json else "UNAVAILABLE",
            "drift_monitoring_status": "MONITORED" if latest_drift else "UNAVAILABLE",
            "registry_status": m.status.upper(),
            "drift_status": {
                "flagged": bool(latest_drift.flagged) if latest_drift else False,
                "value": latest_drift.value if latest_drift else None,
                "threshold": latest_drift.threshold if latest_drift else None,
                "metric": latest_drift.drift_metric if latest_drift else None,
                "computed_at": latest_drift.computed_at if latest_drift else None
            },
            "promoted_at": m.promoted_at
        })
    return {"models": report}

@router.get("/audit-logs/export")
def export_audit_logs(
    format: str = "csv",
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: Session = Depends(get_db), 
    current_user: User = Depends(require_role(["Admin", "Auditor"]))
):
    q = db.query(AuditLog).order_by(AuditLog.timestamp.desc())
    
    if date_from:
        q = q.filter(AuditLog.timestamp >= date_from)
    if date_to:
        q = q.filter(AuditLog.timestamp <= date_to)
        
    logs = q.all()
    
    if format == "pdf":
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        
        data = [["ID", "Actor ID", "Action", "Entity Type", "Entity ID", "Timestamp"]]
        for log in logs:
            data.append([
                str(log.id),
                str(log.actor_id),
                log.action,
                log.entity_type,
                log.entity_id,
                log.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            ])
            
        t = Table(data)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(t)
        doc.build(elements)
        buffer.seek(0)
        
        return StreamingResponse(
            buffer, 
            media_type="application/pdf", 
            headers={"Content-Disposition": "attachment; filename=audit_export.pdf"}
        )
        
    else: # default to csv
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["ID", "Actor ID", "Action", "Entity Type", "Entity ID", "Timestamp", "Metadata"])
        
        for log in logs:
            writer.writerow([
                log.id,
                log.actor_id,
                log.action,
                log.entity_type,
                log.entity_id,
                log.timestamp.isoformat(),
                str(log.metadata_json) if log.metadata_json else ""
            ])
            
        buffer.seek(0)
        return StreamingResponse(
            iter([buffer.getvalue()]), 
            media_type="text/csv", 
            headers={"Content-Disposition": "attachment; filename=audit_export.csv"}
        )
