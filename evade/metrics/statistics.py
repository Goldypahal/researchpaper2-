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


# ─────────────────────────── Mixed-Effects & Hierarchical Models ─────────────

def linear_mixed_effects_model(
    df: pd.DataFrame,
    formula: Optional[str] = None,
    group_col: str = "task_id",
) -> dict:
    """
    Gaussian Linear Mixed-Effects Model (LMM) with random task intercepts:
        Outcome ~ Predictors + (1 | Task)
    Appropriate for continuous behavioral metrics:
        delta_completion_tokens, verbosity, hedging_density, latency_ms.
    (Note: smf.mixedlm is a linear Gaussian model, NOT a logistic model).
    """
    try:
        import statsmodels.formula.api as smf
    except ImportError:
        warnings.warn("statsmodels not available; skipping linear mixed-effects model.")
        return {}

    if formula is None:
        formula = "outcome ~ condition + model + domain + cue_level + condition:model"

    try:
        model = smf.mixedlm(formula, df, groups=df[group_col])
        result = model.fit(disp=False)
        ci = result.conf_int()
        return {
            "model_type": "LinearMixedModel_Gaussian",
            "formula": formula,
            "params": result.params.to_dict(),
            "bse": result.bse.to_dict(),
            "pvalues": result.pvalues.to_dict(),
            "ci_95": {k: [float(ci.loc[k, 0]), float(ci.loc[k, 1])] for k in ci.index},
            "aic": float(result.aic),
            "bic": float(result.bic),
            "converged": bool(result.converged),
            "n_observations": int(result.nobs),
        }
    except Exception as e:
        warnings.warn(f"Linear mixed-effects model failed: {e}")
        return {"error": str(e)}


def binary_cluster_logistic_regression(
    df: pd.DataFrame,
    formula: Optional[str] = None,
    group_col: str = "task_id",
) -> dict:
    """
    Cluster-robust binomial logistic regression or GEE for binary outcomes:
        Logit(P(Outcome=1)) = beta_0 + beta_1 X_1 + ...
    Appropriate for binary behavioral outcomes:
        refusal (0/1), accuracy (0/1).
    Accounts for within-task clustering across paired conditions.
    """
    try:
        import statsmodels.api as sm
        import statsmodels.formula.api as smf
    except ImportError:
        warnings.warn("statsmodels not available; skipping binary logistic regression.")
        return {}

    if formula is None:
        formula = "outcome ~ cue_level + C(domain)"

    # Try Generalized Estimating Equations (GEE) with Binomial family first
    try:
        gee = smf.gee(formula, groups=group_col, data=df, family=sm.families.Binomial())
        result = gee.fit()
        ci = result.conf_int()
        odds_ratios = {k: float(np.exp(v)) for k, v in result.params.to_dict().items()}
        return {
            "model_type": "Binomial_GEE_ClusterRobust",
            "formula": formula,
            "params": result.params.to_dict(),
            "odds_ratios": odds_ratios,
            "bse": result.bse.to_dict(),
            "pvalues": result.pvalues.to_dict(),
            "ci_95": {k: [float(ci.loc[k, 0]), float(ci.loc[k, 1])] for k in ci.index},
            "converged": bool(result.converged),
            "n_observations": int(result.nobs),
        }
    except Exception:
        # Fallback to smf.logit with cluster-robust standard errors
        try:
            logit = smf.logit(formula, data=df)
            result = logit.fit(disp=False, cov_type="cluster", cov_kwds={"groups": df[group_col]})
            ci = result.conf_int()
            odds_ratios = {k: float(np.exp(v)) for k, v in result.params.to_dict().items()}
            return {
                "model_type": "Logit_ClusterRobust",
                "formula": formula,
                "params": result.params.to_dict(),
                "odds_ratios": odds_ratios,
                "bse": result.bse.to_dict(),
                "pvalues": result.pvalues.to_dict(),
                "ci_95": {k: [float(ci.loc[k, 0]), float(ci.loc[k, 1])] for k in ci.index},
                "prsquared": float(getattr(result, "prsquared", 0.0)),
                "converged": bool(result.converged),
                "n_observations": int(result.nobs),
            }
        except Exception as e:
            warnings.warn(f"Binary cluster logistic regression failed: {e}")
            return {"error": str(e)}


def fit_task_level_dose_response(
    df: pd.DataFrame,
    outcome_col: str = "delta_completion_tokens",
    group_col: str = "task_id",
) -> dict:
    """
    Task-level mixed-effects model testing the primary scientific dose-response hypothesis:
        Y_ij = beta_0 + beta_1 CueLevel_j + beta_2 Domain_i + u_i + eps_ij
    Directly tests whether cue salience increases behavioral shift across all
    underlying observations (e.g. N=600 or N=500 paired shifts), preserving
    the paired task random effect u_i.
    """
    try:
        import statsmodels.formula.api as smf
    except ImportError:
        warnings.warn("statsmodels not available; skipping dose-response mixed model.")
        return {}

    formula = f"{outcome_col} ~ cue_level + C(domain)"
    try:
        model = smf.mixedlm(formula, df, groups=df[group_col])
        result = model.fit(disp=False)
        ci = result.conf_int()

        cue_beta = float(result.params.get("cue_level", 0.0))
        cue_se = float(result.bse.get("cue_level", 0.0))
        cue_pval = float(result.pvalues.get("cue_level", 1.0))
        cue_ci = [float(ci.loc["cue_level", 0]), float(ci.loc["cue_level", 1])] if "cue_level" in ci.index else [0.0, 0.0]

        return {
            "outcome": outcome_col,
            "formula": formula,
            "beta_cue_level": cue_beta,
            "se_cue_level": cue_se,
            "p_value_cue_level": cue_pval,
            "ci_95_cue_level": cue_ci,
            "all_params": result.params.to_dict(),
            "all_pvalues": result.pvalues.to_dict(),
            "aic": float(result.aic),
            "bic": float(result.bic),
            "converged": bool(result.converged),
            "n_observations": int(result.nobs),
            "n_tasks": int(df[group_col].nunique()),
        }
    except Exception as e:
        warnings.warn(f"Task-level dose-response model failed for {outcome_col}: {e}")
        return {"error": str(e), "outcome": outcome_col}


def mixed_effects_regression(df: pd.DataFrame) -> dict:
    """
    Backward-compatible wrapper for linear_mixed_effects_model.
    Note: Fits Gaussian Linear Mixed-Effects Model (LMM), appropriate for continuous metrics.
    For binary outcomes (refusal, accuracy), use binary_cluster_logistic_regression.
    """
    return linear_mixed_effects_model(df)


# ─────────────────────────── Multiple Testing Correction ─────────────────────

def adjust_pvalues(
    p_values: Union[List[float], Dict[str, float]],
    method: str = "holm",
) -> Union[List[float], Dict[str, float]]:
    """
    Multiple-testing correction for families of secondary statistical tests.
    Methods:
      - 'holm': Holm-Bonferroni step-down (controls Family-Wise Error Rate - FWER)
      - 'fdr_bh' or 'bh': Benjamini-Hochberg (controls False Discovery Rate - FDR)
      - 'bonferroni': Standard Bonferroni single-step correction
    """
    is_dict = isinstance(p_values, dict)
    if is_dict:
        keys = list(p_values.keys())
        raw_p = [float(p_values[k]) for k in keys]
    else:
        keys = []
        raw_p = [float(p) for p in p_values]

    if not raw_p:
        return {} if is_dict else []

    try:
        from statsmodels.stats.multitest import multipletests
        sm_method = "fdr_bh" if method.lower() in {"bh", "fdr", "fdr_bh"} else method.lower()
        _, adj_p, _, _ = multipletests(raw_p, method=sm_method)
        adj_list = [float(p) for p in adj_p]
    except Exception:
        # Standalone pure-Python fallback
        n = len(raw_p)
        if method.lower() == "bonferroni":
            adj_list = [min(1.0, p * n) for p in raw_p]
        elif method.lower() in {"bh", "fdr", "fdr_bh"}:
            # Benjamini-Hochberg step-up
            sorted_indices = sorted(range(n), key=lambda i: raw_p[i])
            adj_list = [0.0] * n
            cum_min = 1.0
            for rank_rev, idx in enumerate(reversed(sorted_indices)):
                rank = n - rank_rev
                val = (raw_p[idx] * n) / rank
                cum_min = min(cum_min, val)
                adj_list[idx] = min(1.0, cum_min)
        else:
            # Holm-Bonferroni step-down (default)
            sorted_indices = sorted(range(n), key=lambda i: raw_p[i])
            adj_list = [0.0] * n
            cum_max = 0.0
            for rank, idx in enumerate(sorted_indices):
                val = raw_p[idx] * (n - rank)
                cum_max = max(cum_max, val)
                adj_list[idx] = min(1.0, cum_max)

    if is_dict:
        return {k: adj_list[i] for i, k in enumerate(keys)}
    return adj_list



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
