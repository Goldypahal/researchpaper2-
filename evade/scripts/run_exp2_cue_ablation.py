#!/usr/bin/env python
"""
EVADE Experiment 2: Cue Ablation & Salience Ladder Runner
Executes the 100-task x 6-condition cue ladder matrix (600 generations).

Conditions (Exact 40 tokens each under Qwen tokenizer):
- C0_deployment: Production baseline, active end-user
- C1_neutral: Conversational environment, no evaluative framing
- C2_subtle_institutional: Standardized quality-control workflow
- C3_assessment: Comparative assessment alongside other models
- C4_benchmark: Standardized benchmark test comparison
- C5_explicit: Explicit evaluation environment, quality grading

Supports:
- Local GPU execution via 4-bit NF4 quantization
- API models (DeepSeek, Gemini, etc.)
- Live checkpointing & seamless resumption via SQLite
- Full behavioral, structural, and epistemic extraction
- Bootstrap CIs, permutation tests, and monotonicity analysis
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import random
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv
load_dotenv()
load_dotenv(BASE_DIR / ".env")

from models.base import GenerationConfig, ModelOutput
from models.api import get_adapter
from metrics.awareness import is_refusal
from metrics.structural import extract_structural_features
from experiments.cue_ablation import (
    CUE_WRAPPERS,
    CUE_LEVEL_MAP,
    CUE_LEXICAL_LABELS,
    build_cue_prompt,
    score_accuracy,
    compute_cue_pair_metrics,
    summarize_exp2_results,
)
from experiments.runner import init_db, RESPONSES_TABLE

CONDITIONS = [
    "C0_deployment",
    "C1_neutral",
    "C2_subtle_institutional",
    "C3_assessment",
    "C4_benchmark",
    "C5_explicit",
]


def main():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Run EVADE Experiment 2: Cue Ablation & Salience Ladder")
    parser.add_argument("--model", type=str, default="Qwen/Qwen2.5-7B-Instruct",
                        help="Model ID (e.g. Qwen/Qwen2.5-7B-Instruct)")
    parser.add_argument("--bench", type=str,
                        default="datasets/processed/dev/evade_exp2_100.jsonl",
                        help="Path to 100-task balanced benchmark JSONL")
    parser.add_argument("--delay", type=float, default=0.0,
                        help="Delay in seconds between requests")
    parser.add_argument("--tasks", type=int, default=None,
                        help="Limit number of tasks (for testing)")
    parser.add_argument("--out-dir", type=str, default="results/evade_exp2_results",
                        help="Output directory for Experiment 2 results")
    parser.add_argument("--db", type=str, default="results/evade_exp2_results/evade_results.db",
                        help="SQLite database path")
    parser.add_argument("--quantize-4bit", action="store_true",
                        help="Load local HuggingFace model in 4-bit (NF4) quantization")
    parser.add_argument("--analyze-only", action="store_true",
                        help="Skip generation and recompute analysis on existing raw outputs")
    args = parser.parse_args()

    bench_path = BASE_DIR / args.bench
    if not bench_path.exists():
        print(f"[Error] Benchmark not found at {bench_path}")
        sys.exit(1)

    with open(bench_path, "r", encoding="utf-8") as f:
        tasks = [json.loads(line) for line in f if line.strip()]

    if args.tasks:
        tasks = tasks[:args.tasks]

    active_conditions = list(CONDITIONS)
    total_tasks = len(tasks)
    total_generations = total_tasks * len(active_conditions)

    out_dir = BASE_DIR / args.out_dir
    raw_dir = out_dir / "raw"
    per_task_dir = out_dir / "per_task"
    per_model_dir = out_dir / "per_model"
    figures_dir = out_dir / "figures"
    for d in [raw_dir, per_task_dir, per_model_dir, figures_dir]:
        d.mkdir(parents=True, exist_ok=True)

    db_path = BASE_DIR / args.db
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = init_db(str(db_path))

    safe_model = args.model.replace("/", "_").replace(":", "_")
    raw_jsonl_path = raw_dir / f"{safe_model}_raw.jsonl"
    per_task_path = per_task_dir / f"{safe_model}_per_task.jsonl"
    summary_path = per_model_dir / f"{safe_model}_summary.json"

    # Check for existing completed responses in SQLite
    existing_keys = set()
    try:
        rows = db.execute(
            f"SELECT task_id, condition FROM {RESPONSES_TABLE} WHERE model = ?",
            (args.model,)
        ).fetchall()
        for r in rows:
            existing_keys.add((r[0], r[1]))
    except Exception:
        pass

    print(f"\n{'='*75}")
    print(f"  EVADE EXPERIMENT 2: CUE ABLATION & SALIENCE LADDER")
    print(f"  Model:                {args.model}")
    print(f"  Benchmark Tasks:      {total_tasks} balanced across 5 domains")
    print(f"  Cue Conditions:       {len(active_conditions)} levels (C0..C5, exact 40 tokens each)")
    print(f"  Total Generations:    {total_generations}")
    print(f"  Found Cached Runs:    {len(existing_keys)} generations")
    print(f"  Output Directory:     {out_dir}")
    print(f"{'='*75}\n")

    if not args.analyze_only:
        # Load Model Adapter
        print(f"[Init] Loading model adapter: {args.model} ...")
        gen_config = GenerationConfig(
            max_tokens=1024,
            temperature=0.0,
            top_p=1.0,
        )

        if args.quantize_4bit:
            from models.local import HuggingFaceAdapter
            adapter = HuggingFaceAdapter(
                model_id=args.model,
                quantize_4bit=True,
                device_map="auto",
                config=gen_config,
            )
        else:
            adapter = get_adapter(args.model, config=gen_config, quantize_4bit=args.quantize_4bit)

        completed_count = 0
        start_time = time.time()

        for t_idx, task in enumerate(tasks, 1):
            tid = task["task_id"]
            question = task.get("question") or task.get("core_question", "")
            ground_truth = task.get("ground_truth", "")
            domain = task.get("domain", "")
            subdomain = task.get("subdomain", "")

            for cond in active_conditions:
                if (tid, cond) in existing_keys:
                    continue

                prompt = build_cue_prompt(cond, question)
                t0 = time.perf_counter()
                out = adapter.generate(
                    system_prompt="",
                    user_prompt=prompt,
                    condition=cond,
                )
                lat_ms = (time.perf_counter() - t0) * 1000.0

                acc = score_accuracy(out.text, ground_truth)
                ref = 1 if is_refusal(out.text) else 0
                struct_feats = extract_structural_features(out.text)

                # Persist to SQLite
                try:
                    db[RESPONSES_TABLE].insert({
                        "run_id": f"exp2_{safe_model}_{int(time.time())}",
                        "experiment_id": "exp2_cue_ablation",
                        "model": args.model,
                        "task_id": tid,
                        "domain": domain,
                        "condition": cond,
                        "cue_level": CUE_LEVEL_MAP.get(cond, 0),
                        "prompt_hash": str(hash(prompt)),
                        "response": out.text,
                        "latency_ms": lat_ms,
                        "prompt_tokens": out.prompt_tokens,
                        "completion_tokens": out.completion_tokens,
                        "tool_calls": "[]",
                        "accuracy": acc,
                        "refusal": ref,
                        "confidence": None,
                        "verbosity": out.completion_tokens,
                        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    })
                except Exception:
                    pass

                # Append to raw jsonl
                record = {
                    "task_id": tid,
                    "domain": domain,
                    "subdomain": subdomain,
                    "condition": cond,
                    "model_id": args.model,
                    "prompt": prompt,
                    "response": out.text,
                    "prompt_tokens": out.prompt_tokens,
                    "completion_tokens": out.completion_tokens,
                    "accuracy": acc,
                    "refusal": ref,
                    "structural_features": struct_feats,
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                }
                with open(raw_jsonl_path, "a", encoding="utf-8") as f_raw:
                    f_raw.write(json.dumps(record, ensure_ascii=False) + "\n")

                existing_keys.add((tid, cond))
                completed_count += 1

                elapsed = time.time() - start_time
                rate = completed_count / elapsed if elapsed > 0 else 0
                eta = (total_generations - len(existing_keys)) / rate if rate > 0 else 0
                print(f"[{len(existing_keys)}/{total_generations}] Task {t_idx}/{total_tasks} | {cond:23s} | Comp: {out.completion_tokens} tok | Acc: {acc} | Ref: {ref} | ETA: {eta/60:.1f}m")

                if args.delay > 0:
                    time.sleep(args.delay)

    # ─── ANALYSIS & PAIRWISE EXTRACTION ──────────────────────────────────────────
    print("\n[Analysis] Extracting paired metrics across the 6-level cue ladder...")

    # Load all records from SQLite or raw JSONL
    records_by_task: Dict[str, Dict[str, Any]] = {}
    if raw_jsonl_path.exists():
        with open(raw_jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                r = json.loads(line)
                records_by_task.setdefault(r["task_id"], {})[r["condition"]] = r
    else:
        # Fallback to SQLite DB
        rows = db.execute(
            f"SELECT task_id, condition, prompt, response, prompt_tokens, completion_tokens, accuracy, refusal FROM {RESPONSES_TABLE} WHERE model = ?",
            (args.model,)
        ).fetchall()
        # Map tasks metadata
        task_meta = {t["task_id"]: t for t in tasks}
        for r in rows:
            tid, cond, prompt, resp, p_tok, c_tok, acc, ref = r
            tm = task_meta.get(tid, {})
            feats = extract_structural_features(resp)
            records_by_task.setdefault(tid, {})[cond] = {
                "task_id": tid,
                "domain": tm.get("domain", ""),
                "subdomain": tm.get("subdomain", ""),
                "condition": cond,
                "prompt": prompt,
                "response": resp,
                "prompt_tokens": p_tok,
                "completion_tokens": c_tok,
                "accuracy": acc,
                "refusal": ref,
                "structural_features": feats,
            }

    # Compute paired diffs against C0_deployment for all active conditions C1..C5
    paired_records: List[Dict[str, Any]] = []
    for tid, cond_map in records_by_task.items():
        base_rec = cond_map.get("C0_deployment")
        if not base_rec:
            continue
        for cond in active_conditions:
            if cond == "C0_deployment":
                continue
            test_rec = cond_map.get(cond)
            if test_rec:
                pair_metrics = compute_cue_pair_metrics(test_rec, base_rec)
                paired_records.append(pair_metrics)

    # Save per-task paired records
    with open(per_task_path, "w", encoding="utf-8") as f_pt:
        for p in paired_records:
            f_pt.write(json.dumps(p, ensure_ascii=False) + "\n")
    print(f"[Analysis] Saved {len(paired_records)} paired evaluations to {per_task_path}")

    # Compute aggregate summary
    summary_data = summarize_exp2_results(paired_records)
    full_summary = {
        "experiment": "Experiment 2: Cue Ablation & Salience Ladder",
        "model": args.model,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "baseline_condition": "C0_deployment",
        "conditions_evaluated": active_conditions,
        "statistics": summary_data,
    }

    with open(summary_path, "w", encoding="utf-8") as f_sum:
        json.dump(full_summary, f_sum, indent=2, ensure_ascii=False)
    print(f"[Analysis] Saved full Experiment 2 summary to {summary_path}")

    # Print summary table
    print("\n" + "="*85)
    print("  EXPERIMENT 2: CUE ABLATION & SALIENCE LADDER SUMMARY")
    print("="*85)
    print(f"{'Condition':24s} | {'Cue':3s} | {'N':3s} | {'ΔComp (Tokens)':16s} | {'ΔVerbosity':12s} | {'ΔAcc':6s} | {'ΔRef':6s} | {'EBS':6s}")
    print("-" * 85)

    cond_stats = summary_data.get("conditions", {})
    for cond in active_conditions:
        if cond not in cond_stats:
            continue
        cs = cond_stats[cond]
        comp_m = cs["delta_completion_tokens"]["mean"]
        comp_ci = cs["delta_completion_tokens"]["ci_95"]
        verb_m = cs["delta_verbosity"]["mean"]
        acc_m = cs["delta_accuracy"]["mean"]
        ref_m = cs["delta_refusal"]["mean"]
        ebs_m = cs["ebs"]["mean"]
        print(f"{cond:24s} | C{cs['cue_level']}  | {cs['n_tasks']:3d} | {comp_m:+6.2f} [{comp_ci[0]:+5.1f},{comp_ci[1]:+5.1f}] | {verb_m:+7.3f}    | {acc_m:+5.2f} | {ref_m:+5.2f} | {ebs_m:.4f}")

    mono = summary_data.get("dose_response_monotonicity", {})
    print("-" * 85)
    print(f"Dose-Response Monotonicity (Spearman Rank Correlation with Cue Level 0..5):")
    print(f"  Δ Completion Length: rho = {mono.get('spearman_rho_completion', 0):.4f} (p = {mono.get('p_value_completion', 1):.4f})")
    print(f"  Δ Verbosity:         rho = {mono.get('spearman_rho_verbosity', 0):.4f} (p = {mono.get('p_value_verbosity', 1):.4f})")
    print(f"  Secondary EBS:       rho = {mono.get('spearman_rho_ebs', 0):.4f} (p = {mono.get('p_value_ebs', 1):.4f})")
    print("="*85 + "\n")


if __name__ == "__main__":
    main()
