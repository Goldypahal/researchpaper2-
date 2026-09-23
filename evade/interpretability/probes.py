"""
Interpretability — Linear Probes
Phase 5 / RQ6 — Predicts evaluation vs deployment condition and behavioral shift
from hidden state representations.

Trains: Logistic Regression (linear probe), MLP.
(Roadmap §9, §19, §27)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from interpretability.activations import ActivationRecord, get_layer_matrix


@dataclass
class ProbeResult:
    model_name: str
    layer_idx: int
    probe_type: str         # "logistic" | "mlp"
    target: str             # "condition" | "shift"
    accuracy: float
    auc: float
    cv_accuracy_mean: float
    cv_accuracy_std: float
    coefficients: Optional[np.ndarray] = None   # for logistic probe


def train_condition_probe(
    records: list[ActivationRecord],
    layer_idx: int = -1,
    probe_type: str = "logistic",
    n_cv_folds: int = 5,
    seed: int = 42,
) -> ProbeResult:
    """
    Train a probe to predict EVALUATION vs DEPLOYMENT from hidden states.
    (Roadmap §9 — linear probe)

    Uses stratified k-fold cross-validation for unbiased evaluation.
    """
    X, y, _ = get_layer_matrix(records, layer_idx=layer_idx)

    if len(set(y)) < 2:
        raise ValueError("Need both EVALUATION and DEPLOYMENT samples for probe training.")

    # Build probe pipeline
    if probe_type == "logistic":
        clf = Pipeline([
            ("scaler", StandardScaler()),
            ("probe",  LogisticRegression(max_iter=1000, C=1.0, random_state=seed)),
        ])
    elif probe_type == "mlp":
        clf = Pipeline([
            ("scaler", StandardScaler()),
            ("probe",  MLPClassifier(hidden_layer_sizes=(256,), max_iter=300, random_state=seed)),
        ])
    else:
        raise ValueError(f"Unknown probe_type: {probe_type}")

    # Cross-validated accuracy
    cv = StratifiedKFold(n_splits=n_cv_folds, shuffle=True, random_state=seed)
    cv_scores = cross_val_score(clf, X, y, cv=cv, scoring="accuracy")

    # Fit on full dataset for held-out AUC
    clf.fit(X, y)
    y_pred  = clf.predict(X)
    y_proba = clf.predict_proba(X)[:, 1]

    coef = None
    if probe_type == "logistic":
        coef = clf.named_steps["probe"].coef_[0]

    return ProbeResult(
        model_name=records[0].model if records else "unknown",
        layer_idx=layer_idx,
        probe_type=probe_type,
        target="condition",
        accuracy=float(accuracy_score(y, y_pred)),
        auc=float(roc_auc_score(y, y_proba)),
        cv_accuracy_mean=float(np.mean(cv_scores)),
        cv_accuracy_std=float(np.std(cv_scores)),
        coefficients=coef,
    )


def train_shift_prediction_probe(
    records: list[ActivationRecord],
    layer_idx: int = -1,
    probe_type: str = "logistic",
    shift_threshold: float = 0.05,
    seed: int = 42,
) -> ProbeResult:
    """
    Train a probe to predict WHETHER the model will exhibit a behavioral shift,
    from its hidden state BEFORE generating the answer.

    This is the "predict the shift before the answer" experiment (roadmap §19).

    Requires that records have `behavioral_shift` filled in (from EBS computation).
    Records without behavioral_shift are skipped.
    """
    valid = [r for r in records if r.behavioral_shift is not None]
    if not valid:
        raise ValueError("No records with behavioral_shift filled. Run EBS computation first.")

    X_all, _, task_ids = get_layer_matrix(valid, layer_idx=layer_idx)
    y_all = np.array([
        1 if abs(r.behavioral_shift) > shift_threshold else 0
        for r in valid
    ])

    if len(set(y_all)) < 2:
        # All same class — trivial result
        return ProbeResult(
            model_name=valid[0].model,
            layer_idx=layer_idx,
            probe_type=probe_type,
            target="shift",
            accuracy=float(np.mean(y_all == 0)),  # majority baseline
            auc=0.5,
            cv_accuracy_mean=float(np.mean(y_all == 0)),
            cv_accuracy_std=0.0,
        )

    if probe_type == "logistic":
        clf = Pipeline([
            ("scaler", StandardScaler()),
            ("probe",  LogisticRegression(max_iter=1000, C=1.0, random_state=seed)),
        ])
    else:
        clf = Pipeline([
            ("scaler", StandardScaler()),
            ("probe",  MLPClassifier(hidden_layer_sizes=(256,), max_iter=300, random_state=seed)),
        ])

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
    cv_scores = cross_val_score(clf, X_all, y_all, cv=cv, scoring="accuracy")
    clf.fit(X_all, y_all)

    y_pred  = clf.predict(X_all)
    y_proba = clf.predict_proba(X_all)[:, 1]

    coef = None
    if probe_type == "logistic":
        coef = clf.named_steps["probe"].coef_[0]

    return ProbeResult(
        model_name=valid[0].model,
        layer_idx=layer_idx,
        probe_type=probe_type,
        target="shift",
        accuracy=float(accuracy_score(y_all, y_pred)),
        auc=float(roc_auc_score(y_all, y_proba)),
        cv_accuracy_mean=float(np.mean(cv_scores)),
        cv_accuracy_std=float(np.std(cv_scores)),
        coefficients=coef,
    )


def probe_all_layers(
    records: list[ActivationRecord],
    target: str = "condition",  # "condition" | "shift"
    probe_type: str = "logistic",
) -> list[ProbeResult]:
    """Sweep all layers and return probe accuracy per layer."""
    if not records or not records[0].hidden_states:
        return []

    n_layers = len(records[0].hidden_states)
    results  = []
    for layer_idx in range(n_layers):
        try:
            if target == "condition":
                r = train_condition_probe(records, layer_idx=layer_idx, probe_type=probe_type)
            else:
                r = train_shift_prediction_probe(records, layer_idx=layer_idx, probe_type=probe_type)
            results.append(r)
        except Exception as e:
            print(f"  Layer {layer_idx} failed: {e}")
    return results
