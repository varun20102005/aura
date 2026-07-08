from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.core import User
from ..routers.auth import require_role
from ..services.benchmark_service import get_best_benchmark

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/cost-benchmark")
def get_cost_benchmark(
    procedure_code: str = Query(...),
    provider_id: str = Query(None),
    region: str = Query(None),
    billed_amount: float = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Officer", "Investigator", "Supervisor", "Auditor", "Admin"]))
):
    benchmark = get_best_benchmark(
        db=db, 
        procedure_code=procedure_code, 
        provider_id=provider_id, 
        region=region
    )
    
    if not benchmark:
        return {
            "status": "UNAVAILABLE",
            "reason_code": "NO_PROCEDURE_BENCHMARK",
            "message": "A reliable benchmark cannot be calculated because insufficient historical data exists for this procedure code.",
            "tier_used": None,
            "sample_size": 0,
            "median": None,
            "p25": None,
            "p75": None,
            "iqr": None,
            "analysis": None
        }
    
    response = {
        "status": "AVAILABLE",
        "reason_code": None,
        "message": None,
        "tier_used": benchmark.confidence,
        "sample_size": benchmark.sample_size,
        "median": benchmark.median,
        "p25": benchmark.p25,
        "p75": benchmark.p75,
        "iqr": benchmark.iqr,
    }
    
    if billed_amount is not None:
        # Check if outlier: > P75 + 1.5 * IQR or < P25 - 1.5 * IQR
        upper_bound = benchmark.p75 + (1.5 * benchmark.iqr)
        lower_bound = benchmark.p25 - (1.5 * benchmark.iqr)
        
        is_outlier = billed_amount > upper_bound or billed_amount < lower_bound
        deviation = 0.0
        if billed_amount > upper_bound:
            deviation = billed_amount - upper_bound
        elif billed_amount < lower_bound:
            deviation = lower_bound - billed_amount
            
        response["analysis"] = {
            "billed_amount": billed_amount,
            "is_outlier": is_outlier,
            "deviation_from_band": deviation,
            "upper_bound": upper_bound,
            "lower_bound": lower_bound
        }
        
    return response
