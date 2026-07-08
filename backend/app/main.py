import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from .config import settings
from .routers import auth, claims, admin, reports, analytics, providers, investigators, notifications
from .database import engine, Base, SessionLocal
from apscheduler.schedulers.background import BackgroundScheduler
from .services.risk_service import update_all_provider_risk_profiles
from .services.drift_service import compute_model_drift

# We will use Alembic for migrations, but we can also just create tables if they don't exist for dev
tables = [t for t in Base.metadata.sorted_tables if t.name != "claim_embeddings"]
Base.metadata.create_all(bind=engine, tables=tables)

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="AURA API",
    description="Automated Risk & Audit Analyzer Backend",
    version="1.0.0"
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(claims.router)
app.include_router(admin.router)
app.include_router(reports.router)
app.include_router(analytics.router)
app.include_router(providers.router)
app.include_router(investigators.router)
app.include_router(notifications.router)

if os.getenv("ENVIRONMENT", "development") != "production":
    from .routers import dev_diagnostic
    app.include_router(dev_diagnostic.router)

scheduler = BackgroundScheduler()

def init_risk_defaults(db):
    from .models.core import RiskThresholdConfig, RiskWeightConfig
    
    # Init bands
    if not db.query(RiskThresholdConfig).first():
        db.add_all([
            RiskThresholdConfig(risk_band="Low", lower_bound=0.0, upper_bound=0.3),
            RiskThresholdConfig(risk_band="Medium", lower_bound=0.3, upper_bound=0.7),
            RiskThresholdConfig(risk_band="High", lower_bound=0.7, upper_bound=1.0)
        ])
    
    # Init default weights (1/6th each)
    if not db.query(RiskWeightConfig).first():
        w = 1.0 / 6.0
        db.add(RiskWeightConfig(
            version="v1.0",
            fraud_weight=w, anomaly_weight=w, duplicate_weight=w,
            graph_weight=w, cost_weight=w, provider_weight=w,
            is_active=1
        ))
    db.commit()

def init_model_registry(db):
    from .models.core import ModelRegistry
    import json
    import os
    
    # Load xgboost evaluation metrics if they exist
    xgboost_metrics = None
    if os.path.exists("xgboost_eval_out.json"):
        try:
            with open("xgboost_eval_out.json") as f:
                xgboost_metrics = json.load(f).get("metrics")
        except Exception:
            pass

    if not db.query(ModelRegistry).first():
        db.add(ModelRegistry(
            model_type="xgboost", 
            version="v1.0.0", 
            status="active", 
            artifact_path="ml_models/xgboost_fraud.json",
            metrics_json=xgboost_metrics
        ))
        db.add(ModelRegistry(
            model_type="isolation_forest", 
            version="v1.0.0", 
            status="active", 
            artifact_path="ml_models/isolation_forest.joblib",
            metrics_json=None
        ))
        db.commit()
    else:
        # Update existing model metrics if not set
        xgb_m = db.query(ModelRegistry).filter_by(model_type="xgboost", version="v1.0.0").first()
        if xgb_m and not xgb_m.metrics_json and xgboost_metrics:
            xgb_m.metrics_json = xgboost_metrics
            db.commit()

def cleanup_duplicate_assignments(db):
    from .models.core import CaseAssignment
    from sqlalchemy import func
    # Identify pairs that have duplicates
    pairs = db.query(CaseAssignment.claim_id, CaseAssignment.investigator_id).group_by(
        CaseAssignment.claim_id, CaseAssignment.investigator_id
    ).having(func.count(CaseAssignment.id) > 1).all()
    
    for claim_id, investigator_id in pairs:
        # Keep the latest assignment, delete the rest
        duplicates = db.query(CaseAssignment).filter_by(
            claim_id=claim_id, investigator_id=investigator_id
        ).order_by(CaseAssignment.assigned_at.desc()).all()
        
        for duplicate in duplicates[1:]:
            db.delete(duplicate)
    db.commit()

@app.on_event("startup")
def start_scheduler():
    def job():
        db = SessionLocal()
        try:
            from .services.drift_service import compute_model_drift
            update_all_provider_risk_profiles(db)
            compute_model_drift(db)
        finally:
            db.close()
            
    # Initialize defaults
    db = SessionLocal()
    try:
        init_risk_defaults(db)
        init_model_registry(db)
        cleanup_duplicate_assignments(db)
    finally:
        db.close()
            
    # Run the rolling aggregation every hour
    scheduler.add_job(job, 'interval', hours=1)
    scheduler.start()

@app.on_event("shutdown")
def shutdown_scheduler():
    scheduler.shutdown()

@app.get("/")
def read_root():
    return {"message": "Welcome to AURA API", "status": "running"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/health/ready")
def readiness_check():
    """Verifies database connectivity before reporting ready."""
    try:
        db = SessionLocal()
        db.execute(Base.metadata.tables["users"].select().limit(1))
        db.close()
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=503, content={"status": "not_ready", "database": str(e)})

import uuid

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response
