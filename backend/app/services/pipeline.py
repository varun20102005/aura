import os
import time
import json
import pandas as pd
import numpy as np
import joblib
from sqlalchemy.orm import Session
from ..models.core import Claim, ClaimDocument, ModelScore, ShapExplanation, DuplicateMatch, AuditLog, GraphRelationship
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

def process_claim_pipeline(claim_id: int, db: Session):
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        return
    
    doc = db.query(ClaimDocument).filter(ClaimDocument.claim_id == claim_id).first()
    
    # 1. OCR
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

    # 2. ML Inference (XGBoost & Isolation Forest)
    try:
        xgb_model, xgb_path = _load_model_from_registry(db, "xgboost", "ml_models/xgboost_fraud.json")
        iso_model, iso_path = _load_model_from_registry(db, "isolation_forest", "ml_models/isolation_forest.joblib")
        features = _get_model_features()
        
        # Build feature vector for this single claim
        # We need to map procedure_code to the one-hot columns
        feat_dict = {f: 0 for f in features}
        if "billed_amount" in feat_dict:
            feat_dict["billed_amount"] = claim.billed_amount
        proc_col = f"procedure_code_{claim.procedure_code}"
        if proc_col in feat_dict:
            feat_dict[proc_col] = 1
            
        df_feat = pd.DataFrame([feat_dict])
        
        xgb_pred = float(xgb_model.predict_proba(df_feat)[0][1])
        iso_pred = float(iso_model.decision_function(df_feat)[0]) # anomaly score
        
        # Save scores
        db.add(ModelScore(claim_id=claim_id, model_type="xgboost", score=xgb_pred))
        db.add(ModelScore(claim_id=claim_id, model_type="isolation_forest", score=iso_pred))
        db.commit()
        
        # 3. Explainability (SHAP)
        explainer = shap.TreeExplainer(xgb_model)
        shap_values = explainer.shap_values(df_feat)
        for i, col in enumerate(features):
            val = float(shap_values[0][i])
            if abs(val) > 0.01: # only store significant features
                db.add(ShapExplanation(claim_id=claim_id, feature=col, contribution_value=val))
        db.commit()
    except Exception as e:
        logger.error(f"ML step failed: {e}")

    # 4. Duplicate Match (RapidFuzz)
    try:
        past_claims = db.query(Claim).filter(Claim.id != claim_id).limit(100).all()
        for pc in past_claims:
            if claim.procedure_code == pc.procedure_code:
                sim = rapidfuzz.fuzz.ratio(str(claim.billed_amount), str(pc.billed_amount))
                if sim > 95:
                    db.add(DuplicateMatch(claim_id=claim_id, matched_claim_id=pc.id, similarity_score=sim, method="fuzzy"))
        db.commit()
    except Exception as e:
        logger.error(f"Duplicate step failed: {e}")

    # 4b. Graph Relationship (NetworkX)
    try:
        # Simple extraction: patient and provider relationship
        # In a real app we'd build the graph in-memory, detect cliques/hubs, then save
        G = nx.Graph()
        G.add_edge(claim.patient_ref, claim.provider_ref, claim_id=claim_id)
        # Store relationships based on this claim
        db.add(GraphRelationship(
            entity_1=claim.patient_ref, 
            entity_2=claim.provider_ref, 
            relationship_type="PATIENT_PROVIDER", 
            metadata_json={"claim_id": claim_id}
        ))
        db.commit()
    except Exception as e:
        logger.error(f"Graph step failed: {e}")

    # 4c. Procedure & Code Validation
    try:
        from .validation_service import run_procedure_validation
        run_procedure_validation(db, claim_id)
    except Exception as e:
        logger.error(f"Procedure validation failed: {e}")
        db.rollback()

    # 5. LLM Helper
    if settings.GEMINI_API_KEY:
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = f"Summarize healthcare claim {claim.id} for patient {claim.patient_ref} with billed amount {claim.billed_amount}."
            response = model.generate_content(prompt)
        except Exception as e:
            logger.error(f"LLM Helper failed: {e}")

    # 6. Generate Hybrid Embeddings
    try:
        from .embedding_service import generate_claim_embedding
        generate_claim_embedding(db, claim_id)
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        db.rollback()

    # 7. Risk Aggregation
    try:
        from .aggregation_service import generate_risk_aggregate
        generate_risk_aggregate(db, claim_id)
    except Exception as e:
        logger.error(f"Risk aggregation failed: {e}")
        db.rollback()

    # Mark as ready for investigation
    claim.status = "action_required"
    audit = AuditLog(action="PIPELINE_COMPLETE", entity_type="CLAIM", entity_id=str(claim_id))
    db.add(audit)
    db.commit()
