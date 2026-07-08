import sys
import json
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.core import Claim, ModelScore, DuplicateMatch, GraphRelationship, ProviderRiskProfile, RiskWeightConfig
from app.services.aggregation_service import normalize_components, generate_risk_aggregate, get_active_weights

def test_aggregation():
    db = SessionLocal()
    try:
        claims = db.query(Claim).limit(10).all()
        results = []
        weights = get_active_weights(db)
        
        for c in claims:
            # Re-generate properly
            generate_risk_aggregate(db, c.id)
            
            # Manually calculate
            norms = normalize_components(db, c)
            manual_agg = (
                norms["fraud_score"] * weights["fraud"] +
                norms["anomaly_score"] * weights["anomaly"] +
                norms["duplicate_score"] * weights["duplicate"] +
                norms["graph_score"] * weights["graph"] +
                norms["cost_score"] * weights["cost"] +
                norms["provider_score"] * weights["provider"]
            )
            
            # Backend aggregate
            # The function `generate_risk_aggregate` saves it to RiskAggregate
            from app.models.core import RiskAggregate
            backend_agg = db.query(RiskAggregate).filter_by(claim_id=c.id).first()
            backend_score = backend_agg.aggregate_score if backend_agg else 0.0
            
            diff = abs(manual_agg - backend_score)
            
            results.append({
                "Claim ID": c.id,
                "Component Scores": norms,
                "Weights": weights,
                "Manual Aggregate": round(manual_agg, 4),
                "Backend Aggregate": round(backend_score, 4),
                "Difference": round(diff, 6),
                "PASS/FAIL": "PASS" if diff < 0.0001 else "FAIL"
            })
            
        with open("risk_aggregate_out.json", "w") as f:
            json.dump(results, f, indent=2)
            
    finally:
        db.close()

if __name__ == "__main__":
    test_aggregation()
