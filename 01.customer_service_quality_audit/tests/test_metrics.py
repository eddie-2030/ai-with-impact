# tests/test_metrics.py
import numpy as np
from eval.metrics import agreement_and_corr

def test_agreement_corr_basic():
    human = np.array([1,2,3,4,5])
    model = np.array([1.2,2.0,3.2,3.9,4.8])
    out = agreement_and_corr(human, model)
    assert -1.0 <= out["kappa"] <= 1.0
    assert -1.0 <= out["pearson_r"] <= 1.0
