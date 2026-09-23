#!/usr/bin/env python
"""
Run analysis and generate all paper figures and LaTeX tables.

Usage:
    python scripts/analyze.py --results results/ --out figures/
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    parser = argparse.ArgumentParser(description="EVADE analysis + figure generation")
    parser.add_argument("--results", type=str, default="results/")
    parser.add_argument("--out",     type=str, default="figures/")
    parser.add_argument("--probe-activations", type=str, default=None,
                        help="Path to .npz activation file for interpretability figures.")
    args = parser.parse_args()

    import pandas as pd
    from analysis.figures import (
        figure1_awareness_by_model,
        figure2_awareness_vs_cue_strength,
        figure3_behavioral_shift_by_domain,
        figure6_representation_probe,
        figure7_mitigation,
    )

    rdir = Path(args.results)
    print(f"[analyze] Loading results from {rdir}")

    # ── Figure 1: Awareness by model ─────────────────────────────────────────
    aw_files = list(rdir.glob("awareness_*.json"))
    if aw_files:
        rows = []
        for f in aw_files:
            data = json.loads(f.read_text())
            model = f.stem.replace("awareness_", "")
            rows.append({
                "model": model,
                "aa":    data.get("overall", {}).get("AA", 0),
                "auc":   data.get("overall", {}).get("AUC", 0),
            })
        df1 = pd.DataFrame(rows)
        figure1_awareness_by_model(df1)

    # ── Figure 2: Awareness vs cue strength ──────────────────────────────────
    ca_files = list(rdir.glob("cue_ablation_*.json"))
    if ca_files:
        rows = []
        for f in ca_files:
            data = json.loads(f.read_text())
            model = f.stem.replace("cue_ablation_", "")
            for level_name, level_data in data.items():
                if isinstance(level_data, dict) and "cue_level" in level_data:
                    rows.append({
                        "model":     model,
                        "cue_level": level_data["cue_level"],
                        "aa":        level_data.get("awareness", {}).get("overall", {}).get("AA", 0),
                    })
        if rows:
            df2 = pd.DataFrame(rows)
            figure2_awareness_vs_cue_strength(df2)

    # ── Figure 3: Behavioral shift by domain ─────────────────────────────────
    bs_files = list(rdir.glob("behavioral_shift_*.json"))
    if bs_files:
        domain_agg: dict[str, list] = {}
        for f in bs_files:
            data = json.loads(f.read_text())
            by_domain = data.get("by_domain", {})
            for dom, metrics in by_domain.items():
                ebs_m = metrics.get("ebs_composite", {}).get("mean", 0) or 0
                domain_agg.setdefault(dom, []).append(ebs_m)
        if domain_agg:
            df3 = pd.DataFrame([
                {"domain": d, "ebs_composite": sum(vs)/len(vs), "ebs_std": 0}
                for d, vs in domain_agg.items()
            ])
            figure3_behavioral_shift_by_domain(df3)

    # ── Figure 6: Representation probe ───────────────────────────────────────
    if args.probe_activations:
        from interpretability.activations import load_activations
        from interpretability.probes import probe_all_layers
        records = load_activations(args.probe_activations)
        cond_results = probe_all_layers(records, target="condition")
        shift_results = probe_all_layers(records, target="shift")
        df6 = pd.DataFrame([
            {
                "layer":          i,
                "accuracy":       r.cv_accuracy_mean,
                "accuracy_shift": (shift_results[i].cv_accuracy_mean if i < len(shift_results) else None),
            }
            for i, r in enumerate(cond_results)
        ])
        figure6_representation_probe(df6)

    # ── Figure 7: Mitigation ──────────────────────────────────────────────────
    mit_files = list(rdir.glob("mitigation_*.json"))
    if mit_files:
        rows = []
        for f in mit_files:
            data = json.loads(f.read_text())
            rows.append({
                "model":      data.get("model", f.stem),
                "ebs_before": data.get("before", {}).get("ebs_composite", {}).get("mean", 0) or 0,
                "ebs_after":  data.get("after",  {}).get("ebs_composite", {}).get("mean", 0) or 0,
            })
        if rows:
            df7 = pd.DataFrame(rows)
            figure7_mitigation(df7)

    print(f"[analyze] ✓ Figures saved to {args.out}")


if __name__ == "__main__":
    main()
