import pytest

def compute_hybrid_score(fuzzy_score, semantic_score, weight):
    return (weight * semantic_score) + ((1.0 - weight) * fuzzy_score)

def test_hybrid_scoring_math():
    f_score = 0.8  # 80% fuzzy match
    s_score = 0.6  # 60% semantic match
    
    # 50/50 weighting
    hybrid_50 = compute_hybrid_score(f_score, s_score, 0.5)
    assert hybrid_50 == 0.7
    
    # 80% semantic weighting
    hybrid_80s = compute_hybrid_score(f_score, s_score, 0.8)
    # (0.8 * 0.6) + (0.2 * 0.8) = 0.48 + 0.16 = 0.64
    assert pytest.approx(hybrid_80s, 0.001) == 0.64
    
    # 100% fuzzy weighting
    hybrid_100f = compute_hybrid_score(f_score, s_score, 0.0)
    assert hybrid_100f == 0.8


