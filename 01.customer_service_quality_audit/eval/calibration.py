# eval/calibration.py
from __future__ import annotations
import pickle
from typing import Dict
import numpy as np
from sklearn.isotonic import IsotonicRegression

# Fit isotonic regression per dimension to calibrate model outputs → human labels (1–5)

def fit_calibrator(model_scores: np.ndarray, human_labels: np.ndarray) -> Dict[str, IsotonicRegression]:
    # model_scores, human_labels: shape (N,3)
    calibs = {}
    dims = ["professionalism", "friendliness", "resolution_effectiveness"]
    for i, d in enumerate(dims):
        ir = IsotonicRegression(out_of_bounds="clip")
        ir.fit(model_scores[:, i], human_labels[:, i])
        calibs[d] = ir
    return calibs

def apply_calibrator(calibs: Dict[str, IsotonicRegression], scores: np.ndarray) -> np.ndarray:
    dims = ["professionalism", "friendliness", "resolution_effectiveness"]
    out = []
    for i, d in enumerate(dims):
        out.append(calibs[d].transform(scores[:, i]))
    return np.vstack(out).T

def save_calibrator(calibs: Dict[str, IsotonicRegression], path: str):
    with open(path, "wb") as f:
        pickle.dump(calibs, f)

def load_calibrator(path: str) -> Dict[str, IsotonicRegression]:
    with open(path, "rb") as f:
        return pickle.load(f)
