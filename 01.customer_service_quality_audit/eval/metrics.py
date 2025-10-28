# eval/metrics.py
from typing import Dict
import numpy as np
from sklearn.metrics import cohen_kappa_score
from scipy.stats import pearsonr

def agreement_and_corr(human: np.ndarray, model: np.ndarray) -> Dict[str, float]:
    human_i = human.astype(int)
    model_i = np.rint(model).astype(int)
    kappa = cohen_kappa_score(human_i, model_i)
    r, _ = pearsonr(human.astype(float), model.astype(float))
    return {"kappa": float(kappa), "pearson_r": float(r)}

def triple_metrics(human_trip: np.ndarray, model_trip: np.ndarray) -> Dict[str, Dict[str, float]]:
    # Expect shape (N, 3)
    out = {}
    dims = ["professionalism", "friendliness", "resolution_effectiveness"]
    for i, d in enumerate(dims):
        out[d] = agreement_and_corr(human_trip[:, i], model_trip[:, i])
    return out
