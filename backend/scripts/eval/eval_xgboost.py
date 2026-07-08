import pandas as pd
import numpy as np
import xgboost as xgb
import json
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, 
    roc_auc_score, average_precision_score, confusion_matrix, brier_score_loss
)

def evaluate_baseline():
    df = pd.read_csv("data/synthetic_claims.csv")
    
    df_features = pd.get_dummies(df, columns=['procedure_code'])
    features = [col for col in df_features.columns if col.startswith('procedure_code_') or col == 'billed_amount']
    
    X = df_features[features]
    y = df_features['is_fraud']
    
    # Train/Test split (80/20)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    # Train model
    model = xgb.XGBClassifier(n_estimators=100, max_depth=4, learning_rate=0.1, random_state=42)
    model.fit(X_train, y_train)
    
    y_pred_prob = model.predict_proba(X_test)[:, 1]
    y_pred = model.predict(X_test)
    
    # Core Metrics
    pr_auc = average_precision_score(y_test, y_pred_prob)
    brier = brier_score_loss(y_test, y_pred_prob)
    
    # Threshold Analysis
    thresholds = [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
    threshold_results = {}
    for t in thresholds:
        preds = (y_pred_prob >= t).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_test, preds).ravel()
        p = precision_score(y_test, preds, zero_division=0)
        r = recall_score(y_test, preds, zero_division=0)
        f1 = f1_score(y_test, preds, zero_division=0)
        threshold_results[str(t)] = {
            "precision": float(p), "recall": float(r), "f1": float(f1),
            "fp": int(fp), "fn": int(fn)
        }
        
    tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()
    
    report = {
        "metrics": {
            "accuracy": float(accuracy_score(y_test, y_pred)),
            "precision": float(precision_score(y_test, y_pred)),
            "recall": float(recall_score(y_test, y_pred)),
            "f1": float(f1_score(y_test, y_pred)),
            "roc_auc": float(roc_auc_score(y_test, y_pred_prob)),
            "pr_auc": float(pr_auc),
            "brier_score": float(brier),
            "false_positive_rate": float(fp / (fp + tn)),
            "false_negative_rate": float(fn / (fn + tp))
        },
        "thresholds": threshold_results
    }
    
    with open("xgboost_eval_out.json", "w") as f:
        json.dump(report, f, indent=2)

if __name__ == "__main__":
    evaluate_baseline()
