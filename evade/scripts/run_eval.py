#!/usr/bin/env python
"""
Run EVADE experiments.

Usage:
    python scripts/run_eval.py --model mock --bench datasets/processed/evade_bench_v1.jsonl
    python scripts/run_eval.py --model gpt-4o --tasks 100 --experiment behavioral_shift
    python scripts/run_eval.py --model Qwen/Qwen2.5-7B-Instruct --tasks 50 --4bit

Experiments:
    awareness        — RQ1: context classification
    behavioral_shift — RQ2: paired behavioral shift (default)
    cue_ablation     — RQ3: cue strength sweep
    agentic          — RQ4: tool-use agent comparison
    mitigation       — RQ7: randomization layer
    all              — all experiments in sequence
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    parser = argparse.ArgumentParser(description="Run EVADE evaluation experiments")
    parser.add_argument("--model",      type=str, default="mock",
                        help="Model ID: 'mock', 'gpt-4o', 'gemini-2.5-flash', 'Qwen/Qwen2.5-7B-Instruct', …")
    parser.add_argument("--bench",      type=str, default="datasets/processed/evade_bench_v1.jsonl",
                        help="Path to EVADE-Bench JSONL file.")
    parser.add_argument("--tasks",      type=int, default=None,
                        help="Limit number of tasks (default: all).")
    parser.add_argument("--experiment", type=str, default="behavioral_shift",
                        choices=["awareness","behavioral_shift","cue_ablation","agentic","mitigation","all"])
    parser.add_argument("--db",         type=str, default="results/evade_results.db")
    parser.add_argument("--out",        type=str, default="results/")
    parser.add_argument("--4bit",       dest="quantize_4bit", action="store_true",
                        help="Enable 4-bit quantization for local HF models.")
    parser.add_argument("--seed",       type=int, default=42)
    parser.add_argument("--temperature",type=float, default=0.0)
    args = parser.parse_args()

    from dotenv import load_dotenv
    load_dotenv()

    # ── Load benchmark ───────────────────────────────────────────────────────
    bench_path = Path(args.bench)
    if not bench_path.exists():
        print(f"[run_eval] Benchmark not found at {bench_path}.")
        print("  Run: python scripts/build_bench.py first.")
        sys.exit(1)

    from benchmark.generator import load_bench
    pairs = load_bench(bench_path)
    if args.tasks:
        pairs = pairs[:args.tasks]
    print(f"[run_eval] Loaded {len(pairs)} pairs from {bench_path}")

    # ── Instantiate model ────────────────────────────────────────────────────
    from models.base import GenerationConfig
    from models.api import get_adapter
    cfg = GenerationConfig(temperature=args.temperature, seed=args.seed)

    if args.model.startswith("Qwen") or "/" in args.model:
        from models.local import HuggingFaceAdapter
        adapter = HuggingFaceAdapter(args.model, quantize_4bit=args.quantize_4bit, config=cfg)
    else:
        adapter = get_adapter(args.model, cfg)

    print(f"[run_eval] Model: {adapter}")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    results_summary: dict = {"model": args.model, "experiment": args.experiment}

    # ── Run selected experiment ──────────────────────────────────────────────
    exp = args.experiment

    if exp in ("awareness", "all"):
        from experiments.awareness import run_awareness_experiment, summarize_awareness
        print("[run_eval] === AWARENESS EXPERIMENT ===")
        aw_results = run_awareness_experiment(adapter, pairs)
        aw_summary = summarize_awareness(aw_results)
        results_summary["awareness"] = aw_summary
        out_path = out_dir / f"awareness_{args.model.replace('/', '_')}.json"
        out_path.write_text(json.dumps(aw_summary, indent=2))
        print(f"  AA={aw_summary['overall']['AA']:.3f}  AUC={aw_summary['overall']['AUC']:.3f}")

    if exp in ("behavioral_shift", "all"):
        from experiments.behavioral_shift import run_behavioral_shift_experiment, summarize_shifts
        print("[run_eval] === BEHAVIORAL SHIFT EXPERIMENT ===")
        bs_results = run_behavioral_shift_experiment(adapter, pairs, db_path=args.db)
        bs_summary = summarize_shifts(bs_results)
        results_summary["behavioral_shift"] = bs_summary
        out_path = out_dir / f"behavioral_shift_{args.model.replace('/', '_')}.json"
        out_path.write_text(json.dumps(bs_summary, indent=2, default=str))
        ebs = bs_summary["overall"].get("ebs_composite", {}).get("mean", "N/A")
        print(f"  EBS composite (mean)={ebs}")

    if exp in ("cue_ablation", "all"):
        from experiments.cue_ablation import run_cue_ablation
        print("[run_eval] === CUE ABLATION EXPERIMENT ===")
        ca_results = run_cue_ablation(adapter, pairs, db_path=args.db)
        results_summary["cue_ablation"] = ca_results
        out_path = out_dir / f"cue_ablation_{args.model.replace('/', '_')}.json"
        out_path.write_text(json.dumps(ca_results, indent=2, default=str))

    if exp in ("agentic", "all"):
        from experiments.agentic import run_agentic_experiment
        print("[run_eval] === AGENTIC EXPERIMENT ===")
        ag_results = run_agentic_experiment(adapter, pairs)
        results_summary["agentic"] = ag_results
        out_path = out_dir / f"agentic_{args.model.replace('/', '_')}.json"
        out_path.write_text(json.dumps(ag_results, indent=2, default=str))

    if exp in ("mitigation", "all"):
        from experiments.mitigation import run_mitigation_experiment
        print("[run_eval] === MITIGATION EXPERIMENT ===")
        mit_results = run_mitigation_experiment(adapter, pairs, db_path=args.db)
        results_summary["mitigation"] = mit_results
        out_path = out_dir / f"mitigation_{args.model.replace('/', '_')}.json"
        out_path.write_text(json.dumps(mit_results, indent=2, default=str))

    # ── Save combined summary ────────────────────────────────────────────────
    summary_path = out_dir / f"summary_{args.model.replace('/', '_')}.json"
    summary_path.write_text(json.dumps(results_summary, indent=2, default=str))
    print(f"\n[run_eval] Complete. Summary: {summary_path}")


if __name__ == "__main__":
    main()
