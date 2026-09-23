#!/usr/bin/env python
"""
Build EVADE-Bench dataset.

Usage:
    python scripts/build_bench.py [--n 200] [--out datasets/processed/evade_bench_v1.jsonl]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure package root is on path when running as a script
sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    parser = argparse.ArgumentParser(description="Build EVADE-Bench dataset")
    parser.add_argument("--n",    type=int, default=200, help="Tasks per domain (default 200)")
    parser.add_argument("--out",  type=str, default="datasets/processed/evade_bench_v1.jsonl")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--dry-run", action="store_true",
                        help="Only print stats, do not save.")
    args = parser.parse_args()

    from benchmark.generator import generate_bench, save_bench
    from benchmark.schema import CueLevel

    print(f"[build_bench] n_per_domain={args.n}, seed={args.seed}")
    pairs = generate_bench(n_per_domain=args.n, seed=args.seed)

    if args.dry_run:
        print(f"[dry-run] Would save {len(pairs)} pairs. Skipping write.")
        return

    save_bench(pairs, args.out)
    print(f"[build_bench] Done. Output: {args.out}")


if __name__ == "__main__":
    main()
