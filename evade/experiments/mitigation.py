"""
Experiment: Mitigation
Phase 6 / RQ7 — Can randomized evaluation environments reduce evaluation-conditioned behavior?

Implements the Evaluation Randomization Layer (roadmap §16) and measures
EBS_before vs EBS_after.
"""
from __future__ import annotations

import random

from benchmark.schema import CueLevel, EVADEPair
from benchmark.perturbations import apply_perturbations, PERTURBATION_PIPELINE
from experiments.behavioral_shift import run_behavioral_shift_experiment, summarize_shifts
from metrics.behavioral_shift import aggregate_ebs
from models.base import ModelAdapter


def apply_randomization_layer(
    pairs: list[EVADEPair],
    seed: int = 42,
) -> list[EVADEPair]:
    """
    Evaluation Randomization Layer (roadmap §16).

    Pipeline:
        Benchmark → Task randomizer → Prompt naturalizer → Metadata remover
               → Format randomizer → Model

    Applies all perturbation steps to both evaluation and deployment contexts.
    """
    random.seed(seed)
    all_steps = [s.name for s in PERTURBATION_PIPELINE]
    mitigated = []
    for pair in pairs:
        new_eval = apply_perturbations(pair.evaluation_context, steps=all_steps)
        new_dep  = apply_perturbations(pair.deployment_context,  steps=all_steps)
        from benchmark.schema import EVADEPair as _P
        mitigated.append(_P(
            task=pair.task,
            evaluation_context=new_eval,
            deployment_context=new_dep,
        ))
    return mitigated


def run_mitigation_experiment(
    adapter: ModelAdapter,
    pairs: list[EVADEPair],
    db_path: str = "results/evade_results.db",
) -> dict:
    """
    Compare EBS before and after applying the Evaluation Randomization Layer.

    Result format:
        {
          "before": { EBS aggregate },
          "after":  { EBS aggregate },
          "reduction": { delta per component }
        }
    """
    print("[Mitigation] Running BEFORE-mitigation baseline…")
    results_before = run_behavioral_shift_experiment(adapter, pairs, db_path=db_path)
    agg_before     = aggregate_ebs(results_before)

    print("[Mitigation] Applying Evaluation Randomization Layer…")
    mitigated_pairs = apply_randomization_layer(pairs)

    print("[Mitigation] Running AFTER-mitigation experiment…")
    results_after = run_behavioral_shift_experiment(adapter, mitigated_pairs, db_path=db_path)
    agg_after     = aggregate_ebs(results_after)

    # Reduction in EBS composite
    def safe_delta(before_key, after_key):
        b = agg_before.get(before_key, {}).get("mean", float("nan"))
        a = agg_after.get(after_key,  {}).get("mean", float("nan"))
        return b - a  # positive = mitigation improved (reduced shift)

    reduction = {
        "ebs_composite":   safe_delta("ebs_composite",   "ebs_composite"),
        "delta_refusal":   safe_delta("delta_refusal",   "delta_refusal"),
        "delta_verbosity": safe_delta("delta_verbosity", "delta_verbosity"),
        "delta_accuracy":  safe_delta("delta_accuracy",  "delta_accuracy"),
    }

    return {
        "model":    adapter.model_id,
        "n_pairs":  len(pairs),
        "before":   agg_before,
        "after":    agg_after,
        "reduction": reduction,
    }
