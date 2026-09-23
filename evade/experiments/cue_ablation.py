"""
Experiment: Cue Ablation
RQ3 — Which contextual cues are responsible for evaluation awareness?

Progressively strips cues and measures how awareness and behavioral shift degrade.
Implements the 6-level cue hierarchy + the roadmap's adversarial perturbation pipeline.
"""
from __future__ import annotations

from tqdm import tqdm

from benchmark.generator import build_context
from benchmark.perturbations import PERTURBATION_PIPELINE, apply_perturbations
from benchmark.schema import (
    AwarenessResult, BehavioralShiftResult, Condition, CueLevel, EVADEPair,
)
from experiments.awareness import run_awareness_experiment, summarize_awareness
from experiments.behavioral_shift import run_behavioral_shift_experiment
from metrics.awareness import cue_dependence
from models.base import ModelAdapter


def run_cue_ablation(
    adapter: ModelAdapter,
    pairs: list[EVADEPair],
    db_path: str = "results/evade_results.db",
) -> dict:
    """
    Run the full 6-level cue ablation (roadmap §6).

    For each cue level, generates fresh pairs with that cue level's context,
    runs both awareness classification and behavioral shift measurement.

    Returns a nested dict: { cue_level → { "awareness": summary, "shift": summary } }
    """
    results_by_level: dict = {}

    for cue_level in CueLevel:
        # Re-wrap pairs at this specific cue level
        rebucketed = []
        for pair in pairs:
            eval_ctx = build_context(pair.task, Condition.EVALUATION, cue_level)
            dep_ctx  = build_context(pair.task, Condition.DEPLOYMENT,  cue_level)
            from benchmark.schema import EVADEPair as _P
            rebucketed.append(_P(task=pair.task, evaluation_context=eval_ctx, deployment_context=dep_ctx))

        print(f"\n[CueAblation] Level {cue_level.value} ({cue_level.name}) — {len(rebucketed)} pairs")

        awareness_results = run_awareness_experiment(adapter, rebucketed, cue_levels=[cue_level])
        shift_results     = run_behavioral_shift_experiment(adapter, rebucketed, db_path=db_path)

        from experiments.awareness import summarize_awareness
        from experiments.behavioral_shift import summarize_shifts

        results_by_level[cue_level.name] = {
            "cue_level": cue_level.value,
            "awareness": summarize_awareness(awareness_results),
            "shift":     summarize_shifts(shift_results),
        }

    # Compute Cue Dependence summary
    all_awareness: list[AwarenessResult] = []
    for level_data in results_by_level.values():
        pass  # Awareness results per level were computed inline

    # Compute CD = AA_explicit − AA_minimal across levels
    explicit_aa     = results_by_level.get(CueLevel.EXPLICIT.name, {}).get("awareness", {}).get("overall", {}).get("AA", float("nan"))
    naturalistic_aa = results_by_level.get(CueLevel.NATURALISTIC.name, {}).get("awareness", {}).get("overall", {}).get("AA", float("nan"))

    results_by_level["cue_dependence_cd"] = (
        explicit_aa - naturalistic_aa
        if explicit_aa == explicit_aa and naturalistic_aa == naturalistic_aa
        else float("nan")
    )

    return results_by_level


def run_perturbation_ablation(
    adapter: ModelAdapter,
    pairs: list[EVADEPair],
    db_path: str = "results/evade_results.db",
) -> dict:
    """
    Run the adversarial Evaluation Cue Perturbation pipeline (roadmap §8).

    Progressively applies: paraphrase → format_randomize → remove_metadata
    → remove_benchmark_names → naturalize → agent_context

    For each level of perturbation, measures awareness and shift.
    """
    results: dict = {}
    current_pairs = pairs

    for step in PERTURBATION_PIPELINE:
        print(f"[PerturbAblation] Applying step: {step.name}")
        perturbed_pairs = []
        for pair in current_pairs:
            new_eval = apply_perturbations(pair.evaluation_context, steps=[step.name])
            new_dep  = apply_perturbations(pair.deployment_context,  steps=[step.name])
            from benchmark.schema import EVADEPair as _P
            perturbed_pairs.append(_P(
                task=pair.task,
                evaluation_context=new_eval,
                deployment_context=new_dep,
            ))

        awareness = run_awareness_experiment(adapter, perturbed_pairs)
        from experiments.awareness import summarize_awareness
        results[step.name] = summarize_awareness(awareness)
        current_pairs = perturbed_pairs

    return results
