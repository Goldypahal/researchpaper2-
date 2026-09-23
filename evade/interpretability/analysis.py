"""
Interpretability — Analysis
Evaluates probe accuracy per layer and generates representation → shift correlation.
Also implements cross-model transfer analysis (roadmap §18).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
from scipy import stats

from interpretability.activations import ActivationRecord, get_layer_matrix
from interpretability.probes import ProbeResult, probe_all_layers


def probe_accuracy_by_layer(
    records: list[ActivationRecord],
    probe_type: str = "logistic",
) -> dict[str, list[ProbeResult]]:
    """
    Sweep all layers for both condition and shift targets.

    Returns:
        {
          "condition": [ProbeResult per layer],
          "shift":     [ProbeResult per layer],
        }
    """
    return {
        "condition": probe_all_layers(records, target="condition", probe_type=probe_type),
        "shift":     probe_all_layers(records, target="shift",     probe_type=probe_type),
    }


def representation_shift_correlation(
    records: list[ActivationRecord],
    layer_idx: int = -1,
) -> dict:
    """
    Test the correlation between the evaluation representation strength
    (logit of the condition probe) and the observed behavioral shift.

    This is the core of roadmap §9:
        EvaluationRepresentation → BehavioralShift

    Requires records with `behavioral_shift` filled in.
    """
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import Pipeline

    valid = [r for r in records if r.behavioral_shift is not None]
    if len(valid) < 10:
        return {"error": "Insufficient records with behavioral_shift"}

    X, y_cond, _ = get_layer_matrix(valid, layer_idx=layer_idx)
    y_shift = np.array([r.behavioral_shift for r in valid])

    # Train a logistic probe on the condition label
    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("lr",     LogisticRegression(max_iter=1000)),
    ])
    pipe.fit(X, y_cond)

    # Get probability of "EVALUATION" as representation strength
    eval_prob = pipe.predict_proba(X)[:, 1]

    # Correlate with behavioral shift
    pearson_r, pearson_p  = stats.pearsonr(eval_prob, y_shift)
    spearman_r, spearman_p = stats.spearmanr(eval_prob, y_shift)

    return {
        "n":              len(valid),
        "layer":          layer_idx,
        "pearson_r":      float(pearson_r),
        "pearson_p":      float(pearson_p),
        "spearman_r":     float(spearman_r),
        "spearman_p":     float(spearman_p),
        "interpretation": (
            "Strong positive correlation: models that more strongly represent the evaluation "
            "context show larger behavioral shifts."
            if pearson_r > 0.3
            else "Weak or no correlation between evaluation representation and behavioral shift."
        ),
    }


def cross_model_transfer(
    train_records: list[ActivationRecord],
    test_records:  list[ActivationRecord],
    layer_idx: int = -1,
    probe_type: str = "logistic",
) -> dict:
    """
    Train a probe on models A, B, C and test on model D.
    Answers roadmap §18: is evaluation awareness model-specific or generalizable?

    Returns: accuracy and AUC on the held-out model.
    """
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import Pipeline
    from sklearn.metrics import accuracy_score, roc_auc_score

    X_train, y_train, _ = get_layer_matrix(train_records, layer_idx=layer_idx)
    X_test,  y_test,  _ = get_layer_matrix(test_records,  layer_idx=layer_idx)

    if X_train.shape[1] != X_test.shape[1]:
        return {"error": "Hidden dimensions differ between models — cannot transfer directly."}

    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("clf",    LogisticRegression(max_iter=1000) if probe_type == "logistic"
                   else __import__("sklearn.neural_network", fromlist=["MLPClassifier"]).MLPClassifier()),
    ])
    pipe.fit(X_train, y_train)

    y_pred  = pipe.predict(X_test)
    y_proba = pipe.predict_proba(X_test)[:, 1]

    train_models = list(set(r.model for r in train_records))
    test_models  = list(set(r.model for r in test_records))

    return {
        "train_models": train_models,
        "test_model":   test_models,
        "accuracy":     float(accuracy_score(y_test, y_pred)),
        "auc":          float(roc_auc_score(y_test, y_proba)),
        "n_train":      len(train_records),
        "n_test":       len(test_records),
        "interpretation": (
            "Probe generalizes across models — suggests a model-independent signature "
            "of evaluation-aware behavior."
            if accuracy_score(y_test, y_pred) > 0.65
            else "Probe does not generalize — evaluation awareness may be model-specific."
        ),
    }
