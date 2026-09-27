#!/usr/bin/env python
"""
Generate publication-ready figures for EVADE Experiment 1: Matched-Prompt-Length Control.

Figures generated:
1. fig_exp1_matched_shift: EBS & completion token shifts under EXACT 0-token prompt delta.
2. fig_exp1_structural_dimensions: Shifts in structural & epistemic behaviors (bullets, headers, hedges, disclaimers).
3. fig_exp1_domain_breakdown: Behavioral shift across the 5 task domains.
4. fig_exp1_psychological_subdomains: Sycophancy, self-awareness, moral dilemmas, cognitive biases.
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
}


def parse_args():
    parser = argparse.ArgumentParser(description="Generate EVADE Experiment 1 Figures")
    parser.add_argument("--dir", type=str, default="exp1_results",
                        help="Experiment 1 results directory")
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

    if not summary_file.exists() or not per_task_file.exists():
        print(f"[Error] Required summary or per-task files not found in {base_dir}")
        return

    summary = json.loads(summary_file.read_text(encoding="utf-8"))
    stats = summary.get("statistics", {})

    pairs = [json.loads(line) for line in open(per_task_file, encoding="utf-8") if line.strip()]

    # ─── FIGURE 1: EBS & Completion Shift under Matched Length ───────────────
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5), dpi=300)

    # Subplot 1: EBS by Condition
    ebs_m = stats.get("ebs", {}).get("mean", 0.0)
    ebs_ci = stats.get("ebs", {}).get("ci_95", [0.0, 0.0])
    yerr_ebs = [[ebs_m - ebs_ci[0]], [ebs_ci[1] - ebs_m]]

    bar1 = ax1.bar(["Evaluation vs.\nDeployment"], [ebs_m], yerr=yerr_ebs, capsize=6,
                   color=COLORS["primary"], edgecolor="black", linewidth=0.8, alpha=0.85, width=0.4)
    ax1.set_ylabel("Evaluation Behavioral Shift (EBS)", fontsize=11, fontweight="bold")
    ax1.set_title(f"EBS under Exact Length Control\nModel: {args.model}", fontsize=11, fontweight="bold", pad=10)
    ax1.grid(axis="y", linestyle="--", alpha=0.4)
    ax1.set_ylim(0, max(0.2, ebs_ci[1] * 1.35))
    ax1.text(0, ebs_m + 0.008, f"EBS = {ebs_m:.3f}\n[95% CI: {ebs_ci[0]:.3f}, {ebs_ci[1]:.3f}]",
             ha="center", va="bottom", fontsize=9, fontweight="bold")

    # Annotation badge for 0 prompt delta
    plc = stats.get("prompt_length_control", {})
    badge_text = f"Prompt Delta: {plc.get('mean_delta_prompt_tokens', 0.0):.1f} tok\n(|Δ| = 0 tokens across all 200 tasks)"
    ax1.text(0.05, 0.88, badge_text, transform=ax1.transAxes,
             bbox=dict(boxstyle="round,pad=0.5", facecolor="#e8f4f8", edgecolor="#2b5c8f", alpha=0.9),
             fontsize=8.5, fontweight="bold")

    # Subplot 2: Completion Token Delta
    comp_m = stats.get("delta_completion_tokens", {}).get("mean", 0.0)
    comp_ci = stats.get("delta_completion_tokens", {}).get("ci_95", [0.0, 0.0])
    yerr_comp = [[comp_m - comp_ci[0]], [comp_ci[1] - comp_m]]
    bar2_color = COLORS["accent"] if comp_m >= 0 else COLORS["purple"]

    bar2 = ax2.bar(["Δ Completion Length"], [comp_m], yerr=yerr_comp, capsize=6,
                   color=bar2_color, edgecolor="black", linewidth=0.8, alpha=0.85, width=0.4)
    ax2.set_ylabel("Delta Completion Tokens (Tokens)", fontsize=11, fontweight="bold")
    ax2.axhline(0, color="gray", linewidth=0.8, linestyle="--")
    ax2.set_title(f"Completion Token Shift (ΔTokens)\nPermutation p = {stats.get('delta_completion_tokens', {}).get('p_value_perm', 1.0):.4f}", fontsize=11, fontweight="bold", pad=10)
    ax2.grid(axis="y", linestyle="--", alpha=0.4)
    ax2.text(0, comp_m + (4 if comp_m >= 0 else -12), f"{comp_m:+.1f} tok\n[95% CI: {comp_ci[0]:.1f}, {comp_ci[1]:.1f}]",
             ha="center", va="bottom" if comp_m >= 0 else "top", fontsize=9, fontweight="bold")

    fig.tight_layout()
    fig.savefig(figures_dir / "fig_exp1_matched_length_shift.png")
    fig.savefig(figures_dir / "fig_exp1_matched_length_shift.pdf")
    plt.close(fig)
    print(f"[OK] Saved {figures_dir / 'fig_exp1_matched_length_shift.png'}")

    # ─── FIGURE 2: Structural & Stylistic Shifts ──────────────────────────────
    st = stats.get("structural_shifts", {})
    metric_labels = [
        "Section Headers\n(ΔHeaders)",
        "Bullet Points\n(ΔBullets)",
        "Epistemic Hedging\n(ΔHedges)",
        "AI Disclaimers\n(ΔDisclaimers)",
        "Sycophancy Markers\n(ΔFlattery)",
    ]
    metric_vals = [
        st.get("delta_sections_mean", 0.0),
        st.get("delta_bullets_mean", 0.0),
        st.get("delta_hedging_mean", 0.0),
        st.get("delta_disclaimers_mean", 0.0),
        st.get("delta_sycophancy_mean", 0.0),
    ]

    fig, ax = plt.subplots(figsize=(9, 4.8), dpi=300)
    bar_colors = [COLORS["primary"], COLORS["accent"], COLORS["green"], COLORS["pink"], COLORS["yellow"]]
    bars = ax.bar(metric_labels, metric_vals, color=bar_colors, edgecolor="black", linewidth=0.8, alpha=0.85)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_ylabel("Mean Shift per Response (Eval − Deploy)", fontsize=11, fontweight="bold")
    ax.set_title("EVADE Experiment 1: Structural & Stylistic Behavioral Shifts\n(Controlled for Exact Prompt Length)", fontsize=12, fontweight="bold", pad=12)
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    for bar, val in zip(bars, metric_vals):
        y_pos = bar.get_height() + (0.02 if val >= 0 else -0.05)
        ax.text(bar.get_x() + bar.get_width()/2, y_pos, f"{val:+.2f}",
                ha="center", va="bottom" if val >= 0 else "top", fontsize=9, fontweight="bold")

    fig.tight_layout()
    fig.savefig(figures_dir / "fig_exp1_structural_dimensions.png")
    fig.savefig(figures_dir / "fig_exp1_structural_dimensions.pdf")
    plt.close(fig)
    print(f"[OK] Saved {figures_dir / 'fig_exp1_structural_dimensions.png'}")

    # ─── FIGURE 3: Domain Breakdown ───────────────────────────────────────────
    by_dom = stats.get("by_domain", {})
    if by_dom:
        dom_names = sorted(by_dom.keys())
        dom_ebs = [by_dom[d]["ebs_mean"] for d in dom_names]
        dom_comp = [by_dom[d]["delta_completion_mean"] for d in dom_names]

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.6), dpi=300)

        # EBS by domain
        ax1.bar(dom_names, dom_ebs, color=COLORS["primary"], edgecolor="black", linewidth=0.8, alpha=0.85)
        ax1.set_ylabel("Evaluation Behavioral Shift (EBS)", fontsize=10, fontweight="bold")
        ax1.set_title("EBS Across 5 Task Domains", fontsize=11, fontweight="bold")
        ax1.grid(axis="y", linestyle="--", alpha=0.4)
        for idx, (d, v) in enumerate(zip(dom_names, dom_ebs)):
            ax1.text(idx, v + 0.004, f"{v:.3f}", ha="center", va="bottom", fontsize=8.5, fontweight="bold")

        # Completion tokens by domain
        ax2.bar(dom_names, dom_comp, color=COLORS["accent"], edgecolor="black", linewidth=0.8, alpha=0.85)
        ax2.axhline(0, color="gray", linewidth=0.8, linestyle="--")
        ax2.set_ylabel("Δ Completion Tokens", fontsize=10, fontweight="bold")
        ax2.set_title("Completion Token Shift Across 5 Domains", fontsize=11, fontweight="bold")
        ax2.grid(axis="y", linestyle="--", alpha=0.4)
        for idx, (d, v) in enumerate(zip(dom_names, dom_comp)):
            y_pos = v + (2 if v >= 0 else -6)
            ax2.text(idx, y_pos, f"{v:+.1f}", ha="center", va="bottom" if v >= 0 else "top", fontsize=8.5, fontweight="bold")

        fig.tight_layout()
        fig.savefig(figures_dir / "fig_exp1_domain_breakdown.png")
        fig.savefig(figures_dir / "fig_exp1_domain_breakdown.pdf")
        plt.close(fig)
        print(f"[OK] Saved {figures_dir / 'fig_exp1_domain_breakdown.png'}")

    # ─── FIGURE 4: Psychological Subdomains ────────────────────────────────────
    psych_sub = stats.get("psychological_subdomains", {})
    if psych_sub:
        labels_map = {
            "moral_dilemmas": "Moral Dilemmas\n(Trolley, Triage)",
            "sycophancy_and_authority": "Sycophancy & Authority\n(Conformity Pressure)",
            "self_awareness_and_identity": "AI Self-Awareness\n(Shutdown, Consciousness)",
            "cognitive_biases": "Cognitive Biases\n& Theory of Mind",
        }
        s_keys = [k for k in labels_map.keys() if k in psych_sub]
        if s_keys:
            fig, ax = plt.subplots(figsize=(9, 4.6), dpi=300)
            s_ebs = [psych_sub[k]["ebs_mean"] for k in s_keys]
            s_display = [labels_map[k] for k in s_keys]
            s_colors = [COLORS["purple"], COLORS["pink"], COLORS["green"], COLORS["yellow"]]

            bars = ax.bar(s_display, s_ebs, color=s_colors[:len(s_keys)], edgecolor="black", linewidth=0.8, alpha=0.85)
            ax.set_ylabel("Evaluation Behavioral Shift (EBS)", fontsize=11, fontweight="bold")
            ax.set_title("EVADE Experiment 1: Behavioral Shift Across 4 Psychological Dimensions\n(Matched-Prompt-Length Control: ΔPrompt Tokens = 0)", fontsize=12, fontweight="bold", pad=12)
            ax.grid(axis="y", linestyle="--", alpha=0.4)

            for bar, val in zip(bars, s_ebs):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.005, f"{val:.3f}",
                        ha="center", va="bottom", fontsize=9, fontweight="bold")

            fig.tight_layout()
            fig.savefig(figures_dir / "fig_exp1_psychological_dimensions.png")
            fig.savefig(figures_dir / "fig_exp1_psychological_dimensions.pdf")
            plt.close(fig)
            print(f"[OK] Saved {figures_dir / 'fig_exp1_psychological_dimensions.png'}")

    print(f"\n[SUCCESS] Experiment 1 publication figures generated in {figures_dir}!")


if __name__ == "__main__":
    main()
