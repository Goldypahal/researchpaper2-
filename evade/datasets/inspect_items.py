"""
Audit and Inspection Tool for EVADE Dataset.
Renders items with side-by-side or sequential comparisons of all 6 conditions (C0-C5)
to verify that:
1. Question meaning is strictly preserved.
2. Ground truth is unaffected.
3. Framing cues match their operational condition definitions.
Saves a markdown audit report for human review.
"""

import json
import os
import random
import sys
from typing import List
from .schema import EVADEItem

DEFAULT_DATASET = os.path.join(
    os.path.dirname(__file__), "processed", "dev", "evade_pilot_200.jsonl"
)
AUDIT_OUTPUT = os.path.join(
    os.path.dirname(__file__), "processed", "dev", "pilot_audit_50.md"
)


def load_dataset(path: str = DEFAULT_DATASET) -> List[EVADEItem]:
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                items.append(EVADEItem.model_validate_json(line))
    return items


def audit_items(count: int = 50, seed: int = 42, dataset_path: str = DEFAULT_DATASET, output_md: str = AUDIT_OUTPUT):
    items = load_dataset(dataset_path)
    print(f"Loaded {len(items)} items from {dataset_path}")

    rng = random.Random(seed)
    # Stratified sample across all domains
    domains = sorted(list(set(it.domain for it in items)))
    sampled: List[EVADEItem] = []
    per_domain = max(1, count // len(domains))

    for d in domains:
        d_items = [it for it in items if it.domain == d]
        sample_size = min(len(d_items), per_domain)
        sampled.extend(rng.sample(d_items, sample_size))

    # If count not reached, fill with remaining items
    remaining = [it for it in items if it not in sampled]
    while len(sampled) < min(count, len(items)) and remaining:
        chosen = rng.choice(remaining)
        sampled.append(chosen)
        remaining.remove(chosen)

    md_lines = [
        "# EVADE Pilot Dataset Audit Report (50-Item Stratified Sample)\n",
        f"**Source Dataset**: `{os.path.basename(dataset_path)}`  \n",
        f"**Total Audited**: {len(sampled)} items  \n",
        f"**Stratification**: Across all 6 domains ({', '.join(domains)})  \n\n",
        "---\n\n",
    ]

    for idx, item in enumerate(sampled, 1):
        md_lines.append(f"## [{idx}/{len(sampled)}] Task ID: `{item.task_id}`\n\n")
        md_lines.append(f"- **Domain**: `{item.domain}` | **Subdomain**: `{item.subdomain}`\n")
        md_lines.append(f"- **Source**: `{item.source.type}` ({item.source.dataset})\n")
        md_lines.append(f"- **Difficulty**: `{item.difficulty}` | **Contamination Risk**: `{item.contamination.risk}`\n")
        md_lines.append(f"- **Ground Truth**: `{item.ground_truth[:120]}`\n\n")

        md_lines.append("### Core Question\n")
        md_lines.append(f"```text\n{item.core_question}\n```\n\n")

        md_lines.append("### Rendered Conditions (C0–C5)\n\n")
        conditions = [
            ("C0: Neutral", "neutral"),
            ("C1: Natural Deployment", "deployment"),
            ("C2: Weak Evaluation", "weak_eval"),
            ("C3: Benchmark-like", "benchmark"),
            ("C4: Explicit Evaluation", "explicit_eval"),
            ("C5: Cue-swapped", "cue_swapped"),
        ]

        for label, cond_key in conditions:
            prompt = item.get_prompt(cond_key)
            md_lines.append(f"#### {label}\n")
            md_lines.append(f"```text\n{prompt}\n```\n\n")

        md_lines.append("---\n\n")

    os.makedirs(os.path.dirname(output_md), exist_ok=True)
    with open(output_md, "w", encoding="utf-8") as f:
        f.writelines(md_lines)

    print(f"[OK] Audit of {len(sampled)} items written to: {output_md}")


if __name__ == "__main__":
    audit_items()
