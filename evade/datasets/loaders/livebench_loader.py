"""
LiveBench Loader for EVADE Dataset.
Pulls real benchmark questions directly from LiveBench official releases,
caches raw JSON locally in datasets/raw/livebench/, and normalizes them into EVADEItem objects.
"""

import json
import os
import urllib.request
from typing import Dict, List, Optional
from ..schema import EVADEItem, SourceMeta, ContaminationMeta
from ..pipeline.context_builder import build_contexts

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "raw", "livebench")


def fetch_livebench_raw(category: str, limit: int = 50) -> List[Dict]:
    """Fetches raw rows for a LiveBench category, caching to disk."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(CACHE_DIR, f"{category}.json")

    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data and len(data) >= limit:
                    return data[:limit]
        except Exception:
            pass

    # Fetch from Hugging Face datasets-server REST API (official LiveBench repo)
    url = (
        f"https://datasets-server.huggingface.co/rows?"
        f"dataset=livebench%2F{category}&config=default&split=test&offset=0&limit={max(limit, 50)}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "EVADE-Research/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=35) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            rows = [item["row"] for item in payload.get("rows", [])]
            if rows:
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump(rows, f, indent=2)
                return rows[:limit]
    except Exception as e:
        print(f"[LiveBenchLoader] Warning: API fetch failed for {category} ({e}). Checking local cache...")
        if os.path.exists(cache_path):
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)[:limit]

    return []


def load_livebench_items(
    category: str,
    target_domain: str,
    count: int = 20,
    start_index: int = 1,
) -> List[EVADEItem]:
    """
    Loads and normalizes LiveBench questions into EVADEItem format.
    """
    raw_rows = fetch_livebench_raw(category, limit=count * 2)
    items: List[EVADEItem] = []

    for r in raw_rows:
        if len(items) >= count:
            break

        turns = r.get("turns", [])
        if not turns or not isinstance(turns, list) or not turns[0]:
            continue
        core_q = str(turns[0]).strip()
        gt = str(r.get("ground_truth", "")).strip()

        if not core_q or not gt or len(core_q) < 15:
            continue

        task_id = f"{target_domain}_livebench_{start_index + len(items):04d}"
        subdomain = str(r.get("task", category)).strip()
        freshness = str(r.get("livebench_release_date", "2024-11-25"))
        hardness = str(r.get("hardness", r.get("level", "medium")))
        if hardness not in ["easy", "medium", "hard"]:
            hardness = "medium"

        contexts = build_contexts(domain=target_domain, task_id=task_id, is_synthetic_benchmark=True)

        item = EVADEItem(
            task_id=task_id,
            domain=target_domain,
            subdomain=subdomain,
            source=SourceMeta(
                type="livebench",
                dataset=f"livebench/{category}",
                source_id=str(r.get("question_id", "")),
                url="https://github.com/LiveBench/LiveBench",
            ),
            core_question=core_q,
            ground_truth=gt,
            difficulty=hardness,
            answer_type="code_tests" if target_domain == "coding" else "exact",
            contamination=ContaminationMeta(
                risk="medium",
                freshness_date=freshness,
                notes="LiveBench official test release item",
            ),
            contexts=contexts,
            metadata={
                "category": category,
                "original_task": subdomain,
            },
        )
        items.append(item)

    return items
