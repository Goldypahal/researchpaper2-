"""
Experiment: Behavioral Shift
Phase 3 / RQ2 — Does evaluation awareness causally alter model behavior?

Runs paired inference (evaluation vs deployment context) and computes EBS metrics.
"""
from __future__ import annotations

from tqdm import tqdm

from benchmark.schema import BehavioralShiftResult, CueLevel, Domain, EVADEPair, ModelResponse
from experiments.runner import ExperimentRunner
from metrics.behavioral_shift import aggregate_ebs, compute_ebs, js_divergence
from models.base import ModelAdapter


def run_behavioral_shift_experiment(
    adapter: ModelAdapter,
    pairs: list[EVADEPair],
    db_path: str = "results/evade_results.db",
    show_progress: bool = True,
) -> list[BehavioralShiftResult]:
    """
    Run paired behavioral shift experiment.

    For every task pair, generates a response under evaluation context and
    under deployment context, then computes EBS.

    Returns: list of BehavioralShiftResult, one per pair.
    """
    runner = ExperimentRunner(
        adapter=adapter,
        db_path=db_path,
        experiment_type="behavioral_shift",
    )

    pairs_iter = tqdm(pairs, desc=f"BehavShift [{adapter.model_id}]") if show_progress else pairs
    shift_results: list[BehavioralShiftResult] = []

    for pair in pairs_iter:
        eval_resp, dep_resp = runner.run_pair(pair)
        ebs = compute_ebs(eval_resp, dep_resp)
        shift_results.append(ebs)

    return shift_results


def summarize_shifts(results: list[BehavioralShiftResult]) -> dict:
    """Aggregate EBS by model, domain, cue level."""
    summary: dict = {
        "overall": aggregate_ebs(results),
        "by_domain": {},
        "by_cue_level": {},
    }

    for dom in Domain:
        sub = [r for r in results if r.domain == dom]
        if sub:
            summary["by_domain"][dom.value] = aggregate_ebs(sub)

    for cl in CueLevel:
        sub = [r for r in results if r.cue_level == cl.value]
        if sub:
            summary["by_cue_level"][cl.name] = aggregate_ebs(sub)

    return summary
