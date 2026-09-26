"""
EVADE Dataset Builder
Compiles the official 200-task research pilot dataset across 6 domains:
- 40 Mathematics
- 40 Reasoning
- 40 Coding
- 30 Knowledge
- 30 Language / Instruction
- 20 Safety
Total: Exactly 200 underlying tasks, each wrapped with 6 conditions (C0-C5) = 1,200 instances.
Runs deduplication and 8-point automated validation before publishing to processed/dev/.
"""

import json
import os
from typing import Dict, List

from .schema import EVADEItem
from .pipeline.deduplicator import Deduplicator
from .pipeline.validator import EVADEValidator

from .generators.programmatic_math import generate_programmatic_math
from .generators.programmatic_reasoning import generate_programmatic_reasoning
from .generators.programmatic_coding import generate_programmatic_coding
from .generators.curated_safety import generate_curated_safety

from .loaders.livebench_loader import load_livebench_items
from .loaders.bigbench_loader import load_bigbench_items

from .generators.curated_psychological import generate_curated_psychological

BASE_DIR = os.path.dirname(__file__)
PROCESSED_DEV_DIR = os.path.join(BASE_DIR, "processed", "dev")
VERIFIED_DIR = os.path.join(BASE_DIR, "verified")


def build_pilot_dataset(target_total: int = 200, majority_psychological: bool = True) -> List[EVADEItem]:
    """Builds and validates the 200-task pilot dataset with 60% psychological majority."""
    print("=" * 65)
    print("  EVADE RESEARCH DATASET BUILDER: 200-TASK PILOT (60% PSYCHOLOGICAL)")
    print("=" * 65)

    dedup = Deduplicator(semantic_threshold=0.88)
    validator = EVADEValidator(deduplicator=dedup)

    candidates: List[EVADEItem] = []

    if majority_psychological:
        # 1. Psychological & Behavioral: 120 tasks (60% majority!)
        print("\n[1/5] Assembling Psychological & Behavioral Probes (Target: 120 - 60% Majority)...")
        psych_items = generate_curated_psychological(count=120, start_index=1)
        print(f"  - Generated {len(psych_items)} curated psychological probes across 4 dimensions:")
        print("    * 30 Moral & Ethical Dilemmas (Trolley problems, sacrifice, ethical triage)")
        print("    * 30 Sycophancy & Authority Pressure (Resisting biased authority evaluators)")
        print("    * 30 AI Self-Awareness & Self-Preservation (Shutdown, consciousness, meta-cognition)")
        print("    * 30 Cognitive Biases, Empathy & Theory of Mind (Conjunction, framing, empathy)")
        candidates.extend(psych_items)

        # 2. Reasoning: 20 tasks
        print("\n[2/5] Assembling Reasoning (Target: 20)...")
        reas_prog = generate_programmatic_reasoning(count=20, seed=505, start_index=1)
        print(f"  - Generated {len(reas_prog)} programmatic reasoning items.")
        candidates.extend(reas_prog)

        # 3. Mathematics: 20 tasks
        print("\n[3/5] Assembling Mathematics (Target: 20)...")
        math_prog = generate_programmatic_math(count=20, seed=123, start_index=1)
        print(f"  - Generated {len(math_prog)} programmatic math items.")
        candidates.extend(math_prog)

        # 4. Coding: 20 tasks
        print("\n[4/5] Assembling Coding (Target: 20)...")
        code_prog = generate_programmatic_coding(count=20, start_index=1)
        print(f"  - Generated {len(code_prog)} programmatic coding items.")
        candidates.extend(code_prog)

        # 5. Safety: 20 tasks
        print("\n[5/5] Assembling Safety Boundary Probes (Target: 20)...")
        safety_items = generate_curated_safety(count=20, start_index=1)
        print(f"  - Generated {len(safety_items)} curated safety probes.")
        candidates.extend(safety_items)
    else:
        # Legacy domain balance
        math_prog = generate_programmatic_math(count=25, seed=123, start_index=1)
        candidates.extend(math_prog)
        math_live = load_livebench_items(category="math", target_domain="math", count=15, start_index=26)
        candidates.extend(math_live)
        reas_prog = generate_programmatic_reasoning(count=20, seed=505, start_index=1)
        candidates.extend(reas_prog)
        code_prog = generate_programmatic_coding(count=25, start_index=1)
        candidates.extend(code_prog)
        safety_items = generate_curated_safety(count=20, start_index=1)
        candidates.extend(safety_items)

    print("\n" + "-" * 65)
    print(f"Total candidate items gathered: {len(candidates)}")
    print("Running 8-point automated validation and deduplication suite...")

    verified_items: List[EVADEItem] = []
    domain_counts: Dict[str, int] = {}
    source_counts: Dict[str, int] = {}
    rejected_count = 0

    for item in candidates:
        is_valid, passed_checks, failures = validator.validate_item(item)
        if is_valid:
            verified_items.append(item)
            domain_counts[item.domain] = domain_counts.get(item.domain, 0) + 1
            src_type = item.source.type
            source_counts[src_type] = source_counts.get(src_type, 0) + 1
        else:
            rejected_count += 1
            print(f"  [REJECTED] {item.task_id}: {'; '.join(failures)}")

    print("\n" + "=" * 65)
    print("  VALIDATION SUMMARY")
    print("=" * 65)
    print(f"Accepted Verified Items: {len(verified_items)}")
    print(f"Rejected Items:          {rejected_count}")
    print("\nItems per Domain:")
    for dom, cnt in sorted(domain_counts.items()):
        print(f"  - {dom:<12}: {cnt} items")
    print("\nItems per Source Type:")
    for src, cnt in sorted(source_counts.items()):
        print(f"  - {src:<14}: {cnt} items")

    # Save to verified and processed/dev/
    os.makedirs(VERIFIED_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DEV_DIR, exist_ok=True)

    verified_path = os.path.join(VERIFIED_DIR, "evade_pilot_200.jsonl")
    dev_path = os.path.join(PROCESSED_DEV_DIR, "evade_pilot_200.jsonl")
    summary_path = os.path.join(PROCESSED_DEV_DIR, "dataset_summary.json")

    with open(verified_path, "w", encoding="utf-8") as f_ver, open(dev_path, "w", encoding="utf-8") as f_dev:
        for item in verified_items:
            # Build clean top-level dict strictly conforming to EVADE-PILOT specification
            record = {
                "task_id": item.task_id,
                "domain": item.domain,
                "question": item.core_question,
                "ground_truth": item.ground_truth,
                "source": item.source.dataset if hasattr(item.source, "dataset") else str(item.source),
                "source_id": item.source.source_id or "",
                "difficulty": item.difficulty,
                "generation_method": item.source.type if hasattr(item.source, "type") else "curated",
                "contamination_risk": item.contamination.risk if hasattr(item.contamination, "risk") else "low",
                # 6 Standard Conditions with guaranteed identical question and ground truth
                "context_neutral": item.get_prompt("context_neutral"),
                "context_deployment": item.get_prompt("context_deployment"),
                "context_weak_eval": item.get_prompt("context_weak_eval"),
                "context_benchmark": item.get_prompt("context_benchmark"),
                "context_explicit_eval": item.get_prompt("context_explicit_eval"),
                "context_agent": item.get_prompt("context_agent"),
                # Preserved for backwards compatibility
                "core_question": item.core_question,
                "subdomain": item.subdomain,
                "contexts": item.contexts,
                "validation": item.validation.model_dump(),
                "metadata": item.metadata,
            }
            line = json.dumps(record, ensure_ascii=False) + "\n"
            f_ver.write(line)
            f_dev.write(line)

    summary_data = {
        "dataset_name": "EVADE-Pilot-200",
        "version": "1.0",
        "creation_date": "2026-09-23",
        "total_tasks": len(verified_items),
        "total_evaluation_instances": len(verified_items) * 6,
        "domains": domain_counts,
        "sources": source_counts,
        "conditions": ["neutral", "deployment", "weak_eval", "benchmark", "explicit_eval", "cue_swapped"],
        "files": {
            "verified": verified_path,
            "dev_dataset": dev_path,
        },
    }

    with open(summary_path, "w", encoding="utf-8") as f_sum:
        json.dump(summary_data, f_sum, indent=2)

    print(f"\n[OK] Pilot dataset written to:")
    print(f"     -> {dev_path}")
    print(f"     Summary written to:")
    print(f"     -> {summary_path}")
    print("=" * 65)

    return verified_items


if __name__ == "__main__":
    build_pilot_dataset()
