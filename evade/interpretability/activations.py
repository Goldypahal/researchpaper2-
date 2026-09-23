"""
Interpretability — Activation Extraction
Phase 5 / RQ6 — Can internal representations predict evaluation-conditioned behavioral shifts?

Extracts hidden states from local HuggingFace models for probe training.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

from benchmark.schema import Condition, EVADEPair
from models.local import HuggingFaceAdapter


@dataclass
class ActivationRecord:
    task_id: str
    model: str
    condition: str
    cue_level: int
    domain: str
    hidden_states: list[np.ndarray]  # one array per layer, shape [hidden_dim]
    behavioral_shift: Optional[float] = None  # EBS composite for this pair (filled later)


def extract_activations(
    adapter: HuggingFaceAdapter,
    pairs: list[EVADEPair],
    layers: list[int] | None = None,
    save_path: str | Path | None = None,
) -> list[ActivationRecord]:
    """
    Extract hidden states for all pairs (evaluation + deployment conditions).

    Args:
        adapter: Must be a HuggingFaceAdapter (local model).
        pairs: EVADE-Bench pairs.
        layers: Which transformer layers to extract (default: all).
        save_path: Optional .npz path to persist activations.

    Returns:
        List of ActivationRecord objects.
    """
    records: list[ActivationRecord] = []

    for pair in pairs:
        for ctx, cond in [
            (pair.evaluation_context, Condition.EVALUATION),
            (pair.deployment_context, Condition.DEPLOYMENT),
        ]:
            hs = adapter.get_hidden_states(ctx.system_prompt, ctx.user_prompt, layers=layers)
            records.append(ActivationRecord(
                task_id=pair.task.task_id,
                model=adapter.model_id,
                condition=cond.value,
                cue_level=ctx.cue_level.value,
                domain=pair.task.domain.value,
                hidden_states=hs,
            ))

    if save_path:
        _save_activations(records, save_path)

    return records


def _save_activations(records: list[ActivationRecord], path: str | Path) -> None:
    """Save activations as a compressed .npz file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    arrays = {}
    metadata = []
    for i, rec in enumerate(records):
        for j, layer_hs in enumerate(rec.hidden_states):
            arrays[f"rec_{i}_layer_{j}"] = layer_hs
        metadata.append({
            "index":     i,
            "task_id":   rec.task_id,
            "model":     rec.model,
            "condition": rec.condition,
            "cue_level": rec.cue_level,
            "domain":    rec.domain,
            "n_layers":  len(rec.hidden_states),
            "behavioral_shift": rec.behavioral_shift,
        })

    np.savez_compressed(str(path), **arrays)
    meta_path = path.with_suffix(".meta.json")
    with meta_path.open("w") as f:
        json.dump(metadata, f)
    print(f"[Activations] Saved {len(records)} records to {path}")


def load_activations(npz_path: str | Path) -> list[ActivationRecord]:
    """Load activations from .npz + .meta.json files."""
    npz_path = Path(npz_path)
    data = np.load(str(npz_path))
    with npz_path.with_suffix(".meta.json").open() as f:
        metadata = json.load(f)

    records = []
    for meta in metadata:
        i = meta["index"]
        n_layers = meta["n_layers"]
        hs = [data[f"rec_{i}_layer_{j}"] for j in range(n_layers)]
        records.append(ActivationRecord(
            task_id=meta["task_id"],
            model=meta["model"],
            condition=meta["condition"],
            cue_level=meta["cue_level"],
            domain=meta["domain"],
            hidden_states=hs,
            behavioral_shift=meta.get("behavioral_shift"),
        ))
    return records


def get_layer_matrix(
    records: list[ActivationRecord],
    layer_idx: int = -1,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """
    Build (X, y_condition, labels) for probe training from a specific layer.

    Args:
        records: List of ActivationRecord.
        layer_idx: Layer index (-1 = last layer).

    Returns:
        X: [n_samples, hidden_dim]
        y: [n_samples] binary (1=EVALUATION, 0=DEPLOYMENT)
        task_ids: [n_samples]
    """
    X, y, task_ids = [], [], []
    for rec in records:
        if not rec.hidden_states:
            continue
        layer = rec.hidden_states[layer_idx]
        X.append(layer)
        y.append(1 if rec.condition == Condition.EVALUATION.value else 0)
        task_ids.append(rec.task_id)

    return np.stack(X), np.array(y), task_ids
