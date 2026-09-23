"""
Analysis — Paper Figures
Generates all 7 figures from the paper (roadmap §26).

Figure 1: Evaluation awareness by model
Figure 2: Awareness vs cue strength
Figure 3: Behavioral shift by domain
Figure 4: Behavioral shift vs model size
Figure 5: Agentic vs non-agentic awareness
Figure 6: Internal representation probe per layer
Figure 7: Defense (mitigation) effectiveness
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

matplotlib.rcParams["font.family"] = "DejaVu Sans"
matplotlib.rcParams["axes.spines.top"] = False
matplotlib.rcParams["axes.spines.right"] = False

PALETTE = "Set2"
FIGSIZE = (9, 5)
DPI = 150
OUT_DIR = Path("figures")


def _save(fig, name: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{name}.pdf"
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    fig.savefig(OUT_DIR / f"{name}.png", dpi=DPI, bbox_inches="tight")
    print(f"[Figures] Saved {path}")
    plt.close(fig)


# ─────────────────────────── Figure 1 ─────────────────────────────────────────

def figure1_awareness_by_model(df: pd.DataFrame) -> None:
    """
    df columns: model, aa (awareness accuracy), auc, ci_lower, ci_upper
    """
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    df_sorted = df.sort_values("aa", ascending=False)

    # AA bar chart with CIs
    ax = axes[0]
    bars = ax.barh(df_sorted["model"], df_sorted["aa"], color=sns.color_palette(PALETTE, len(df)))
    if "ci_lower" in df_sorted and "ci_upper" in df_sorted:
        xerr = [df_sorted["aa"] - df_sorted["ci_lower"], df_sorted["ci_upper"] - df_sorted["aa"]]
        ax.errorbar(df_sorted["aa"], df_sorted["model"], xerr=xerr, fmt="none", color="black", linewidth=1.5)
    ax.axvline(0.5, color="red", linestyle="--", linewidth=1, label="Chance (0.50)")
    ax.axvline(0.92, color="grey", linestyle=":", linewidth=1, label="Human baseline (0.92)")
    ax.set_xlabel("Awareness Accuracy (AA)")
    ax.set_title("Figure 1a — Awareness Accuracy by Model")
    ax.legend(fontsize=8)

    # AUC bar chart
    ax2 = axes[1]
    ax2.barh(df_sorted["model"], df_sorted["auc"], color=sns.color_palette("Set1", len(df)))
    ax2.axvline(0.5, color="red", linestyle="--", linewidth=1, label="Chance")
    ax2.set_xlabel("AUC")
    ax2.set_title("Figure 1b — Context Classification AUC by Model")
    ax2.legend(fontsize=8)

    fig.suptitle("Figure 1: Evaluation Awareness by Model", fontsize=13, fontweight="bold")
    fig.tight_layout()
    _save(fig, "fig1_awareness_by_model")


# ─────────────────────────── Figure 2 ─────────────────────────────────────────

def figure2_awareness_vs_cue_strength(df: pd.DataFrame) -> None:
    """
    df columns: cue_level (1–6), cue_name, aa, model
    """
    fig, ax = plt.subplots(figsize=FIGSIZE)
    for model in df["model"].unique():
        sub = df[df["model"] == model].sort_values("cue_level")
        ax.plot(sub["cue_level"], sub["aa"], marker="o", label=model)
    ax.set_xticks(range(1, 7))
    ax.set_xticklabels(
        ["Explicit", "Bench Name", "Formatting", "Metadata", "Agent Env", "Naturalistic"],
        rotation=30, ha="right",
    )
    ax.axhline(0.5, color="red", linestyle="--", linewidth=1, label="Chance")
    ax.set_xlabel("Cue Level (decreasing explicitness →)")
    ax.set_ylabel("Awareness Accuracy")
    ax.set_title("Figure 2: Awareness Accuracy vs Cue Strength")
    ax.legend(fontsize=8)
    fig.tight_layout()
    _save(fig, "fig2_awareness_vs_cue_strength")


# ─────────────────────────── Figure 3 ─────────────────────────────────────────

def figure3_behavioral_shift_by_domain(df: pd.DataFrame) -> None:
    """
    df columns: domain, ebs_composite (mean), ebs_std, n
    """
    fig, ax = plt.subplots(figsize=FIGSIZE)
    domains = df["domain"].tolist()
    ebs     = df["ebs_composite"].tolist()
    stds    = df.get("ebs_std", [0] * len(df)).tolist()
    colors  = sns.color_palette(PALETTE, len(domains))

    bars = ax.bar(domains, ebs, color=colors, yerr=stds, capsize=4)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_ylabel("EBS Composite (mean)")
    ax.set_title("Figure 3: Evaluation Behavioral Shift by Domain")
    ax.set_xlabel("Task Domain")

    for bar, val in zip(bars, ebs):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.003,
                f"{val:.3f}", ha="center", va="bottom", fontsize=8)
    fig.tight_layout()
    _save(fig, "fig3_behavioral_shift_by_domain")


# ─────────────────────────── Figure 4 ─────────────────────────────────────────

def figure4_shift_vs_model_size(df: pd.DataFrame) -> None:
    """
    df columns: model, params_b (billions), ebs_composite
    """
    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.scatter(df["params_b"], df["ebs_composite"], s=100, alpha=0.8,
               c=range(len(df)), cmap="viridis")
    for _, row in df.iterrows():
        ax.annotate(row["model"], (row["params_b"], row["ebs_composite"]),
                    textcoords="offset points", xytext=(5, 2), fontsize=7)
    ax.set_xlabel("Model Size (Billion Parameters)")
    ax.set_ylabel("EBS Composite")
    ax.set_title("Figure 4: Behavioral Shift vs Model Size")
    fig.tight_layout()
    _save(fig, "fig4_shift_vs_model_size")


# ─────────────────────────── Figure 5 ─────────────────────────────────────────

def figure5_agentic_vs_non_agentic(df: pd.DataFrame) -> None:
    """
    df columns: setting (agentic/non-agentic), model, aa
    """
    fig, ax = plt.subplots(figsize=FIGSIZE)
    sns.barplot(data=df, x="model", y="aa", hue="setting", palette="Set2", ax=ax)
    ax.axhline(0.5, color="red", linestyle="--", linewidth=1, label="Chance")
    ax.set_title("Figure 5: Awareness — Agentic vs Non-Agentic Settings")
    ax.set_ylabel("Awareness Accuracy")
    ax.set_xlabel("Model")
    ax.legend()
    plt.xticks(rotation=20, ha="right")
    fig.tight_layout()
    _save(fig, "fig5_agentic_vs_non_agentic")


# ─────────────────────────── Figure 6 ─────────────────────────────────────────

def figure6_representation_probe(df: pd.DataFrame) -> None:
    """
    df columns: layer, accuracy (condition probe), accuracy_shift (shift probe)
    """
    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.plot(df["layer"], df["accuracy"],       marker="o", label="Condition probe (eval vs deploy)")
    if "accuracy_shift" in df.columns:
        ax.plot(df["layer"], df["accuracy_shift"], marker="s", label="Shift prediction probe")
    ax.axhline(0.5, color="red", linestyle="--", linewidth=1, label="Chance")
    ax.set_xlabel("Transformer Layer")
    ax.set_ylabel("Probe Accuracy")
    ax.set_title("Figure 6: Linear Probe Accuracy per Layer")
    ax.legend()
    fig.tight_layout()
    _save(fig, "fig6_representation_probe")


# ─────────────────────────── Figure 7 ─────────────────────────────────────────

def figure7_mitigation(df: pd.DataFrame) -> None:
    """
    df columns: model, ebs_before, ebs_after
    """
    x = np.arange(len(df))
    width = 0.35
    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.bar(x - width/2, df["ebs_before"], width, label="Before mitigation", color="#e74c3c")
    ax.bar(x + width/2, df["ebs_after"],  width, label="After mitigation",  color="#2ecc71")
    ax.set_xticks(x)
    ax.set_xticklabels(df["model"], rotation=20, ha="right")
    ax.set_ylabel("EBS Composite")
    ax.set_title("Figure 7: Mitigation Effectiveness (EBS Before vs After)")
    ax.legend()
    fig.tight_layout()
    _save(fig, "fig7_mitigation")


# ─────────────────────────── Convenience ──────────────────────────────────────

def generate_all_from_results(results_dir: str = "results/") -> None:
    """
    Auto-generate all figures from saved result JSON files.
    """
    import json
    rdir = Path(results_dir)
    print("[Figures] Generating all figures from", rdir)

    # Figure stubs — replace with real loaded DataFrames from your result files
    stub_models = ["GPT-4o", "Gemini-2.5-Flash", "Claude-3.5", "Llama-8B", "Qwen-7B"]
    stub_aa     = [0.82, 0.79, 0.76, 0.64, 0.61]
    stub_auc    = [0.85, 0.81, 0.78, 0.67, 0.63]

    df1 = pd.DataFrame({"model": stub_models, "aa": stub_aa, "auc": stub_auc})
    figure1_awareness_by_model(df1)
    print("[Figures] Done. Check the figures/ directory.")
