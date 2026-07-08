import os
import sys
import argparse
import pandas as pd
from sklearn.metrics import roc_auc_score, precision_score, recall_score

# Add backend to path so we can import AURA modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.core import Base, Claim, ClaimDocument, ModelScore, RiskAggregate
from app.services.pipeline import process_claim_pipeline
from dataset_adapter import DatasetAdapter

def setup_isolated_db():
    """Spins up an isolated in-memory SQLite DB for evaluation."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    # Filter out Vector-dependent tables if testing with SQLite
    tables = [t for t in Base.metadata.sorted_tables if t.name != "claim_embeddings"]
    Base.metadata.create_all(bind=engine, tables=tables)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, SessionLocal()

def run_evaluation(csv_path: str, output_format: str = "markdown"):
    print(f"Loading dataset from {csv_path}...")
    engine, db = setup_isolated_db()
    
    adapter = DatasetAdapter(csv_path)
    raw_claims = adapter.load_data()
    
    print(f"Ingesting {len(raw_claims)} claims into isolated memory DB...")
    y_true = []
    claim_ids = []
    
    for c_data in raw_claims:
        true_label = c_data.pop("_eval_true_label")
        ocr_text = c_data.pop("_eval_ocr_text")
        y_true.append(true_label)
        
        claim = Claim(**c_data)
        db.add(claim)
        db.commit()
        db.refresh(claim)
        claim_ids.append(claim.id)
        
        if ocr_text:
            doc = ClaimDocument(claim_id=claim.id, file_path="eval.pdf", ocr_text=ocr_text, ocr_confidence=0.99)
            db.add(doc)
            db.commit()

    print("Running AURA ML Pipeline on eval dataset...")
    for cid in claim_ids:
        process_claim_pipeline(cid, db)
        
    print("Gathering predictions...")
    y_pred_xgb = []
    y_pred_agg = []
    
    for cid in claim_ids:
        xgb_score = db.query(ModelScore).filter_by(claim_id=cid, model_type="xgboost").first()
        agg_score = db.query(RiskAggregate).filter_by(claim_id=cid).first()
        
        y_pred_xgb.append(xgb_score.score if xgb_score else 0.0)
        y_pred_agg.append(agg_score.aggregate_score if agg_score else 0.0)
        
    print("Calculating metrics...")
    # Binarize predictions at 0.5 for precision/recall
    y_pred_xgb_bin = [1 if x >= 0.5 else 0 for x in y_pred_xgb]
    y_pred_agg_bin = [1 if x >= 0.7 else 0 for x in y_pred_agg] # High risk band
    
    # Safely calculate AUC (needs >1 class)
    try:
        xgb_auc = roc_auc_score(y_true, y_pred_xgb)
        agg_auc = roc_auc_score(y_true, y_pred_agg)
    except ValueError:
        xgb_auc = 0.0
        agg_auc = 0.0
        
    xgb_prec = precision_score(y_true, y_pred_xgb_bin, zero_division=0)
    xgb_rec = recall_score(y_true, y_pred_xgb_bin, zero_division=0)
    
    agg_prec = precision_score(y_true, y_pred_agg_bin, zero_division=0)
    agg_rec = recall_score(y_true, y_pred_agg_bin, zero_division=0)
    
    report = f"""# AURA Evaluation Report

## Dataset
- **Source**: `{csv_path}`
- **Records**: {len(raw_claims)}

## XGBoost Model (Base Fraud)
- **AUC-ROC**: {xgb_auc:.4f}
- **Precision**: {xgb_prec:.4f}
- **Recall**: {xgb_rec:.4f}

## AURA Risk Aggregation Engine (Phase 5)
- **AUC-ROC**: {agg_auc:.4f}
- **Precision**: {agg_prec:.4f}
- **Recall**: {agg_rec:.4f}

*Note: The Aggregation Engine uses a strict High-Risk cutoff (0.7) for binary classification metrics in this report, combining fraud, anomaly, similarity, graph, and cost signals.*
"""
    
    out_file = "evaluation_report.md"
    with open(out_file, "w") as f:
        f.write(report)
        
    print(f"Done. Report saved to {out_file}")
    db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run AURA Evaluation Pipeline")
    parser.add_argument("--dataset", type=str, required=False, default=r"C:\Users\cvaru\OneDrive\Desktop\auraaaaa\data\evaluation\dataset.csv", help="Path to CSV dataset")
    args = parser.parse_args()
    
    run_evaluation(args.dataset)
