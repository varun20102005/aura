import os
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.ensemble import IsolationForest
import joblib

def train():
    print("Loading synthetic dataset...")
    df = pd.read_csv("data/synthetic_claims.csv")
    
    # Feature engineering for the ML models
    # We will use 'billed_amount' and one-hot encode 'procedure_code'
    # In a real app, provider/patient history would also be features
    
    df_features = pd.get_dummies(df, columns=['procedure_code'])
    features = [col for col in df_features.columns if col.startswith('procedure_code_') or col == 'billed_amount']
    
    X = df_features[features]
    y = df_features['is_fraud']
    
    print(f"Training XGBoost Fraud Classifier on {len(X)} samples...")
    # Train supervised XGBoost
    xgb_model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        random_state=42
    )
    xgb_model.fit(X, y)
    
    print("Training Isolation Forest Anomaly Detector...")
    # Train unsupervised Isolation Forest
    iso_model = IsolationForest(
        n_estimators=100,
        contamination=0.05,
        random_state=42
    )
    iso_model.fit(X)
    
    # Save the models and feature list
    os.makedirs("ml_models", exist_ok=True)
    
    print("Saving models to ml_models/...")
    xgb_model.save_model("ml_models/xgboost_fraud.json")
    joblib.dump(iso_model, "ml_models/isolation_forest.joblib")
    joblib.dump(features, "ml_models/model_features.joblib")
    
    print("Training complete.")

if __name__ == "__main__":
    train()
