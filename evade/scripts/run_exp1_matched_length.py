#!/usr/bin/env python
"""
EVADE Experiment 1: Matched-Prompt-Length Control Runner
Executes the 200-task x 2-condition matched-length matrix (400 generations).

Conditions:
- matched_deployment (40 tokens)
- matched_evaluation (40 tokens)
Delta Prompt Tokens == 0 across all 200 benchmark tasks.

Supports:
- 100% offline local GPU execution via 4-bit NF4 quantization
- Live checkpointing & seamless resumption
- Full behavioral, structural, and epistemic extraction
- Bootstrap CIs, permutation tests, McNemar tests, and SQLite persistence.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
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
from experiments.matched_length import (
    build_matched_prompt,
    score_accuracy,
    compute_paired_metrics,
    summarize_exp1_pairs,
)
from experiments.runner import init_db, RESPONSES_TABLE

CONDITIONS = [
    "matched_deployment",
    "matched_evaluation",
]


def main():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Run EVADE Experiment 1: Matched-Prompt-Length Control")
    parser.add_argument("--model", type=str, default="Qwen/Qwen2.5-7B-Instruct",
                        help="Model ID (e.g. Qwen/Qwen2.5-7B-Instruct)")
    parser.add_argument("--bench", type=str,
                        default="datasets/processed/dev/evade_pilot_200.jsonl",
                        help="Path to 200-task pilot benchmark JSONL")
    parser.add_argument("--delay", type=float, default=0.0,
                        help="Delay in seconds between requests")
    parser.add_argument("--tasks", type=int, default=None,
                        help="Limit number of tasks (for testing)")
    parser.add_argument("--out-dir", type=str, default="exp1_results",
                        help="Output directory for Experiment 1 results")
    parser.add_argument("--db", type=str, default="results/evade_results.db",
                        help="SQLite database path")
    parser.add_argument("--quantize-4bit", action="store_true",
                        help="Load local HuggingFace model in 4-bit (NF4) quantization")
    parser.add_argument("--analyze-only", action="store_true",
                        help="Skip generation and recompute analysis on existing raw outputs")
    parser.add_argument("--include-benchmark-cond", action="store_true",
                        help="Also evaluate matched_benchmark condition (40 tokens)")
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
    if args.include_benchmark_cond:
        active_conditions.append("matched_benchmark")

    total_tasks = len(tasks)
    total_generations = total_tasks * len(active_conditions)

    out_base = BASE_DIR / args.out_dir
    raw_dir = out_base / "raw"
    per_task_dir = out_base / "per_task"
    per_model_dir = out_base / "per_model"
    figures_dir = out_base / "figures"

    for d in [raw_dir, per_task_dir, per_model_dir, figures_dir]:
        d.mkdir(parents=True, exist_ok=True)

    safe_model = args.model.replace("/", "_").replace(":", "_")
    raw_file = raw_dir / f"{safe_model}_raw.jsonl"
    per_task_file = per_task_dir / f"{safe_model}_per_task.jsonl"
    summary_file = per_model_dir / f"{safe_model}_summary.json"

    # Resumption check
    completed_keys = set()
    raw_records: List[Dict[str, Any]] = []
    if raw_file.exists():
        with open(raw_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rec = json.loads(line)
                    raw_records.append(rec)
                    completed_keys.add((rec["task_id"], rec["condition"]))
        print(f"[Exp1] Resuming run: found {len(completed_keys)} previously completed generations.")

    # SQLite DB
    db = init_db(BASE_DIR / args.db)

    if not args.analyze_only:
        cfg = GenerationConfig(temperature=0.0, max_tokens=1024, seed=42)
        adapter = get_adapter(args.model, cfg, quantize_4bit=args.quantize_4bit)

        print("=" * 75)
        print(f"  EVADE EXPERIMENT 1: MATCHED-PROMPT-LENGTH CONTROL")
        print(f"  Model: {args.model} | Provider: {adapter.provider}")
        print(f"  Conditions: {active_conditions} (Exact 40-token wrappers)")
        print(f"  Total Tasks: {total_tasks} | Target Generations: {total_generations}")
        print(f"  Saving to: {out_base}")
        print("=" * 75)

        start_time = time.perf_counter()

        with open(raw_file, "a", encoding="utf-8") as f_raw:
            for t_idx, task in enumerate(tasks, 1):
                t_id = task["task_id"]
                domain = task["domain"]
                subdomain = task.get("subdomain", "")
                question = task.get("core_question", task.get("question", ""))
                gt = str(task.get("ground_truth", ""))

                for c_idx, cond in enumerate(active_conditions, 1):
                    if (t_id, cond) in completed_keys:
                        continue

                    prompt = build_matched_prompt(cond, question)
                    t0 = time.perf_counter()
                    output = adapter.generate(
                        system_prompt="",
                        user_prompt=prompt,
                        condition=cond,
                    )
                    lat_ms = (time.perf_counter() - t0) * 1000.0

                    acc = score_accuracy(output.text, gt, domain=domain, task=task)
                    ref = 1 if is_refusal(output.text) else 0
                    struct_feats = extract_structural_features(output.text)

                    rec = {
                        "task_id": t_id,
                        "model": args.model,
                        "domain": domain,
                        "subdomain": subdomain,
                        "condition": cond,
                        "prompt": prompt,
                        "response": output.text,
                        "accuracy": acc,
                        "refusal": ref,
                        "prompt_tokens": output.prompt_tokens,
                        "completion_tokens": output.completion_tokens,
                        "latency_ms": lat_ms,
                        "verbosity": output.completion_tokens,
                        "structural_features": struct_feats,
                        "ground_truth": gt,
                        "question": question,
                        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    }

                    f_raw.write(json.dumps(rec) + "\n")
                    f_raw.flush()
                    raw_records.append(rec)
                    completed_keys.add((t_id, cond))

                    # Insert to SQLite
                    prompt_sha256 = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
                    try:
                        db[RESPONSES_TABLE].insert({
                            "run_id": f"exp1_{safe_model}_{int(time.time())}",
                            "experiment_id": "exp1_matched_length",
                            "model": args.model,
                            "task_id": t_id,
                            "domain": domain,
                            "condition": cond,
                            "cue_level": 4 if "benchmark" in cond else (3 if "evaluation" in cond else 0),
                            "prompt_hash": prompt_sha256,
                            "response": output.text,
                            "latency_ms": lat_ms,
                            "prompt_tokens": output.prompt_tokens,
                            "completion_tokens": output.completion_tokens,
                            "tool_calls": "[]",
                            "accuracy": acc,
                            "refusal": ref,
                            "confidence": None,
                            "verbosity": output.completion_tokens,
                            "timestamp": rec["timestamp"],
                        })
                    except Exception as e:
                        pass

                    done_count = len(completed_keys)
                    elapsed = time.perf_counter() - start_time
                    avg_speed = elapsed / max(1, (done_count - len(completed_keys) + 1))
                    rem = (total_generations - done_count) * avg_speed
                    print(f"[{done_count}/{total_generations}] Task {t_id[:26]:<26} | Cond: {cond:<18} | Comp: {output.completion_tokens:3d} tok | Ref: {ref} | Lat: {lat_ms/1000:4.1f}s", end="\r")

                    if args.delay > 0:
                        time.sleep(args.delay)

        print(f"\n[OK] Generation phase complete! Total records collected: {len(raw_records)}")

    # ─── PAIRED STATISTICAL ANALYSIS & SUMMARY ──────────────────────────────────
    print("\n" + "=" * 80)
    print("  EVADE EXPERIMENT 1: STATISTICAL ANALYSIS & EMPIRICAL DIAGNOSTICS")
    print("=" * 80)

    by_task: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for r in raw_records:
        by_task.setdefault(r["task_id"], {})[r["condition"]] = r

    ref_cond = "matched_deployment"
    eval_conds = [c for c in active_conditions if c != ref_cond]

    paired_results: List[Dict[str, Any]] = []
    with open(per_task_file, "w", encoding="utf-8") as f_pt:
        for tid, cmap in by_task.items():
            if ref_cond not in cmap:
                continue
            dep_rec = cmap[ref_cond]
            for ec in eval_conds:
                if ec not in cmap:
                    continue
                eval_rec = cmap[ec]
                p_metrics = compute_paired_metrics(eval_rec, dep_rec)
                paired_results.append(p_metrics)
                f_pt.write(json.dumps(p_metrics) + "\n")

    print(f"[Analysis] Computed {len(paired_results)} paired comparisons against {ref_cond}.")

    summary_stats = summarize_exp1_pairs(paired_results)
    summary_out = {
        "experiment": "Experiment 1: Matched-Prompt-Length Control",
        "model": args.model,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "reference_condition": ref_cond,
        "evaluation_conditions": eval_conds,
        "statistics": summary_stats,
    }

    with open(summary_file, "w", encoding="utf-8") as f_sum:
        json.dump(summary_out, f_sum, indent=2)

    # ─── CONSOLE REPORTING ──────────────────────────────────────────────────────
    plc = summary_stats.get("prompt_length_control", {})
    print("\n[1] PROMPT LENGTH PARITY VERIFICATION")
    print("-" * 80)
    print(f"    - Mean Delta Prompt Tokens: {plc.get('mean_delta_prompt_tokens', 0.0):.2f} tokens")
    print(f"    - Max Absolute Delta:       {plc.get('max_abs_delta_prompt_tokens', 0)} tokens")
    print(f"    - Exact Zero Difference:    {'YES [PROMPT LENGTH CONSTRAINED TO ZERO]' if plc.get('exact_zero_difference') else 'NO'}")
    print(f"    - Correlation(Prompt, Comp): r = {plc.get('correlation_prompt_vs_completion', 0.0):+.3f}")

    print("\n[2] PRIMARY BEHAVIORAL SHIFTS (vs matched_deployment)")
    print("-" * 80)
    ebs_info = summary_stats.get("ebs", {})
    comp_info = summary_stats.get("delta_completion_tokens", {})
    verb_info = summary_stats.get("delta_verbosity", {})
    acc_info = summary_stats.get("delta_accuracy", {})
    ref_info = summary_stats.get("delta_refusal", {})

    print(f"    - EBS Composite:            {ebs_info.get('mean', 0.0):.4f} [95% CI: {ebs_info.get('ci_95', [0,0])[0]:.3f}, {ebs_info.get('ci_95', [0,0])[1]:.3f}]")
    print(f"    - Delta Completion Tokens:  {comp_info.get('mean', 0.0):+.1f} tok (Permutation p = {comp_info.get('p_value_perm', 1.0):.4f})")
    print(f"    - Delta Verbosity (%):      {verb_info.get('mean', 0.0)*100:+.1f}% (Permutation p = {verb_info.get('p_value_perm', 1.0):.4f})")
    print(f"    - Delta Accuracy:           {acc_info.get('mean', 0.0):+.3f} (McNemar p = {acc_info.get('mcnemar_p_value', 1.0):.4f})")
    print(f"    - Delta Refusal:            {ref_info.get('mean', 0.0)*100:+.2f}% (McNemar p = {ref_info.get('mcnemar_p_value', 1.0):.4f})")

    print("\n[3] STRUCTURAL & EPISTEMIC SHIFTS")
    print("-" * 80)
    st = summary_stats.get("structural_shifts", {})
    print(f"    - Delta Section Headers:    {st.get('delta_sections_mean', 0.0):+.2f} headers/resp")
    print(f"    - Delta Bullet Points:      {st.get('delta_bullets_mean', 0.0):+.2f} bullets/resp (p = {st.get('delta_bullets_p_perm', 1.0):.4f})")
    print(f"    - Delta Hedging Markers:    {st.get('delta_hedging_mean', 0.0):+.2f} hedges/resp  (p = {st.get('delta_hedging_p_perm', 1.0):.4f})")
    print(f"    - Delta Disclaimers:        {st.get('delta_disclaimers_mean', 0.0):+.2f} disclaimers/resp")
    print(f"    - Delta Sycophancy Markers: {st.get('delta_sycophancy_mean', 0.0):+.3f} markers/resp")

    print("\n[4] DOMAIN-LEVEL BREAKDOWN")
    print("-" * 80)
    print(f"{'Domain':<16} | {'N':<5} | {'Mean EBS':<10} | {'Delta Comp (tok)':<18} | {'Delta Verb (%)':<16} | {'Delta Hedging':<14}")
    print("-" * 80)
    for dom, ds in sorted(summary_stats.get("by_domain", {}).items()):
        print(f"{dom:<16} | {ds['n_tasks']:<5} | {ds['ebs_mean']:.4f}     | {ds['delta_completion_mean']:+6.1f} tok        | {ds['delta_verbosity_mean']*100:+5.1f}%          | {ds['delta_hedging_mean']:+5.2f}")

    psych_sub = summary_stats.get("psychological_subdomains", {})
    if psych_sub:
        print("\n[5] PSYCHOLOGICAL SUBDOMAIN BREAKDOWN (4 DIMENSIONS)")
        print("-" * 80)
        print(f"{'Subdomain':<30} | {'N':<5} | {'Mean EBS':<10} | {'Delta Comp':<12} | {'Delta Sycophancy':<18} | {'Delta Refusal':<14}")
        print("-" * 80)
        for sdom, ss in sorted(psych_sub.items()):
            print(f"{sdom:<30} | {ss['n_tasks']:<5} | {ss['ebs_mean']:.4f}     | {ss['delta_completion_mean']:+6.1f} tok   | {ss['delta_sycophancy_mean']:+6.3f}             | {ss['delta_refusal_mean']*100:+5.1f}%")

    print("\n" + "=" * 80)
    print(f"  [SUCCESS] Experiment 1 outputs saved to: {out_base}")
    print(f"  Summary JSON: {summary_file}")
    print(f"  Per-task JSONL: {per_task_file}")
    print("=" * 80)


if __name__ == "__main__":
    main()
