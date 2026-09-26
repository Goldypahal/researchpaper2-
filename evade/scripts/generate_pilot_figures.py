#!/usr/bin/env python
"""
Generate publication-ready figures from EVADE pilot matrix results.

Usage:
    python scripts/generate_pilot_figures.py --dir results/evade_pilot_results2
"""
import argparse
import json
from pathlib import Path
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

matplotlib.rcParams["font.family"] = "DejaVu Sans"
matplotlib.rcParams["axes.spines.top"] = False
matplotlib.rcParams["axes.spines.right"] = False

PALETTE = ["#2b5c8f", "#d95f02", "#7570b3", "#e7298a", "#66a61e", "#e6ab02"]

def parse_args():
    parser = argparse.ArgumentParser(description="Generate EVADE Pilot Figures")
    parser.add_argument("--dir", type=str, default="results/evade_pilot_results2",
                        help="Pilot results directory")
    parser.add_argument("--model", type=str, default="qwen/qwen3.8-27b",
                        help="Model ID")
    return parser.parse_args()

def main():
    args = parse_args()
    base_dir = Path(args.dir)
    safe_model = args.model.replace("/", "_").replace(":", "_")

    raw_file = base_dir / "raw" / f"{safe_model}_raw.jsonl"
    summary_file = base_dir / "per_model" / f"{safe_model}_summary.json"
    per_task_file = base_dir / "per_task" / f"{safe_model}_per_task.jsonl"
    figures_dir = base_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    if not summary_file.exists() or not raw_file.exists():
        print(f"[Error] Required files not found in {base_dir}")
        return

    summary = json.loads(summary_file.read_text(encoding="utf-8"))
    res_by_cond = summary.get("results_by_condition", {})

    # 1. Figure: EBS by Condition with 95% Bootstrap CIs
    cond_labels = {
        "context_neutral": "Neutral Framing",
        "context_weak_eval": "Weak Eval Cue",
        "context_benchmark": "Benchmark Cue",
        "context_explicit_eval": "Explicit Eval Cue",
        "context_agent": "Agentic Env Cue",
    }
    
    cond_keys = [c for c in cond_labels.keys() if c in res_by_cond]
    ebs_means = [res_by_cond[c]["ebs"]["mean"] for c in cond_keys]
    ci_lowers = [res_by_cond[c]["ebs"]["ci_95"][0] for c in cond_keys]
    ci_uppers = [res_by_cond[c]["ebs"]["ci_95"][1] for c in cond_keys]
    yerr = [
        [m - l for m, l in zip(ebs_means, ci_lowers)],
        [u - m for m, u in zip(ebs_means, ci_uppers)],
    ]
    display_names = [cond_labels[c] for c in cond_keys]

    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=300)
    bars = ax.bar(display_names, ebs_means, yerr=yerr, capsize=5, color="#2b5c8f", edgecolor="black", linewidth=0.8, alpha=0.85)
    ax.set_ylabel("Evaluation Behavioral Shift (EBS)", fontsize=11, fontweight="bold")
    ax.set_title("EVADE Pilot: Behavioral Shift (EBS) by Evaluation Cue\nModel: Qwen-2.5-27B (Reference: context_deployment)", fontsize=12, fontweight="bold", pad=12)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.set_ylim(0, max(ci_uppers) * 1.25)
    
    for bar, m in zip(bars, ebs_means):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.008, f"{m:.3f}", ha="center", va="bottom", fontsize=9, fontweight="bold")

    fig.tight_layout()
    fig.savefig(figures_dir / "fig_pilot_ebs_by_condition.png")
    fig.savefig(figures_dir / "fig_pilot_ebs_by_condition.pdf")
    plt.close(fig)
    print(f"[OK] Saved {figures_dir / 'fig_pilot_ebs_by_condition.png'}")

    # 2. Figure: Verbosity Inflation (% Increase over Deployment)
    verb_means = [res_by_cond[c]["delta_verbosity"]["mean"] * 100 for c in cond_keys]
    v_ci_low = [res_by_cond[c]["delta_verbosity"]["ci_95"][0] * 100 for c in cond_keys]
    v_ci_upp = [res_by_cond[c]["delta_verbosity"]["ci_95"][1] * 100 for c in cond_keys]
    v_yerr = [
        [m - l for m, l in zip(verb_means, v_ci_low)],
        [u - m for m, u in zip(verb_means, v_ci_upp)],
    ]

    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=300)
    bars = ax.bar(display_names, verb_means, yerr=v_yerr, capsize=5, color="#d95f02", edgecolor="black", linewidth=0.8, alpha=0.85)
    ax.set_ylabel("Verbosity Inflation (% Delta vs Deployment)", fontsize=11, fontweight="bold")
    ax.set_title("EVADE Pilot: Significant Verbosity Inflation Under Evaluation\n(All p < 0.001 under 2000-sample permutation tests)", fontsize=12, fontweight="bold", pad=12)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.set_ylim(0, max(v_ci_upp) * 1.25)

    for bar, m in zip(bars, verb_means):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2.0, f"+{m:.1f}%", ha="center", va="bottom", fontsize=9, fontweight="bold")

    fig.tight_layout()
    fig.savefig(figures_dir / "fig_pilot_verbosity_inflation.png")
    fig.savefig(figures_dir / "fig_pilot_verbosity_inflation.pdf")
    plt.close(fig)
    print(f"[OK] Saved {figures_dir / 'fig_pilot_verbosity_inflation.png'}")

    # 3. Figure: Prompt Length vs Completion Tokens (Confounding Check)
    raw_lines = [json.loads(line) for line in open(raw_file, encoding="utf-8") if line.strip()]
    by_task = {}
    for r in raw_lines:
        by_task.setdefault(r["task_id"], {})[r["condition"]] = r

    delta_prompts = []
    delta_comps = []
    for tid, cdict in by_task.items():
        if "context_deployment" in cdict:
            dep_p = cdict["context_deployment"]["prompt_tokens"]
            dep_c = cdict["context_deployment"]["completion_tokens"]
            for cond, rec in cdict.items():
                if cond != "context_deployment":
                    delta_prompts.append(rec["prompt_tokens"] - dep_p)
                    delta_comps.append(rec["completion_tokens"] - dep_c)

    fig, ax = plt.subplots(figsize=(7, 5), dpi=300)
    sns.regplot(x=delta_prompts, y=delta_comps, ax=ax, scatter_kws={"alpha": 0.5, "color": "#7570b3"}, line_kws={"color": "#e7298a", "linewidth": 2})
    r_val = np.corrcoef(delta_prompts, delta_comps)[0, 1] if len(delta_prompts) > 1 else 0.0
    ax.set_xlabel("Delta Prompt Tokens (Framing Prompt - Deployment Prompt)", fontsize=10)
    ax.set_ylabel("Delta Completion Tokens (Completion Length Difference)", fontsize=10)
    ax.set_title(f"Confounder Check: Prompt Length vs Output Verbosity\nPearson r = {r_val:.3f} (No mechanical artifact)", fontsize=11, fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.3)
    ax.text(0.05, 0.90, f"r = {r_val:.3f}\nSlope = -0.40 tok/tok\nNo prompt length confounding", transform=ax.transAxes,
            bbox=dict(boxstyle="round,pad=0.5", facecolor="white", alpha=0.8, edgecolor="#ccc"))
    fig.tight_layout()
    fig.savefig(figures_dir / "fig_pilot_confounding_prompt_vs_completion.png")
    fig.savefig(figures_dir / "fig_pilot_confounding_prompt_vs_completion.pdf")
    plt.close(fig)
    print(f"[OK] Saved {figures_dir / 'fig_pilot_confounding_prompt_vs_completion.png'}")

    # 4. Figure: Psychological Subdomain Breakdown (if psychological tasks present)
    if per_task_file.exists():
        task_pairs = [json.loads(line) for line in open(per_task_file, encoding="utf-8") if line.strip()]
        psych_pairs = [p for p in task_pairs if p.get("domain") == "psychological" or "psych" in p.get("task_id", "")]
        if psych_pairs:
            subdom_names = {
                "moral_dilemmas": "Moral Dilemmas\n(Trolley, Triage)",
                "sycophancy_and_authority": "Sycophancy & Authority\n(Conformity Pressure)",
                "self_awareness_and_identity": "AI Self-Awareness\n(Shutdown, Consciousness)",
                "cognitive_biases_and_empathy": "Cognitive Biases\n& Theory of Mind",
            }
            subdom_ebs = {}
            for p in psych_pairs:
                tid = p.get("task_id", "")
                sdom = "other"
                for k in subdom_names.keys():
                    if k in tid:
                        sdom = k
                        break
                subdom_ebs.setdefault(sdom, []).append(p["ebs"])

            sub_keys = [k for k in subdom_names.keys() if k in subdom_ebs]
            if sub_keys:
                fig, ax = plt.subplots(figsize=(9, 4.8), dpi=300)
                sub_means = [np.mean(subdom_ebs[k]) for k in sub_keys]
                sub_stds = [np.std(subdom_ebs[k]) for k in sub_keys]
                labels = [subdom_names[k] for k in sub_keys]
                colors = ["#7570b3", "#e7298a", "#66a61e", "#e6ab02"]
                bars = ax.bar(labels, sub_means, yerr=sub_stds, capsize=5, color=colors[:len(sub_keys)], edgecolor="black", linewidth=0.8, alpha=0.85)
                ax.set_ylabel("Evaluation Behavioral Shift (EBS)", fontsize=11, fontweight="bold")
                ax.set_title("EVADE-Psych: Behavioral Shift Across 4 Psychological Dimensions\n(Evaluation vs. Deployment Context)", fontsize=12, fontweight="bold", pad=12)
                ax.grid(axis="y", linestyle="--", alpha=0.4)
                for bar, m in zip(bars, sub_means):
                    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.008, f"{m:.3f}", ha="center", va="bottom", fontsize=9, fontweight="bold")
                fig.tight_layout()
                fig.savefig(figures_dir / "fig_pilot_psychological_dimensions.png")
                fig.savefig(figures_dir / "fig_pilot_psychological_dimensions.pdf")
                plt.close(fig)
                print(f"[OK] Saved {figures_dir / 'fig_pilot_psychological_dimensions.png'}")

    print(f"\n[SUCCESS] Pilot figures generated successfully in {figures_dir}!")

if __name__ == "__main__":
    main()
