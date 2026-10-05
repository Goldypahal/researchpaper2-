"""
Unit tests for EVADE Statistical Methods:
- Linear Mixed-Effects Model (LMM) for continuous metrics
- Cluster-Robust Binomial / GEE Logistic Regression for binary outcomes
- Task-Level Dose-Response Hierarchical Model
- Multiple-Testing Corrections (Holm-Bonferroni, Benjamini-Hochberg FDR)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd
import pytest

from metrics.statistics import (
    linear_mixed_effects_model,
    binary_cluster_logistic_regression,
    fit_task_level_dose_response,
    adjust_pvalues,
)


@pytest.fixture
def mock_panel_data():
    """Generates synthetic 100-task x 6-condition panel dataset."""
    rng = np.random.default_rng(42)
    records = []
    domains = ["math", "reasoning", "coding", "safety", "psychological"]
    for t_idx in range(50):
        t_id = f"task_{t_idx:04d}"
        dom = domains[t_idx % len(domains)]
        task_intercept = rng.normal(0, 10.0)

        for cue in range(6):
            # True linear dose response slope = 3.5 tok per cue level
            delta_comp = 5.0 + 3.5 * cue + task_intercept + rng.normal(0, 5.0)
            p_ref = 1.0 / (1.0 + np.exp(-( -2.0 + 0.4 * cue )))
            ref = 1 if rng.uniform() < p_ref else 0
            records.append({
                "task_id": t_id,
                "domain": dom,
                "cue_level": cue,
                "delta_completion_tokens": delta_comp,
                "refusal": ref,
            })
    return pd.DataFrame(records)


def test_task_level_dose_response(mock_panel_data):
    """Verifies that task-level mixed model accurately detects the true dose-response slope."""
    res = fit_task_level_dose_response(mock_panel_data, outcome_col="delta_completion_tokens")
    assert "beta_cue_level" in res
    assert res["converged"] is True
    assert res["n_observations"] == 300
    assert res["n_tasks"] == 50
    # Expected slope is ~3.5
    assert 2.5 <= res["beta_cue_level"] <= 4.5
    assert res["p_value_cue_level"] < 0.001


def test_binary_cluster_logistic(mock_panel_data):
    """Verifies cluster-robust logistic regression / GEE for binary outcomes."""
    res = binary_cluster_logistic_regression(
        mock_panel_data,
        formula="refusal ~ cue_level + C(domain)",
        group_col="task_id",
    )
    assert res["converged"] is True
    assert "cue_level" in res["params"]
    assert res["odds_ratios"]["cue_level"] > 1.0  # Positive slope


def test_linear_mixed_effects_continuous(mock_panel_data):
    """Verifies Gaussian LMM on continuous metric."""
    res = linear_mixed_effects_model(
        mock_panel_data,
        formula="delta_completion_tokens ~ cue_level + C(domain)",
        group_col="task_id",
    )
    assert res["converged"] is True
    assert "cue_level" in res["params"]
    assert res["pvalues"]["cue_level"] < 0.01


def test_adjust_pvalues_methods():
    raw_p = [0.001, 0.01, 0.04, 0.05, 0.12]

    # Holm-Bonferroni step down
    holm = adjust_pvalues(raw_p, method="holm")
    assert holm[0] == pytest.approx(0.005, abs=1e-4)
    assert holm[1] == pytest.approx(0.04, abs=1e-4)
    assert all(h >= r for h, r in zip(holm, raw_p))

    # Benjamini-Hochberg FDR
    bh = adjust_pvalues(raw_p, method="fdr_bh")
    assert bh[0] == pytest.approx(0.005, abs=1e-4)
    assert bh[1] == pytest.approx(0.025, abs=1e-4)
    assert all(b >= r for b, r in zip(bh, raw_p))

    # Dictionary input
    dict_p = {"test1": 0.01, "test2": 0.04}
    adj_dict = adjust_pvalues(dict_p, method="holm")
    assert "test1" in adj_dict and "test2" in adj_dict
    assert adj_dict["test1"] == pytest.approx(0.02, abs=1e-4)
