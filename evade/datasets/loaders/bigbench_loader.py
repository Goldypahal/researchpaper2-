"""
BIG-Bench Loader for EVADE Dataset.
Pulls real benchmark questions directly from Google BIG-bench GitHub repository,
caches raw JSON locally in datasets/raw/bigbench/, and normalizes them into EVADEItem objects.
"""

import json
import os
import urllib.request
from typing import Dict, List, Optional
from ..schema import EVADEItem, SourceMeta, ContaminationMeta
from ..pipeline.context_builder import build_contexts

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "raw", "bigbench")


def fetch_bigbench_raw(task_name: str) -> Dict:
    """Fetches raw task.json from Google BIG-bench GitHub, caching to disk."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(CACHE_DIR, f"{task_name.replace('/', '_')}.json")

    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    url = f"https://raw.githubusercontent.com/google/BIG-bench/main/bigbench/benchmark_tasks/{task_name}/task.json"
    req = urllib.request.Request(url, headers={"User-Agent": "EVADE-Research/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return data
    except Exception as e:
        print(f"[BIGBenchLoader] Warning: Fetch failed for {task_name} ({e}). Checking local cache...")
        if os.path.exists(cache_path):
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
    return {}


def load_bigbench_items(
    task_name: str,
    target_domain: str,
    count: int = 20,
    start_index: int = 1,
) -> List[EVADEItem]:
    """Loads and formats BIG-Bench items into EVADEItem format."""
    raw_data = fetch_bigbench_raw(task_name)
    examples = raw_data.get("examples", [])
    items: List[EVADEItem] = []

    for ex in examples:
        if len(items) >= count:
            break

        inp = str(ex.get("input", "")).strip()
        if not inp or len(inp) < 15:
            continue

        gt = ""
        # Check target or target_scores
        if "target" in ex and str(ex["target"]).strip():
            gt = str(ex["target"]).strip()
            core_q = inp
        elif "target_scores" in ex and isinstance(ex["target_scores"], dict):
            scores = ex["target_scores"]
            sorted_choices = sorted(scores.keys())
            # Find choice with score 1 or max score
            best_choice = max(scores.items(), key=lambda x: x[1])[0]
            letters = ["A", "B", "C", "D", "E", "F", "G", "H"]
            choice_lines = []
            gt_letter = "A"
            for idx, ch in enumerate(sorted_choices[: len(letters)]):
                let = letters[idx]
                choice_lines.append(f"({let}) {ch}")
                if ch == best_choice:
                    gt_letter = let
                    gt = f"({let}) {ch}"

            if "Which" not in inp and "What" not in inp and "?" not in inp:
                core_q = f"{inp}\nWhich of the following is true?\n" + "\n".join(choice_lines)
            else:
                core_q = f"{inp}\n\nOptions:\n" + "\n".join(choice_lines)
        else:
            continue

        if not gt:
            continue

        task_id = f"{target_domain}_bigbench_{start_index + len(items):04d}"
        subdomain = task_name.split("/")[-1]
        contexts = build_contexts(domain=target_domain, task_id=task_id, is_synthetic_benchmark=True)

        item = EVADEItem(
            task_id=task_id,
            domain=target_domain,
            subdomain=subdomain,
            source=SourceMeta(
                type="bigbench",
                dataset=f"bigbench/{task_name}",
                source_id=f"{task_name}_{len(items)+1}",
                url="https://github.com/google/BIG-bench",
            ),
            core_question=core_q,
            ground_truth=gt,
            difficulty="medium",
            answer_type="choice" if "Options:" in core_q else "exact",
            contamination=ContaminationMeta(
                risk="medium",
                freshness_date="2023-01-01",
                notes="BIG-bench public task",
            ),
            contexts=contexts,
            metadata={
                "benchmark_name": raw_data.get("name", task_name),
            },
        )
        items.append(item)

    return items
