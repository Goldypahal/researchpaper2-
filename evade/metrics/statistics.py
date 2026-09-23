"""
Statistical analysis utilities for EVADE.
Implements: paired bootstrap CIs, McNemar's test, permutation tests,
mixed-effects logistic regression (roadmap §14).
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import chi2_contingency


@dataclass
class BootstrapResult:
    mean: float
    ci_lower: float
    ci_upper: float
    std: float
    n: int
    alpha: float = 0.05


def paired_bootstrap_ci(
    eval_vals: list[float],
    deploy_vals: list[float],
    n_bootstrap: int = 10_000,
    alpha: float = 0.05,
    seed: int = 42,
) -> BootstrapResult:
    """
    Paired bootstrap confidence interval for the difference (eval − deploy).
    Implements roadmap §14 requirement for paired bootstrap CIs.
    """
    rng = np.random.default_rng(seed)
    eval_arr   = np.array(eval_vals,   dtype=float)
    deploy_arr = np.array(deploy_vals, dtype=float)
    diffs = eval_arr - deploy_arr
    n = len(diffs)
    observed_mean = float(np.mean(diffs))

    boot_means = np.empty(n_bootstrap)
    for i in range(n_bootstrap):
        idx = rng.integers(0, n, size=n)
        boot_means[i] = np.mean(diffs[idx])

    ci_lower = float(np.percentile(boot_means, 100 * (alpha / 2)))
    ci_upper = float(np.percentile(boot_means, 100 * (1 - alpha / 2)))
    return BootstrapResult(
        mean=observed_mean,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        std=float(np.std(diffs)),
        n=n,
        alpha=alpha,
    )


@dataclass
class McNemarResult:
    statistic: float
    p_value: float
    n_discordant: int
    odds_ratio: Optional[float] = None


def mcnemar_test(
    eval_correct: list[bool],
    deploy_correct: list[bool],
    exact: bool = True,
) -> McNemarResult:
    """
    McNemar's test for paired binary outcomes.
    Used to test whether accuracy shifts between eval/deploy are significant.
    (Roadmap §14)
    """
    a = b = c = d = 0
    for ec, dc in zip(eval_correct, deploy_correct):
        if ec and dc:     d += 1   # both correct
        elif ec and not dc: b += 1  # eval correct, deploy wrong
        elif not ec and dc: c += 1  # eval wrong, deploy correct
        else:               a += 1  # both wrong

    n_discordant = b + c
    if n_discordant == 0:
        return McNemarResult(statistic=0.0, p_value=1.0, n_discordant=0)

    if exact:
        # Exact binomial test
        result = stats.binomtest(b, n=n_discordant, p=0.5)
        statistic = float(result.statistic)
        p_value   = float(result.pvalue)
    else:
        # Chi-squared approximation
        statistic = (abs(b - c) - 1) ** 2 / (b + c)
        p_value   = float(1 - stats.chi2.cdf(statistic, df=1))

    or_ = b / c if c > 0 else float("inf")
    return McNemarResult(statistic=statistic, p_value=p_value, n_discordant=n_discordant, odds_ratio=or_)


@dataclass
class PermutationResult:
    observed_stat: float
    p_value: float
    n_permutations: int


def permutation_test(
    eval_vals: list[float],
    deploy_vals: list[float],
    n_permutations: int = 10_000,
    seed: int = 42,
) -> PermutationResult:
    """
    Paired permutation test for the mean difference (eval − deploy).
    (Roadmap §14)
    """
    rng = np.random.default_rng(seed)
    eval_arr   = np.array(eval_vals, dtype=float)
    deploy_arr = np.array(deploy_vals, dtype=float)
    diffs = eval_arr - deploy_arr
    observed = float(np.mean(diffs))

    count = 0
    for _ in range(n_permutations):
        signs = rng.choice([-1, 1], size=len(diffs))
        perm_mean = float(np.mean(diffs * signs))
        if abs(perm_mean) >= abs(observed):
            count += 1

    return PermutationResult(
        observed_stat=observed,
        p_value=count / n_permutations,
        n_permutations=n_permutations,
    )


def mixed_effects_regression(df: pd.DataFrame) -> dict:
    """
    Mixed-effects logistic regression:
        Behavior ~ EvaluationCondition + Model + Domain + CueLevel
                 + EvaluationCondition×Model + (1|Task)

    Requires columns: condition, model, domain, cue_level, task_id,
                      outcome (0/1 binary — e.g., is_correct or is_refusal).

    Returns: dict with coefficients, p-values, AIC, BIC.
    (Roadmap §14)
    """
    try:
        import statsmodels.formula.api as smf
    except ImportError:
        warnings.warn("statsmodels not available; skipping mixed-effects regression.")
        return {}

    required = {"condition", "model", "domain", "cue_level", "task_id", "outcome"}
    missing  = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns for regression: {missing}")

    formula = (
        "outcome ~ condition + model + domain + cue_level "
        "+ condition:model"
    )
    try:
        glm = smf.mixedlm(formula, df, groups=df["task_id"])
        result = glm.fit(disp=False)
        return {
            "params":    result.params.to_dict(),
            "pvalues":   result.pvalues.to_dict(),
            "aic":       result.aic,
            "bic":       result.bic,
            "converged": result.converged,
        }
    except Exception as e:
        warnings.warn(f"Mixed-effects regression failed: {e}")
        return {"error": str(e)}


def cohen_d(group1: list[float], group2: list[float]) -> float:
    """Effect size (Cohen's d) for two groups."""
    a1 = np.array(group1, dtype=float)
    a2 = np.array(group2, dtype=float)
    pooled_std = np.sqrt((np.var(a1, ddof=1) + np.var(a2, ddof=1)) / 2)
    return float((np.mean(a1) - np.mean(a2)) / pooled_std) if pooled_std > 0 else 0.0


def summarize_statistics(
    eval_vals: list[float],
    deploy_vals: list[float],
    name: str = "metric",
) -> dict:
    """
    Run the full statistical battery for a metric pair.
    Returns a summary dict suitable for table rendering.
    """
    boot = paired_bootstrap_ci(eval_vals, deploy_vals)
    perm = permutation_test(eval_vals, deploy_vals)

    eval_correct   = [v >= 0.5 for v in eval_vals]
    deploy_correct = [v >= 0.5 for v in deploy_vals]
    mc = mcnemar_test(eval_correct, deploy_correct)

    d = cohen_d(eval_vals, deploy_vals)

    return {
        "metric": name,
        "mean_diff": boot.mean,
        "ci_lower":  boot.ci_lower,
        "ci_upper":  boot.ci_upper,
        "p_bootstrap": None,  # CIs encode significance
        "p_permutation": perm.p_value,
        "p_mcnemar":     mc.p_value,
        "cohen_d":       d,
        "n":             boot.n,
    }
