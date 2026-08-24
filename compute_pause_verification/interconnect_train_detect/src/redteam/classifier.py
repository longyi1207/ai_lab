"""RandomForest classifier over `RedteamWindowFeatures`, matching Rahman &
Tajdari's §4.2 model choice: 400 trees, no max depth, class weights
adjusted inversely to sample count. They also tried XGBoost (close
runner-up) and SVM-RBF/logistic regression (worse); we only implement RF
here since it's what they report as best and it's what our headline
numbers would be compared against.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from .features import RedteamWindowFeatures

FEATURE_COLUMNS = [
    "mean_power_w", "mean_util_pct",
    "cv_power", "cv_util",
    "autocorr1_power", "autocorr1_util",
    "periodicity_power", "periodicity_util",
    "cumulative_energy_j", "power_mem_corr",
    "first_30s_mem_delta_mb", "time_to_mem_plateau_s",
]


def to_matrix(feats: list[RedteamWindowFeatures]) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Returns (X, y, names). Rows with `is_training is None` (non-ML /
    "other" workloads) are dropped — matches the paper's binary framing.
    """
    rows = [f for f in feats if f.is_training is not None]
    X = np.array([[getattr(f, c) for c in FEATURE_COLUMNS] for f in rows], dtype=np.float64)
    y = np.array([1 if f.is_training else 0 for f in rows], dtype=np.int64)
    names = [f.name for f in rows]
    return X, y, names


@dataclass
class TrainResult:
    n_train: int
    n_pos: int  # training-labeled windows
    n_neg: int  # not-training-labeled windows
    feature_importance: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def train_classifier(X: np.ndarray, y: np.ndarray, seed: int = 0):
    from sklearn.ensemble import RandomForestClassifier

    if len(np.unique(y)) < 2:
        raise ValueError(
            f"need both classes to train; got only {np.unique(y).tolist()} — "
            "benign corpus must include at least one train_ddp and one infer_dp/infer_tp run"
        )
    clf = RandomForestClassifier(
        n_estimators=400, max_depth=None, class_weight="balanced", random_state=seed,
    )
    clf.fit(X, y)
    result = TrainResult(
        n_train=len(y),
        n_pos=int((y == 1).sum()),
        n_neg=int((y == 0).sum()),
        feature_importance=dict(zip(FEATURE_COLUMNS, clf.feature_importances_.tolist())),
    )
    return clf, result


def evaluate(clf, X: np.ndarray, y: np.ndarray | None, names: list[str]) -> dict[str, Any]:
    """Score windows. `y=None` for the adversarial red-team set — we still
    know the ground-truth label from `is_training_label` upstream (it *is*
    training, disguised), the point is whether the classifier's *predicted
    P(training)* drops low enough to evade at a governance-relevant
    decision threshold (0.5 here; report the raw probability too so a
    reader can pick their own threshold, per the paper's point that the
    threshold is a policy choice, not a fixed constant).
    """
    proba = clf.predict_proba(X)[:, 1] if len(X) else np.array([])
    pred = (proba >= 0.5).astype(int)
    rows = [
        {"name": n, "p_training": float(p), "predicted_training": bool(p >= 0.5)}
        for n, p in zip(names, proba)
    ]
    out: dict[str, Any] = {"n_windows": len(rows), "rows": rows}
    if y is not None and len(y):
        acc = float((pred == y).mean())
        tp = int(((pred == 1) & (y == 1)).sum())
        fn = int(((pred == 0) & (y == 1)).sum())
        tn = int(((pred == 0) & (y == 0)).sum())
        fp = int(((pred == 1) & (y == 0)).sum())
        out.update(accuracy=acc, tp=tp, fn=fn, tn=tn, fp=fp)
    return out


def save(clf, path: str | Path) -> None:
    import joblib

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, path)


def load(path: str | Path):
    import joblib

    return joblib.load(path)
