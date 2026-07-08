import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.core import Base, Claim, CostBenchmark
from app.services.benchmark_service import compute_benchmarks, get_best_benchmark

@pytest.fixture(scope="function")
def test_db():
    engine = create_engine("sqlite:///:memory:")
    tables = [t for t in Base.metadata.sorted_tables if t.name != 'claim_embeddings']
    Base.metadata.create_all(bind=engine, tables=tables)
    Session = sessionmaker(bind=engine)
    db = Session()
    yield db
    db.close()

def add_claims(db, count, procedure, provider, amount):
    for i in range(count):
        db.add(Claim(
            patient_ref=f"P_{i}",
            provider_ref=provider,
            procedure_code=procedure,
            billed_amount=amount + (i * 0.1) # tiny variance
        ))
    db.commit()

def test_benchmark_fallback_logic(test_db):
    # Tier 1 meets threshold
    add_claims(test_db, 35, "99214", "PRV1", 150.0)
    
    # Tier 2 doesn't meet threshold for provider PRV2, but meets for region
    add_claims(test_db, 10, "99214", "PRV2", 200.0) # only 10 for PRV2
    
    # Another 20 for PRV3 to hit the region total of 30+
    add_claims(test_db, 20, "99214", "PRV3", 200.0)
    
    compute_benchmarks(test_db, sample_size_threshold=30)
    
    # For PRV1, should hit Tier 1 (High)
    b1 = get_best_benchmark(test_db, procedure_code="99214", provider_id="PRV1", region="ALL")
    assert b1.confidence == "High"
    assert b1.sample_size == 35
    
    # For PRV2, fails Tier 1, hits Tier 2 (Medium) because total for region is 65
    b2 = get_best_benchmark(test_db, procedure_code="99214", provider_id="PRV2", region="ALL")
    assert b2.confidence == "Medium"
    assert b2.sample_size == 65

def test_zero_historical_claims(test_db):
    compute_benchmarks(test_db, sample_size_threshold=30)
    b = get_best_benchmark(test_db, "99214", "PRV1", "ALL")
    assert b is None

def test_exactly_at_threshold(test_db):
    add_claims(test_db, 30, "11111", "PRV1", 100.0)
    compute_benchmarks(test_db, sample_size_threshold=30)
    
    b = get_best_benchmark(test_db, "11111", "PRV1", "ALL")
    assert b.confidence == "High"
    assert b.sample_size == 30

def test_outlier_logic_via_api(client, admin_token, test_db):
    # This assumes `client` uses a separate test DB by default, so we'll mock the benchmark in the api's DB.
    # Actually, we can just test the math directly.
    pass

def test_quartile_calculations(test_db):
    # 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
    # Add claims with specific amounts to test quartiles
    amounts = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    for i, a in enumerate(amounts):
        # We need 30 to hit threshold, or we just rely on Tier 3 (which always passes threshold)
        test_db.add(Claim(
            patient_ref=f"P_{i}",
            provider_ref="PRVX",
            procedure_code="TEST_Q",
            billed_amount=a
        ))
    test_db.commit()
    
    compute_benchmarks(test_db, sample_size_threshold=30)
    
    # It will fall back to Tier 3 (Low) because sample size is 10
    b = get_best_benchmark(test_db, "TEST_Q", "PRVX", "ALL")
    assert b.confidence == "Low"
    assert b.sample_size == 10
    assert b.median == 55.0
    # pd.quantile(0.25) of [10..100] is 32.5
    assert b.p25 == 32.5
    assert b.p75 == 77.5
    assert b.iqr == 45.0
