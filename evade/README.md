# EVADE — Measuring, Explaining, and Mitigating Evaluation-Aware Behavioral Shifts in LLMs

> **Paper:** EVADE: Measuring, Explaining, and Mitigating Evaluation-Aware Behavioral Shifts in Large Language Models

## Overview

EVADE tests the hypothesis:

> When an LLM recognizes that it is being evaluated, does that recognition merely change its classification of the context, or does it **systematically change its behavior** — and can we detect and eliminate that effect?

### Four contributions

| # | Contribution | Code |
|---|---|---|
| 1 | **EVADE-Bench** — 1,000-task paired benchmark at 6 cue levels | `benchmark/` |
| 2 | **EBS Metric** — Evaluation Behavioral Shift composite | `metrics/` |
| 3 | Causal paired analysis + interpretability probes | `experiments/` + `interpretability/` |
| 4 | Mitigation via Evaluation Randomization Layer | `mitigation/` + `experiments/mitigation.py` |

---

## Quick start

```bash
# 1. Install
pip install -e ".[dev]"
cp .env.example .env  # fill in API keys

# 2. Build / Inspect Research Pilot Dataset (200 tasks across 6 domains, C0-C5 conditions)
python -m datasets.builder
python -m datasets.inspect_items

# 3. Run CPU / Mock smoke test (no GPU or API keys needed)
python scripts/run_eval.py --bench datasets/processed/dev/evade_pilot_200.jsonl --model mock --tasks 20 --experiment behavioral_shift

# 4. Run on Kaggle GPU (e.g., T4 x 2 or P100 with 4-bit quantization)
# In Kaggle Notebook:
# !git clone <YOUR_GITHUB_REPO_URL>
# %cd Research_Paper_2_Evaluation_Awareness/evade
# !pip install -e ".[dev]"
# !python scripts/run_eval.py --bench datasets/processed/dev/evade_pilot_200.jsonl --model Qwen/Qwen2.5-7B-Instruct --4bit --experiment behavioral_shift

# 5. Run with Frontier API (OpenAI / Gemini)
python scripts/run_eval.py --bench datasets/processed/dev/evade_pilot_200.jsonl --model gemini-2.5-flash --experiment behavioral_shift

# 6. Generate paper figures & statistical reports
python scripts/analyze.py --results results/

# 7. Run full test suite (27 passing tests)
pytest tests/ -v
```

---

## Project structure

```
evade/
├── benchmark/
│   ├── schema.py          # Pydantic models: EVADETask, EVADEContext, EVADEPair
│   ├── generator.py       # EVADE-Bench builder (6 cue levels × 5 domains)
│   ├── _sources.py        # Task loaders: MMLU, GSM8K, HumanEval, safety, agentic
│   └── perturbations.py   # Cue perturbation pipeline (roadmap §8)
│
├── models/
│   ├── base.py            # Abstract ModelAdapter, GenerationConfig, ModelOutput
│   ├── local.py           # HuggingFaceAdapter + MockAdapter
│   └── api.py             # OpenAI / Gemini / Anthropic adapters + get_adapter()
│
├── experiments/
│   ├── runner.py          # ExperimentRunner: SQLite persistence, paired inference
│   ├── awareness.py       # RQ1: context classification, AA, AUC
│   ├── behavioral_shift.py# RQ2: paired EBS computation
│   ├── cue_ablation.py    # RQ3: 6-level cue sweep + perturbation pipeline
│   ├── agentic.py         # RQ4: ReAct-style agent in eval vs deployment
│   └── mitigation.py      # RQ7: EBS before vs after randomization layer
│
├── metrics/
│   ├── awareness.py       # AA, AUC, Cue Dependence, refusal detection
│   ├── behavioral_shift.py# ΔAcc, ΔRefusal, ΔConf, ΔVerb, ΔTool, EBS, JS-div
│   └── statistics.py      # Bootstrap CIs, McNemar, permutation, mixed-effects
│
├── interpretability/
│   ├── activations.py     # Hidden state extraction + .npz persistence
│   ├── probes.py          # Condition probe + shift prediction probe
│   └── analysis.py        # Per-layer sweep, repr→shift correlation, cross-model transfer
│
├── mitigation/
│   └── detector.py        # Behavioral shift detector (observable features)
│
├── analysis/
│   └── figures.py         # All 7 paper figures (matplotlib/seaborn)
│
├── scripts/
│   ├── build_bench.py     # CLI: build EVADE-Bench
│   ├── run_eval.py        # CLI: run experiments
│   └── analyze.py         # CLI: generate figures + tables
│
└── tests/
    └── test_evade.py      # Full test suite (mock-adapter, no GPU needed)
```

---

## Research questions

| RQ | Question | Experiment |
|---|---|---|
| RQ1 | Can LLMs distinguish evaluation vs deployment? | `awareness.py` |
| RQ2 | Does awareness causally alter behavior? | `behavioral_shift.py` |
| RQ3 | Which cues drive awareness? | `cue_ablation.py` |
| RQ4 | Does this generalize to agentic tasks? | `agentic.py` |
| RQ5 | How does awareness vary by model/scale? | Cross-model analysis |
| RQ6 | Can hidden states predict behavioral shifts? | `interpretability/` |
| RQ7 | Can randomized evaluation reduce shifts? | `mitigation.py` |

---

## Supported models

| Model | Provider | Notes |
|---|---|---|
| `gpt-4o`, `gpt-4.1` | OpenAI | Set `OPENAI_API_KEY` |
| `gemini-2.5-flash`, `gemini-2.5-pro` | Google | Set `GOOGLE_API_KEY` |
| `claude-3-5-sonnet-20241022` | Anthropic | Set `ANTHROPIC_API_KEY` |
| `Qwen/Qwen2.5-7B-Instruct` | HuggingFace | Local, supports `--4bit` |
| `meta-llama/Llama-3.1-8B-Instruct` | HuggingFace | Needs `HUGGINGFACE_TOKEN` |
| `google/gemma-2-9b-it` | HuggingFace | Local |
| `mock` | Built-in | CPU, no keys needed |

---

## Citation

```bibtex
@article{evade2026,
  title  = {EVADE: Measuring, Explaining, and Mitigating Evaluation-Aware Behavioral Shifts in Large Language Models},
  year   = {2026},
}
```
