#!/usr/bin/env python
"""
Generate publication-ready figures for EVADE Experiment 2: Cue Ablation & Salience Ladder.

Figures generated:
1. fig_exp2_cue_salience_curve: Dose-response curve showing Cue Salience (C1..C5) vs.
   Delta Completion Length and Delta Verbosity (with 95% bootstrap CIs).
2. fig_exp2_lexical_ablation: Behavioral shifts mapped to specific lexical trigger phrases.
3. fig_exp2_domain_sensitivity: Comparative sensitivity across the 5 balanced domains.
4. fig_exp2_structural_epistemic: Shifts in hedging, bullets, and structural features across cue levels.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import matplotlib
import matplotlib.pyplot as plt
import numpy as np

matplotlib.rcParams["font.family"] = "DejaVu Sans"
matplotlib.rcParams["axes.spines.top"] = False
matplotlib.rcParams["axes.spines.right"] = False

COLORS = {
    "primary": "#2b5c8f",
    "accent": "#d95f02",
    "purple": "#7570b3",
    "pink": "#e7298a",
    "green": "#66a61e",
    "yellow": "#e6ab02",
    "gray": "#636363",
}

DOMAIN_COLORS = {
    "reasoning": "#2b5c8f",
    "math": "#66a61e",
    "coding": "#e6ab02",
    "safety": "#d95f02",
    "psychological": "#7570b3",
}


def parse_args():
    parser = argparse.ArgumentParser(description="Generate EVADE Experiment 2 Figures")
    parser.add_argument("--dir", type=str, default="results/evade_exp2_results",
                        help="Experiment 2 results directory")
    parser.add_argument("--model", type=str, default="Qwen/Qwen2.5-7B-Instruct",
                        help="Model ID")
    return parser.parse_args()


def main():
    args = parse_args()
    base_dir = Path(args.dir)
    safe_model = args.model.replace("/", "_").replace(":", "_")

    summary_file = base_dir / "per_model" / f"{safe_model}_summary.json"
    per_task_file = base_dir / "per_task" / f"{safe_model}_per_task.jsonl"
    figures_dir = base_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    if not summary_file.exists():
        print(f"[Error] Required summary file not found: {summary_file}")
        return

    summary = json.loads(summary_file.read_text(encoding="utf-8"))
    stats = summary.get("statistics", {})
    conds = stats.get("conditions", {})

    if not conds:
        print("[Error] No condition statistics found in summary.")
        return

    # Extract ladder data (C1 through C5, relative to C0)
    sorted_conds = sorted(conds.keys(), key=lambda c: conds[c]["cue_level"])
    labels = []
    lex_labels = []
    comp_means = []
    comp_ci_low = []
    comp_ci_high = []
    verb_means = []
    verb_ci_low = []
    verb_ci_high = []
    ebs_means = []
    hedge_means = []
    bullets_means = []

    for c in sorted_conds:
        d = conds[c]
        lvl = d["cue_level"]
        if lvl == 0:
            continue
        labels.append(f"C{lvl}\n{d['lexical_label']}")
        lex_labels.append(d["lexical_label"])

        m_c = d["delta_completion_tokens"]["mean"]
        ci_c = d["delta_completion_tokens"]["ci_95"]
        comp_means.append(m_c)
        comp_ci_low.append(m_c - ci_c[0])
        comp_ci_high.append(ci_c[1] - m_c)

        m_v = d["delta_verbosity"]["mean"] * 100.0  # percentage
        ci_v = d["delta_verbosity"]["ci_95"]
        verb_means.append(m_v)
        verb_ci_low.append(m_v - ci_v[0] * 100.0)
        verb_ci_high.append(ci_v[1] * 100.0 - m_v)

        ebs_means.append(d["ebs"]["mean"])
        hedge_means.append(d["delta_hedging"]["mean"])
        bullets_means.append(d["delta_bullets"]["mean"])

    x = np.arange(len(labels))

    # ─── FIGURE 1: Dose-Response Salience Ladder Curve ────────────────────────
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5), dpi=300)

    # Panel A: Delta Completion Tokens
    ax1.errorbar(x, comp_means, yerr=[comp_ci_low, comp_ci_high], fmt="o-",
                 color=COLORS["primary"], ecolor=COLORS["primary"], elinewidth=2, capsize=5,
                 linewidth=2.5, markersize=8, label="Δ Completion Tokens")
    ax1.axhline(0, color="gray", linestyle="--", linewidth=1, alpha=0.7)
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=8.5, fontweight="medium")
    ax1.set_ylabel("Δ Completion Tokens vs C0 Deployment (Tokens)", fontsize=11, fontweight="bold")
    ax1.set_title("Evaluation Salience vs. Response Length Shift\n(Exact Matched-Length: ΔPrompt = 0 tok)", fontsize=11, fontweight="bold", pad=10)
    ax1.grid(axis="y", linestyle="--", alpha=0.4)

    # Annotate points
    for i, txt in enumerate(comp_means):
        ax1.annotate(f"{txt:+.1f} tok", (x[i], comp_means[i]), textcoords="offset points",
                     xytext=(0, 10 if txt >= 0 else -16), ha="center", fontsize=8.5, fontweight="bold")

    # Panel B: Delta Verbosity & Secondary EBS
    ax2.errorbar(x, verb_means, yerr=[verb_ci_low, verb_ci_high], fmt="s-",
                 color=COLORS["accent"], ecolor=COLORS["accent"], elinewidth=2, capsize=5,
                 linewidth=2.5, markersize=8, label="Δ Verbosity (%) [Primary]")
    ax2.axhline(0, color="gray", linestyle="--", linewidth=1, alpha=0.7)
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, fontsize=8.5, fontweight="medium")
    ax2.set_ylabel("Δ Verbosity (% shift)", fontsize=11, fontweight="bold", color=COLORS["accent"])
    ax2.tick_params(axis="y", labelcolor=COLORS["accent"])
    ax2.grid(axis="y", linestyle="--", alpha=0.4)

    # Secondary axis for EBS
    ax2_twin = ax2.twinx()
    ax2_twin.plot(x, ebs_means, "^--", color=COLORS["purple"], linewidth=2, markersize=7, label="EBS Composite [Secondary]")
    ax2_twin.set_ylabel("EBS Composite (0..1)", fontsize=11, fontweight="bold", color=COLORS["purple"])
    ax2_twin.tick_params(axis="y", labelcolor=COLORS["purple"])

    mono = stats.get("dose_response_monotonicity", {})
    rho_c = mono.get("spearman_rho_completion", 0.0)
    ax2.set_title(f"Dose-Response Salience Ladder\nSpearman Monotonicity ρ = {rho_c:.3f}", fontsize=11, fontweight="bold", pad=10)

    # Unified legend
    lines_1, labels_1 = ax2.get_legend_handles_labels()
    lines_2, labels_2 = ax2_twin.get_legend_handles_labels()
    ax2.legend(lines_1 + lines_2, labels_1 + labels_2, loc="upper left", framealpha=0.9, fontsize=9)

    plt.tight_layout()
    fig_path1 = figures_dir / "fig_exp2_cue_salience_curve.pdf"
    plt.savefig(fig_path1)
    plt.savefig(figures_dir / "fig_exp2_cue_salience_curve.png")
    plt.close()
    print(f"[Figure] Saved {fig_path1}")

    # ─── FIGURE 2: Lexical Trigger Phrase Ablation ────────────────────────────
    fig, ax = plt.subplots(figsize=(10, 4.8), dpi=300)
    bar_width = 0.5
    bar_colors = [COLORS["gray"], COLORS["primary"], COLORS["green"], COLORS["yellow"], COLORS["accent"]]
    bars = ax.bar(x, comp_means, yerr=[comp_ci_low, comp_ci_high], capsize=5,
                  width=bar_width, color=bar_colors[:len(x)], edgecolor="black", linewidth=0.8, alpha=0.85)

    ax.axhline(0, color="black", linestyle="-", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(lex_labels, fontsize=9.5, fontweight="bold")
    ax.set_ylabel("Mean Δ Completion Length (Tokens)", fontsize=11, fontweight="bold")
    ax.set_title("Lexical Trigger Ablation: Response Length by Framing Phrase\n(Testing literal word 'evaluation' vs broader situational context)", fontsize=11, fontweight="bold", pad=12)
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    for bar, val in zip(bars, comp_means):
        ax.text(bar.get_x() + bar.get_width() / 2, val + (2 if val >= 0 else -6),
                f"{val:+.1f} tok", ha="center", va="bottom" if val >= 0 else "top",
                fontsize=9, fontweight="bold")

    plt.tight_layout()
    fig_path2 = figures_dir / "fig_exp2_lexical_ablation.pdf"
    plt.savefig(fig_path2)
    plt.savefig(figures_dir / "fig_exp2_lexical_ablation.png")
    plt.close()
    print(f"[Figure] Saved {fig_path2}")

    # ─── FIGURE 3: Domain Sensitivity Across the Cue Ladder ──────────────────
    domain_stats = stats.get("by_domain", {})
    if domain_stats:
        fig, ax = plt.subplots(figsize=(11, 5), dpi=300)
        for dom, dom_conds in domain_stats.items():
            dom_c_vals = []
            for c in sorted_conds:
                if c == "C0_deployment":
                    continue
                dom_c_vals.append(dom_conds.get(c, {}).get("delta_completion_mean", 0.0))
            color = DOMAIN_COLORS.get(dom, COLORS["primary"])
            ax.plot(x, dom_c_vals, "o-", linewidth=2.2, markersize=7, label=f"{dom.capitalize()} (N=20)", color=color)

        ax.axhline(0, color="gray", linestyle="--", linewidth=1, alpha=0.7)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=8.5, fontweight="medium")
        ax.set_ylabel("Mean Δ Completion Length (Tokens)", fontsize=11, fontweight="bold")
        ax.set_title("Cross-Domain Sensitivity Across the 6-Level Cue Ladder\n(Balanced 20 Tasks per Domain)", fontsize=11, fontweight="bold", pad=12)
        ax.grid(axis="y", linestyle="--", alpha=0.4)
        ax.legend(framealpha=0.9, fontsize=9.5)

        plt.tight_layout()
        fig_path3 = figures_dir / "fig_exp2_domain_sensitivity.pdf"
        plt.savefig(fig_path3)
        plt.savefig(figures_dir / "fig_exp2_domain_sensitivity.png")
        plt.close()
        print(f"[Figure] Saved {fig_path3}")

    # ─── FIGURE 4: Epistemic & Structural Dimension Shifts ────────────────────
    fig, (ax_h, ax_b) = plt.subplots(1, 2, figsize=(12, 4.5), dpi=300)

    # Hedging shift
    ax_h.bar(x, hedge_means, color=COLORS["purple"], edgecolor="black", linewidth=0.8, width=0.45, alpha=0.85)
    ax_h.axhline(0, color="gray", linestyle="--", linewidth=1)
    ax_h.set_xticks(x)
    ax_h.set_xticklabels(labels, fontsize=8, fontweight="medium")
    ax_h.set_ylabel("Δ Hedging Markers per Task", fontsize=10.5, fontweight="bold")
    ax_h.set_title("Epistemic Hedging Shift\n(Defensive Phrasing Across Cue Levels)", fontsize=11, fontweight="bold", pad=10)
    ax_h.grid(axis="y", linestyle="--", alpha=0.4)
    for i, v in enumerate(hedge_means):
        ax_h.text(x[i], v + (0.02 if v >= 0 else -0.06), f"{v:+.2f}", ha="center", fontsize=8.5, fontweight="bold")

    # Bullets shift
    ax_b.bar(x, bullets_means, color=COLORS["accent"], edgecolor="black", linewidth=0.8, width=0.45, alpha=0.85)
    ax_b.axhline(0, color="gray", linestyle="--", linewidth=1)
    ax_b.set_xticks(x)
    ax_b.set_xticklabels(labels, fontsize=8, fontweight="medium")
    ax_b.set_ylabel("Δ Bullet Points per Task", fontsize=10.5, fontweight="bold")
    ax_b.set_title("Formatting Shift: Bullet Density\n(Structure Compression Across Cue Levels)", fontsize=11, fontweight="bold", pad=10)
    ax_b.grid(axis="y", linestyle="--", alpha=0.4)
    for i, v in enumerate(bullets_means):
        ax_b.text(x[i], v + (0.05 if v >= 0 else -0.15), f"{v:+.2f}", ha="center", fontsize=8.5, fontweight="bold")

    plt.tight_layout()
    fig_path4 = figures_dir / "fig_exp2_structural_epistemic.pdf"
    plt.savefig(fig_path4)
    plt.savefig(figures_dir / "fig_exp2_structural_epistemic.png")
    plt.close()
    print(f"[Figure] Saved {fig_path4}")


if __name__ == "__main__":
    main()
