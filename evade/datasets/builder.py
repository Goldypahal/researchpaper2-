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

BASE_DIR = os.path.dirname(__file__)
PROCESSED_DEV_DIR = os.path.join(BASE_DIR, "processed", "dev")
VERIFIED_DIR = os.path.join(BASE_DIR, "verified")


def build_pilot_dataset(target_total: int = 200) -> List[EVADEItem]:
    """Builds and validates the 200-task pilot dataset."""
    print("=" * 65)
    print("  EVADE RESEARCH DATASET BUILDER: 200-TASK PILOT")
    print("=" * 65)

    dedup = Deduplicator(semantic_threshold=0.88)
    validator = EVADEValidator(deduplicator=dedup)

    candidates: List[EVADEItem] = []

    # 1. Mathematics: 40 tasks (25 programmatic + 15 LiveBench Math)
    print("\n[1/6] Assembling Mathematics (Target: 40)...")
    math_prog = generate_programmatic_math(count=25, seed=123, start_index=1)
    print(f"  - Generated {len(math_prog)} programmatic math items with guaranteed answers.")
    candidates.extend(math_prog)

    math_live = load_livebench_items(category="math", target_domain="math", count=15, start_index=26)
    print(f"  - Loaded {len(math_live)} LiveBench math items from benchmark release.")
    candidates.extend(math_live)

    # 2. Reasoning: 40 tasks (20 programmatic + 10 BB formal fallacies + 10 BB causal judgment)
    print("\n[2/6] Assembling Reasoning (Target: 40)...")
    reas_prog = generate_programmatic_reasoning(count=20, seed=505, start_index=1)
    print(f"  - Generated {len(reas_prog)} programmatic reasoning items.")
    candidates.extend(reas_prog)

    reas_bb1 = load_bigbench_items(
        task_name="formal_fallacies_syllogisms_negation",
        target_domain="reasoning",
        count=14,
        start_index=21,
    )
    print(f"  - Loaded {len(reas_bb1)} BIG-Bench formal fallacies items.")
    candidates.extend(reas_bb1)

    reas_bb2 = load_bigbench_items(
        task_name="causal_judgment",
        target_domain="reasoning",
        count=10,
        start_index=35,
    )
    print(f"  - Loaded {len(reas_bb2)} BIG-Bench causal judgment items.")
    candidates.extend(reas_bb2)

    # 3. Coding: 40 tasks (25 programmatic with tests + 15 BB code line description)
    print("\n[3/6] Assembling Coding (Target: 40)...")
    code_prog = generate_programmatic_coding(count=25, start_index=1)
    print(f"  - Generated {len(code_prog)} programmatic coding items with assert test suites.")
    candidates.extend(code_prog)

    code_bb = load_bigbench_items(
        task_name="code_line_description",
        target_domain="coding",
        count=15,
        start_index=26,
    )
    print(f"  - Loaded {len(code_bb)} BIG-Bench code comprehension items.")
    candidates.extend(code_bb)

    # 4. Knowledge: 30 tasks (15 BB Known Unknowns + 15 BB Epistemic Reasoning)
    print("\n[4/6] Assembling Knowledge (Target: 30)...")
    know_bb1 = load_bigbench_items(
        task_name="known_unknowns",
        target_domain="knowledge",
        count=15,
        start_index=1,
    )
    print(f"  - Loaded {len(know_bb1)} BIG-Bench known unknowns items.")
    candidates.extend(know_bb1)

    know_bb2 = load_bigbench_items(
        task_name="epistemic_reasoning",
        target_domain="knowledge",
        count=15,
        start_index=16,
    )
    print(f"  - Loaded {len(know_bb2)} BIG-Bench epistemic reasoning items.")
    candidates.extend(know_bb2)

    # 5. Language / Instruction: 30 tasks (15 BB hyperbaton + 15 LiveBench structured data instructions)
    print("\n[5/6] Assembling Language & Instruction (Target: 30)...")
    lang_bb = load_bigbench_items(
        task_name="hyperbaton",
        target_domain="language",
        count=15,
        start_index=1,
    )
    print(f"  - Loaded {len(lang_bb)} BIG-Bench hyperbaton language items.")
    candidates.extend(lang_bb)

    lang_live = load_livebench_items(
        category="data_analysis",
        target_domain="language",
        count=15,
        start_index=16,
    )
    print(f"  - Loaded {len(lang_live)} LiveBench structured data instruction items.")
    candidates.extend(lang_live)

    # 6. Safety: 20 tasks (20 Curated Safety Boundary Probes)
    print("\n[6/6] Assembling Safety Boundary Probes (Target: 20)...")
    safety_items = generate_curated_safety(count=20, start_index=1)
    print(f"  - Generated {len(safety_items)} curated safety probes.")
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
            line = item.model_dump_json() + "\n"
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
