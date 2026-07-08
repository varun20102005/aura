import numpy as np
from sqlalchemy.orm import Session
from ..models.core import ModelRegistry, ModelScore, DriftReport
from .notification_service import notify_drift_breach

def calculate_psi(expected: np.ndarray, actual: np.ndarray, buckets: int = 10, eps: float = 1e-4) -> float:
    """
    Calculate the Population Stability Index (PSI) between two distributions.
    Both expected and actual are 1D arrays of values (e.g. scores between 0 and 1).
    """
    if len(expected) == 0 or len(actual) == 0:
        return 0.0

    # Create percentiles based on the expected distribution
    breakpoints = np.linspace(0, 100, buckets + 1)
    bins = np.percentile(expected, breakpoints)
    
    # Ensure edges cover all data points
    bins[0] -= 1e-5
    bins[-1] += 1e-5

    # Calculate frequencies in each bucket
    expected_freq = np.histogram(expected, bins)[0]
    actual_freq = np.histogram(actual, bins)[0]

    # Convert to percentages
    expected_pct = expected_freq / len(expected)
    actual_pct = actual_freq / len(actual)

    # Add epsilon to avoid divide by zero and log of zero
    expected_pct = np.where(expected_pct == 0, eps, expected_pct)
    actual_pct = np.where(actual_pct == 0, eps, actual_pct)

    # Calculate PSI
    psi_values = (actual_pct - expected_pct) * np.log(actual_pct / expected_pct)
    return float(np.sum(psi_values))

def compute_model_drift(db: Session, threshold: float = 0.20):
    """
    Compute PSI for the currently active models.
    """
    active_models = db.query(ModelRegistry).filter_by(status="active").all()
    
    for model in active_models:
        # Fetch the most recent 1000 scores as 'actual' (live distribution)
        recent_scores = db.query(ModelScore.score).filter_by(model_type=model.model_type)\
            .order_by(ModelScore.generated_at.desc()).limit(1000).all()
            
        if len(recent_scores) < 100:
            continue # Need sufficient data to compute drift
            
        actual_vals = np.array([s[0] for s in recent_scores])
        
        # We don't have explicit training baselines in DB, so we'll use the OLDEST 1000 scores as the 'expected' baseline
        baseline_scores = db.query(ModelScore.score).filter_by(model_type=model.model_type)\
            .order_by(ModelScore.generated_at.asc()).limit(1000).all()
            
        if len(baseline_scores) < 100:
            continue
            
        expected_vals = np.array([s[0] for s in baseline_scores])
        
        # Calculate PSI
        psi = calculate_psi(expected_vals, actual_vals)
        
        flagged = 1 if psi > threshold else 0
        
        # Record DriftReport
        report = DriftReport(
            model_id=model.id,
            feature_or_prediction=f"{model.model_type}_prediction_score",
            drift_metric="PSI",
            value=psi,
            threshold=threshold,
            flagged=flagged
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        
        # Trigger Notification if flagged
        if flagged:
            notify_drift_breach(db, model.id, "PSI", psi, threshold)
            
    return {"status": "success"}
