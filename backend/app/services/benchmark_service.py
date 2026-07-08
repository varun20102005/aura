import pandas as pd
from sqlalchemy.orm import Session
from ..models.core import Claim, CostBenchmark
import logging

logger = logging.getLogger(__name__)

def compute_benchmarks(db: Session, sample_size_threshold: int = 30):
    """
    Computes and saves cost benchmarks using a hierarchical fallback.
    Tiers:
    1. Procedure + Provider + Region (High Confidence)
    2. Procedure + Region (Medium Confidence)
    3. Procedure only (Low Confidence)
    """
    # Fetch all historical claims
    # Currently Claim model doesn't store region, we'll assume a global 'ALL' region for MVP.
    claims = db.query(Claim.procedure_code, Claim.provider_ref.label('provider_id'), Claim.billed_amount).all()
    
    if not claims:
        logger.info("No claims found to build benchmarks.")
        return

    df = pd.DataFrame(claims)
    # Add a mock region since it's required by TRD but not in base Claim schema
    df['region'] = 'ALL' 
    
    # Clear old benchmarks
    db.query(CostBenchmark).delete()
    
    # Tier 1: Procedure + Provider + Region
    t1 = df.groupby(['procedure_code', 'provider_id', 'region']).agg(
        median=('billed_amount', 'median'),
        p25=('billed_amount', lambda x: x.quantile(0.25)),
        p75=('billed_amount', lambda x: x.quantile(0.75)),
        sample_size=('billed_amount', 'count')
    ).reset_index()
    t1['iqr'] = t1['p75'] - t1['p25']
    t1['confidence'] = 'High'
    
    # Filter by threshold
    t1_valid = t1[t1['sample_size'] >= sample_size_threshold]

    # Tier 2: Procedure + Region
    t2 = df.groupby(['procedure_code', 'region']).agg(
        median=('billed_amount', 'median'),
        p25=('billed_amount', lambda x: x.quantile(0.25)),
        p75=('billed_amount', lambda x: x.quantile(0.75)),
        sample_size=('billed_amount', 'count')
    ).reset_index()
    t2['iqr'] = t2['p75'] - t2['p25']
    t2['confidence'] = 'Medium'
    t2['provider_id'] = None
    
    t2_valid = t2[t2['sample_size'] >= sample_size_threshold]

    # Tier 3: Procedure Only
    t3 = df.groupby(['procedure_code']).agg(
        median=('billed_amount', 'median'),
        p25=('billed_amount', lambda x: x.quantile(0.25)),
        p75=('billed_amount', lambda x: x.quantile(0.75)),
        sample_size=('billed_amount', 'count')
    ).reset_index()
    t3['iqr'] = t3['p75'] - t3['p25']
    t3['confidence'] = 'Low'
    t3['provider_id'] = None
    t3['region'] = None
    
    t3_valid = t3 # Tier 3 is the ultimate fallback, we keep it even if < threshold, but mark low conf
    
    # Combine valid tiers
    all_benchmarks = pd.concat([t1_valid, t2_valid, t3_valid], ignore_index=True)
    
    # Persist to DB
    for _, row in all_benchmarks.iterrows():
        bm = CostBenchmark(
            procedure_code=row['procedure_code'],
            region=row.get('region'),
            provider_id=row.get('provider_id'),
            median=float(row['median']),
            p25=float(row['p25']),
            p75=float(row['p75']),
            iqr=float(row['iqr']),
            sample_size=int(row['sample_size']),
            confidence=row['confidence']
        )
        db.add(bm)
    
    db.commit()
    logger.info(f"Computed and saved {len(all_benchmarks)} benchmarks.")

def get_best_benchmark(db: Session, procedure_code: str, provider_id: str = None, region: str = None):
    """
    Retrieves the most specific benchmark available matching the criteria.
    Hierarchical fallback:
    1. procedure + provider + region
    2. procedure + region
    3. procedure
    """
    if provider_id and region:
        b1 = db.query(CostBenchmark).filter_by(
            procedure_code=procedure_code, provider_id=provider_id, region=region
        ).first()
        if b1: return b1
        
    if region:
        b2 = db.query(CostBenchmark).filter_by(
            procedure_code=procedure_code, region=region, provider_id=None
        ).first()
        if b2: return b2
        
    # Ultimate fallback
    b3 = db.query(CostBenchmark).filter_by(
        procedure_code=procedure_code, region=None, provider_id=None
    ).first()
    return b3
