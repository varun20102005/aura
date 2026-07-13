import os
import time
import json
import pandas as pd
import numpy as np
import joblib
from sqlalchemy.orm import Session
from ..models.core import Claim, ClaimDocument, ModelScore, ShapExplanation, DuplicateMatch, AuditLog, GraphRelationship, RiskAggregate
from ..config import settings
import logging

logger = logging.getLogger(__name__)

# Try importing heavy ML libraries, failing gracefully if they aren't loaded yet
try:
    import easyocr
    import pytesseract
    from PIL import Image
    import rapidfuzz
    import networkx as nx
    import xgboost as xgb
    import shap
    import google.generativeai as genai
    
    reader = easyocr.Reader(['en'], gpu=False) # initialize once
except ImportError:
    reader = None

def run_ocr(file_path: str):
    text = ""
    confidence = 0.0
    if not reader:
        return "OCR Library not loaded", 0.0
    
    try:
        results = reader.readtext(file_path)
        text = " ".join([res[1] for res in results])
        confidence = sum([res[2] for res in results]) / len(results) if results else 0.0
    except Exception as e:
        logger.warning(f"EasyOCR failed: {e}. Falling back to pytesseract.")
        try:
            img = Image.open(file_path)
            text = pytesseract.image_to_string(img)
            confidence = 0.5 # tesseract doesn't give easy confidence without verbose output
        except Exception as te:
            logger.error(f"OCR failed entirely: {te}")
            
    return text, confidence

_MODEL_CACHE = {}

def _load_model_from_registry(db: Session, model_type: str, default_path: str):
    from ..models.core import ModelRegistry
    active = db.query(ModelRegistry).filter_by(model_type=model_type, status="active").first()
    path = active.artifact_path if active else default_path
    
    if path in _MODEL_CACHE:
        return _MODEL_CACHE[path], path
        
    if model_type == "xgboost":
        m = xgb.XGBClassifier()
        m.load_model(path)
        _MODEL_CACHE[path] = m
    else:
        m = joblib.load(path)
        _MODEL_CACHE[path] = m
        
    return _MODEL_CACHE[path], path

_FEATURES_CACHE = None

def _get_model_features():
    global _FEATURES_CACHE
    if _FEATURES_CACHE is None:
        _FEATURES_CACHE = joblib.load("ml_models/model_features.joblib")
    return _FEATURES_CACHE

def process_claim_pipeline_task(claim_id: int):
    """
    Entry point for BackgroundTasks. Creates its own DB session
    to avoid reusing the request handler's session (which closes
    after the HTTP response is sent).
    """
    from ..database import SessionLocal
    db = SessionLocal()
    try:
        process_claim_pipeline(claim_id, db)
    except Exception as e:
        logger.error(f"Pipeline task failed for claim {claim_id}: {e}")
        db.rollback()
    finally:
        db.close()

def _run_xgboost(db_path, claim_id, feat_dict):
    # Using local session if needed, but since we just do inference, no DB needed if models are loaded.
    from ..database import SessionLocal
    db = SessionLocal()
    try:
        xgb_model, _ = _load_model_from_registry(db, "xgboost", "ml_models/xgboost_fraud.json")
        features = _get_model_features()
        # Filter feat_dict to ONLY what the model expects
        filtered_feat = {f: feat_dict.get(f, 0) for f in features}
        
        # OHE for procedure code
        proc_code = feat_dict.get("procedure_code")
        if proc_code:
            proc_col = f"procedure_code_{proc_code}"
            if proc_col in filtered_feat:
                filtered_feat[proc_col] = 1
                
        df_feat = pd.DataFrame([filtered_feat])
        score = float(xgb_model.predict_proba(df_feat)[0][1])
        
        # Calculate SHAP locally as well to avoid passing huge model back
        explainer = shap.TreeExplainer(xgb_model)
        shap_vals = explainer.shap_values(df_feat)
        shap_res = [(features[i], float(shap_vals[0][i])) for i in range(len(features)) if abs(float(shap_vals[0][i])) > 0.01]
        
        return {"type": "xgboost", "score": score, "shap": shap_res, "df": df_feat}
    finally:
        db.close()

def _run_isolation_forest(db_path, claim_id, feat_dict):
    from ..database import SessionLocal
    db = SessionLocal()
    try:
        iso_model, _ = _load_model_from_registry(db, "isolation_forest", "ml_models/isolation_forest.joblib")
        features = _get_model_features()
        filtered_feat = {f: feat_dict.get(f, 0) for f in features}
        
        proc_code = feat_dict.get("procedure_code")
        if proc_code:
            proc_col = f"procedure_code_{proc_code}"
            if proc_col in filtered_feat:
                filtered_feat[proc_col] = 1
                
        df_feat = pd.DataFrame([filtered_feat])
        score = float(iso_model.decision_function(df_feat)[0])
        return {"type": "isolation_forest", "score": score}
    finally:
        db.close()

def _run_graph(db_path, claim_id, patient_ref, provider_ref):
    from ..database import SessionLocal
    db = SessionLocal()
    try:
        G = nx.Graph()
        G.add_edge(patient_ref, provider_ref, claim_id=claim_id)
        
        rel = GraphRelationship(
            entity_1=patient_ref, 
            entity_2=provider_ref, 
            relationship_type="PATIENT_PROVIDER", 
            metadata_json={"claim_id": claim_id}
        )
        db.add(rel)
        db.commit()
        return {"type": "graph", "status": "success"}
    finally:
        db.close()

def _run_embedding(db_path, claim_id):
    from ..database import SessionLocal
    from .embedding_service import generate_claim_embedding
    db = SessionLocal()
    try:
        generate_claim_embedding(db, claim_id)
        return {"type": "embedding", "status": "success"}
    finally:
        db.close()

def process_claim_pipeline(claim_id: int, db: Session):
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        return
    
    doc = db.query(ClaimDocument).filter(ClaimDocument.claim_id == claim_id).first()
    
    # 1. OCR (Stage 1)
    try:
        if doc and doc.file_path:
            text, conf = run_ocr(doc.file_path)
            doc.ocr_text = text
            doc.ocr_confidence = float(conf)
            db.commit()
    except Exception as e:
        logger.error(f"OCR step failed: {e}")
        claim.status = "pending OCR"
        db.commit()
        return

    # 2. Feature Engineering (Includes Validation, Duplicates, Benchmarks, Provider Risk)
    from .feature_engineering import build_consolidated_features
    try:
        consolidated_features = build_consolidated_features(db, claim_id)
    except Exception as e:
        logger.error(f"Feature engineering failed: {e}")
        consolidated_features = {"billed_amount": claim.billed_amount, "procedure_code": claim.procedure_code}

    # 3. Parallel AI Execution
    import concurrent.futures
    results = []
    
    # Using dummy string since db connection is created inside threads
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        f_xgb = executor.submit(_run_xgboost, "", claim_id, consolidated_features)
        f_iso = executor.submit(_run_isolation_forest, "", claim_id, consolidated_features)
        f_graph = executor.submit(_run_graph, "", claim_id, claim.patient_ref, claim.provider_ref)
        f_emb = executor.submit(_run_embedding, "", claim_id)
        
        for future in concurrent.futures.as_completed([f_xgb, f_iso, f_graph, f_emb]):
            try:
                results.append(future.result())
            except Exception as e:
                logger.error(f"Parallel AI task failed: {e}")

    # Process AI Results
    df_feat_for_shap = None
    for res in results:
        if not res: continue
        if res.get("type") == "xgboost":
            db.add(ModelScore(claim_id=claim_id, model_type="xgboost", score=res["score"]))
            for feat, val in res.get("shap", []):
                db.add(ShapExplanation(claim_id=claim_id, feature=feat, contribution_value=val))
        elif res.get("type") == "isolation_forest":
            db.add(ModelScore(claim_id=claim_id, model_type="isolation_forest", score=res["score"]))
            
    db.commit()

    # 4. LLM Helper
    if settings.GEMINI_API_KEY:
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Richer prompt combining new features
            prompt = (
                f"Summarize healthcare claim {claim.id} for patient {claim.patient_ref} "
                f"with billed amount {claim.billed_amount}.\n"
                f"Features gathered: {list(consolidated_features.keys())[:10]}...\n"
                f"Identify potential issues based on validation, duplicates, and benchmarks without stating definitive fraud."
            )
            response = model.generate_content(prompt)
        except Exception as e:
            logger.error(f"LLM Helper failed: {e}")

    # 5. Risk Aggregation & Evidence Coverage
    try:
        from .aggregation_service import generate_risk_aggregate
        generate_risk_aggregate(db, claim_id)
        
        # Calculate Evidence Coverage
        agg = db.query(RiskAggregate).filter_by(claim_id=claim_id).first()
        if agg:
            coverage = 0.0
            total_signals = 6.0
            if consolidated_features.get("provider_status") == 1: coverage += 1
            if consolidated_features.get("benchmark_status") == 1: coverage += 1
            if consolidated_features.get("procedure_valid") == 1: coverage += 1
            if doc and doc.ocr_text: coverage += 1
            if len(results) >= 4: coverage += 2 # ML & Graph ran
            
            agg.evidence_coverage = coverage / total_signals
            db.commit()
    except Exception as e:
        logger.error(f"Risk aggregation failed: {e}")

    # 6. Case Routing
    agg = db.query(RiskAggregate).filter_by(claim_id=claim_id).first()
    if agg:
        # Route based on Risk Thresholds (using config)
        from .aggregation_service import get_active_weights
        
        if agg.aggregate_score > 0.75:
            claim.status = "action_required" # High Risk
        elif agg.aggregate_score > 0.4:
            claim.status = "manual_review" # Medium Risk
        elif consolidated_features.get("procedure_valid") == 0:
            claim.status = "rejected" # Hard fail
        else:
            claim.status = "approved" # Low Risk Auto-adjudicate
    else:
        claim.status = "action_required"

    audit = AuditLog(action="PIPELINE_COMPLETE", entity_type="CLAIM", entity_id=str(claim_id))
    db.add(audit)
    db.commit()
