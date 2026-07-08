import logging
import math
from sqlalchemy.orm import Session
from ..models.core import Claim, ModelScore, DuplicateMatch, GraphRelationship, CostBenchmark, ProviderRiskProfile, RiskAggregate, RiskWeightConfig, RiskThresholdConfig

logger = logging.getLogger(__name__)

def sigmoid(x):
    """Squashes unbounded anomaly scores into 0-1"""
    return 1 / (1 + math.exp(-x))

def get_active_weights(db: Session):
    weight_config = db.query(RiskWeightConfig).filter_by(is_active=1).first()
    if not weight_config:
        # Fallback to equal weighting if missing
        w = 1.0 / 6.0
        return {
            "version": "fallback",
            "fraud": w, "anomaly": w, "duplicate": w,
            "graph": w, "cost": w, "provider": w
        }
    return {
        "version": weight_config.version,
        "fraud": weight_config.fraud_weight,
        "anomaly": weight_config.anomaly_weight,
        "duplicate": weight_config.duplicate_weight,
        "graph": weight_config.graph_weight,
        "cost": weight_config.cost_weight,
        "provider": weight_config.provider_weight
    }

def normalize_components(db: Session, claim: Claim):
    """
    Extracts raw signals from the DB for a given claim and normalizes them into 0-1.
    """
    scores = db.query(ModelScore).filter_by(claim_id=claim.id).all()
    fraud_raw = next((s.score for s in scores if s.model_type == "xgboost"), 0.0)
    anomaly_raw = next((s.score for s in scores if s.model_type == "isolation_forest"), 0.0)
    
    # Normalize Fraud (XGBoost outputs prob 0-1 already usually, but bound it)
    n_fraud = max(0.0, min(1.0, fraud_raw))
    
    # Normalize Anomaly (IForest outputs unbounded, usually negative means anomaly)
    # We want higher score = higher risk. Let's invert and sigmoid.
    n_anomaly = sigmoid(-anomaly_raw)
    
    # Normalize Duplicate (Similarity is 0-1)
    duplicates = db.query(DuplicateMatch).filter_by(claim_id=claim.id).all()
    # RapidFuzz returns 0.0 to 100.0, so divide by 100.0 to normalize to 0.0-1.0
    n_duplicate = max([d.similarity_score for d in duplicates] + [0.0]) / 100.0
    
    # Normalize Graph (Number of relationships = proxy for graph risk, max out at 10 edges)
    edge_count = db.query(GraphRelationship).filter(
        (GraphRelationship.entity_1 == claim.provider_ref) | 
        (GraphRelationship.entity_2 == claim.provider_ref)
    ).count()
    n_graph = min(1.0, edge_count / 10.0)
    
    # Normalize Cost (Check deviation from median)
    # Get the best benchmark from our phase 1 service
    from .benchmark_service import get_best_benchmark
    benchmark = get_best_benchmark(db, claim.procedure_code, claim.provider_ref, "UNKNOWN")
    n_cost = 0.0
    if benchmark and benchmark.median > 0:
        ratio = claim.billed_amount / benchmark.median
        # If ratio is 1, risk is 0. If ratio is 3+, risk is 1.0.
        n_cost = max(0.0, min(1.0, (ratio - 1.0) / 2.0))
        
    # Normalize Provider (Risk score is already 0-1)
    provider_profile = db.query(ProviderRiskProfile).filter_by(provider_id=claim.provider_ref).first()
    n_provider = provider_profile.rolling_risk_score if provider_profile else 0.0
    
    return {
        "fraud_score": n_fraud,
        "anomaly_score": n_anomaly,
        "duplicate_score": n_duplicate,
        "graph_score": n_graph,
        "cost_score": n_cost,
        "provider_score": n_provider
    }

def generate_risk_aggregate(db: Session, claim_id: int):
    """
    Computes and saves the aggregate risk score for a claim.
    """
    claim = db.query(Claim).filter_by(id=claim_id).first()
    if not claim:
        return
        
    norms = normalize_components(db, claim)
    weights = get_active_weights(db)
    
    agg = (
        (norms["fraud_score"] * weights["fraud"]) +
        (norms["anomaly_score"] * weights["anomaly"]) +
        (norms["duplicate_score"] * weights["duplicate"]) +
        (norms["graph_score"] * weights["graph"]) +
        (norms["cost_score"] * weights["cost"]) +
        (norms["provider_score"] * weights["provider"])
    )
    
    # Delete old if exists
    db.query(RiskAggregate).filter_by(claim_id=claim_id).delete()
    
    record = RiskAggregate(
        claim_id=claim_id,
        fraud_score=norms["fraud_score"],
        anomaly_score=norms["anomaly_score"],
        duplicate_score=norms["duplicate_score"],
        graph_score=norms["graph_score"],
        cost_score=norms["cost_score"],
        provider_score=norms["provider_score"],
        aggregate_score=agg,
        weighting_version=weights["version"]
    )
    db.add(record)
    db.commit()
    logger.info(f"Aggregated risk for claim {claim_id}: {agg:.2f} (version: {weights['version']})")
