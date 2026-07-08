from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, JSON, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from pgvector.sqlalchemy import Vector
from ..database import Base
from ..config import settings

def utcnow():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, default="Officer")
    totp_secret = Column(String, nullable=True)
    totp_enabled = Column(Integer, default=0) # boolean 0/1
    created_at = Column(DateTime, default=utcnow)

class Claim(Base):
    __tablename__ = "claims"
    id = Column(Integer, primary_key=True, index=True)
    submitted_by = Column(Integer, ForeignKey("users.id"))
    patient_ref = Column(String, index=True)
    provider_ref = Column(String, index=True)
    procedure_code = Column(String, index=True)
    billed_amount = Column(Float)
    document_ref = Column(String)  # path/id to initial uploaded document
    status = Column(String, index=True, default="uploaded")  # uploaded, processing, pending OCR, action_required, approved, denied
    created_at = Column(DateTime, index=True, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    document = relationship("ClaimDocument", back_populates="claim", uselist=False)
    scores = relationship("ModelScore", back_populates="claim")
    notes = relationship("InvestigationNote", back_populates="claim")

class ClaimDocument(Base):
    __tablename__ = "claim_documents"
    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"))
    file_path = Column(String, nullable=False)
    ocr_text = Column(Text)
    ocr_confidence = Column(Float)

    claim = relationship("Claim", back_populates="document")

class ModelScore(Base):
    __tablename__ = "model_scores"
    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"))
    model_type = Column(String) # xgboost, isolation_forest
    score = Column(Float)
    generated_at = Column(DateTime, default=utcnow)

    claim = relationship("Claim", back_populates="scores")

class DuplicateMatch(Base):
    __tablename__ = "duplicate_matches"
    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"))
    matched_claim_id = Column(Integer, ForeignKey("claims.id"))
    similarity_score = Column(Float)
    method = Column(String) # fuzzy, semantic

class GraphRelationship(Base):
    __tablename__ = "graph_relationships"
    id = Column(Integer, primary_key=True, index=True)
    entity_1 = Column(String, index=True)
    entity_2 = Column(String, index=True)
    relationship_type = Column(String)
    metadata_json = Column(JSON, nullable=True)

class ShapExplanation(Base):
    __tablename__ = "shap_explanations"
    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"))
    feature = Column(String)
    contribution_value = Column(Float)

class InvestigationNote(Base):
    __tablename__ = "investigation_notes"
    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"))
    author_id = Column(Integer, ForeignKey("users.id"))
    note_text = Column(Text)
    created_at = Column(DateTime, default=utcnow)

    claim = relationship("Claim", back_populates="notes")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String, nullable=False)
    timestamp = Column(DateTime, default=utcnow)
    metadata_json = Column(JSON, nullable=True)

class Report(Base):
    __tablename__ = "reports"
    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"))
    generated_by = Column(Integer, ForeignKey("users.id"))
    file_path = Column(String)
    generated_at = Column(DateTime, default=utcnow)

class CostBenchmark(Base):
    __tablename__ = "cost_benchmarks"
    id = Column(Integer, primary_key=True, index=True)
    procedure_code = Column(String, index=True, nullable=False)
    region = Column(String, nullable=True)
    provider_id = Column(String, nullable=True)
    median = Column(Float, nullable=False)
    p25 = Column(Float, nullable=False)
    p75 = Column(Float, nullable=False)
    iqr = Column(Float, nullable=False)
    sample_size = Column(Integer, nullable=False)
    confidence = Column(String, nullable=False) # High, Medium, Low
    computed_at = Column(DateTime, default=utcnow)

class ProviderRiskProfile(Base):
    __tablename__ = "provider_risk_profiles"
    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(String, unique=True, index=True, nullable=False)
    rolling_risk_score = Column(Float, nullable=False, default=0.0)
    verified_outcomes_count = Column(Integer, nullable=False, default=0)
    last_computed_at = Column(DateTime, default=utcnow)

class ProcedureValidationFlag(Base):
    __tablename__ = "procedure_validation_flags"
    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), index=True)
    code = Column(String, nullable=False)
    flag_type = Column(String, nullable=False) # invalid_code, description_mismatch, rare_combination
    description = Column(Text, nullable=False)
    
    claim = relationship("Claim", backref="validation_flags")

class ClaimEmbedding(Base):
    __tablename__ = "claim_embeddings"
    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), unique=True, index=True)
    
    if "sqlite" in settings.DATABASE_URL:
        embedding = Column(JSON)
    else:
        embedding = Column(Vector(384)) # 384 dimensions for all-MiniLM-L6-v2
    model_version = Column(String, default="all-MiniLM-L6-v2")
    
    claim = relationship("Claim", backref="embedding")

class RiskAggregate(Base):
    __tablename__ = "risk_aggregates"
    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), unique=True, index=True)
    fraud_score = Column(Float, nullable=False, default=0.0)
    anomaly_score = Column(Float, nullable=False, default=0.0)
    duplicate_score = Column(Float, nullable=False, default=0.0)
    graph_score = Column(Float, nullable=False, default=0.0)
    cost_score = Column(Float, nullable=False, default=0.0)
    provider_score = Column(Float, nullable=False, default=0.0)
    aggregate_score = Column(Float, nullable=False, default=0.0)
    weighting_version = Column(String, nullable=False)
    
    claim = relationship("Claim", backref="risk_aggregate")

class RiskThresholdConfig(Base):
    __tablename__ = "risk_threshold_configs"
    id = Column(Integer, primary_key=True, index=True)
    risk_band = Column(String, unique=True, index=True, nullable=False) # e.g. "Low", "Medium", "High"
    lower_bound = Column(Float, nullable=False)
    upper_bound = Column(Float, nullable=False)
    updated_by = Column(String, nullable=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

class RiskWeightConfig(Base):
    __tablename__ = "risk_weight_configs"
    id = Column(Integer, primary_key=True, index=True)
    version = Column(String, unique=True, index=True, nullable=False)
    fraud_weight = Column(Float, nullable=False)
    anomaly_weight = Column(Float, nullable=False)
    duplicate_weight = Column(Float, nullable=False)
    graph_weight = Column(Float, nullable=False)
    cost_weight = Column(Float, nullable=False)
    provider_weight = Column(Float, nullable=False)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    is_active = Column(Integer, default=0) # 1 for active, 0 for inactive


class ModelRegistry(Base):
    __tablename__ = "model_registry"
    
    id = Column(Integer, primary_key=True, index=True)
    model_type = Column(String, index=True) # e.g. "xgboost", "isolation_forest"
    version = Column(String) # e.g. "v1.0.0"
    metrics_json = Column(JSON) # e.g. {"auc": 0.95, "precision": 0.8}
    status = Column(String) # "candidate", "active", "retired"
    artifact_path = Column(String) # path to the file
    created_at = Column(DateTime, default=utcnow)
    promoted_at = Column(DateTime, nullable=True)

class DriftReport(Base):
    __tablename__ = "drift_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(Integer, ForeignKey("model_registry.id"), index=True)
    feature_or_prediction = Column(String, index=True)
    drift_metric = Column(String) # e.g. PSI
    value = Column(Float)
    threshold = Column(Float)
    flagged = Column(Integer, default=0) # Boolean 0/1
    computed_at = Column(DateTime, default=utcnow)

class CaseAssignment(Base):
    __tablename__ = "case_assignments"
    
    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), index=True)
    investigator_id = Column(Integer, ForeignKey("users.id"), index=True)
    assigned_by = Column(Integer, ForeignKey("users.id"))
    assigned_at = Column(DateTime, default=utcnow)
    sla_due_at = Column(DateTime)
    
    claim = relationship("Claim", backref="assignments")
    investigator = relationship("User", foreign_keys=[investigator_id])
    assigner = relationship("User", foreign_keys=[assigned_by])

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    recipient_id = Column(Integer, ForeignKey("users.id"), index=True)
    type = Column(String) # e.g., "SLA_WARNING", "NEW_ASSIGNMENT", "DRIFT_ALERT"
    payload = Column(JSON) # e.g., {"claim_id": 123, "message": "High risk claim"}
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)
