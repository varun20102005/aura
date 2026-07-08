import os
import json
from datetime import datetime
from typing import Dict, Any, Tuple
from sqlalchemy.orm import Session
from ..models.core import ModelRegistry, AuditLog, utcnow

def register_model(db: Session, model_type: str, version: str, metrics: Dict[str, float], artifact_path: str, actor_id: int = None) -> ModelRegistry:
    # Check if this exact version exists
    existing = db.query(ModelRegistry).filter_by(model_type=model_type, version=version).first()
    if existing:
        raise ValueError(f"Version {version} for {model_type} already exists.")
        
    model = ModelRegistry(
        model_type=model_type,
        version=version,
        metrics_json=metrics,
        status="candidate",
        artifact_path=artifact_path
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    
    log = AuditLog(
        actor_id=actor_id,
        action="MODEL_REGISTERED",
        entity_type="MODEL",
        entity_id=str(model.id),
        metadata_json={"model_type": model_type, "version": version}
    )
    db.add(log)
    db.commit()
    return model

def compare_models(db: Session, candidate_id: int, active_id: int) -> Dict[str, Any]:
    candidate = db.query(ModelRegistry).filter_by(id=candidate_id).first()
    active = db.query(ModelRegistry).filter_by(id=active_id).first()
    
    if not candidate or not active:
        raise ValueError("Model ID not found.")
        
    if candidate.model_type != active.model_type:
        raise ValueError("Cannot compare different model types.")
        
    c_metrics = candidate.metrics_json or {}
    a_metrics = active.metrics_json or {}
    
    diff = {}
    keys = set(c_metrics.keys()).union(set(a_metrics.keys()))
    for k in keys:
        c_val = c_metrics.get(k, 0.0)
        a_val = a_metrics.get(k, 0.0)
        diff[k] = {
            "active": a_val,
            "candidate": c_val,
            "improvement": c_val - a_val
        }
        
    return {
        "model_type": candidate.model_type,
        "active_version": active.version,
        "candidate_version": candidate.version,
        "metrics_diff": diff
    }

def promote_model(db: Session, candidate_id: int, actor_id: int) -> Tuple[ModelRegistry, Dict[str, Any]]:
    candidate = db.query(ModelRegistry).filter_by(id=candidate_id).first()
    if not candidate:
        raise ValueError("Candidate not found.")
    if candidate.status == "active":
        raise ValueError("Model is already active.")
        
    # Get current active
    active = db.query(ModelRegistry).filter_by(model_type=candidate.model_type, status="active").first()
    
    diff_report = {}
    if active:
        diff_report = compare_models(db, candidate.id, active.id)
        active.status = "retired"
        db.add(active)
        
    candidate.status = "active"
    candidate.promoted_at = utcnow()
    db.add(candidate)
    
    log = AuditLog(
        actor_id=actor_id,
        action="MODEL_PROMOTED",
        entity_type="MODEL",
        entity_id=str(candidate.id),
        metadata_json={
            "model_type": candidate.model_type,
            "new_version": candidate.version,
            "retired_version": active.version if active else None
        }
    )
    db.add(log)
    db.commit()
    db.refresh(candidate)
    
    return candidate, diff_report

def rollback_model(db: Session, target_id: int, actor_id: int) -> ModelRegistry:
    target = db.query(ModelRegistry).filter_by(id=target_id).first()
    if not target:
        raise ValueError("Target model not found.")
        
    # Get current active
    active = db.query(ModelRegistry).filter_by(model_type=target.model_type, status="active").first()
    
    if active:
        active.status = "retired"
        db.add(active)
        
    target.status = "active"
    target.promoted_at = utcnow()
    db.add(target)
    
    log = AuditLog(
        actor_id=actor_id,
        action="MODEL_ROLLED_BACK",
        entity_type="MODEL",
        entity_id=str(target.id),
        metadata_json={
            "model_type": target.model_type,
            "rolled_back_to": target.version,
            "retired_version": active.version if active else None
        }
    )
    db.add(log)
    db.commit()
    db.refresh(target)
    
    return target
