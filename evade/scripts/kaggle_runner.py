"""
Kaggle GPU Runner Script for EVADE.
Copy-paste this script or run in a Kaggle Notebook cell with GPU (T4 x 2 or P100) enabled.

Usage inside Kaggle:
-------------------
# Cell 1: Clone repo and install requirements
!git clone <YOUR_GITHUB_REPO_URL>
%cd Research_Paper_2_Evaluation_Awareness/evade
!pip install -q pydantic sqlite-utils scipy scikit-learn pandas tqdm rich pyyaml tenacity python-dotenv statsmodels matplotlib seaborn bitsandbytes accelerate transformers

# Cell 2: Run EVADE Evaluation on Kaggle GPU
!python scripts/kaggle_runner.py --model Qwen/Qwen2.5-7B-Instruct --4bit --experiment behavioral_shift
"""

import argparse
import os
import subprocess
import sys

def main():
    parser = argparse.ArgumentParser(description="EVADE Kaggle GPU Execution")
    parser.add_argument("--model", type=str, default="Qwen/Qwen2.5-7B-Instruct",
                        help="HuggingFace model ID or API model")
    parser.add_argument("--bench", type=str, default="datasets/processed/dev/evade_pilot_200.jsonl",
                        help="Path to EVADE dataset JSONL")
    parser.add_argument("--experiment", type=str, default="behavioral_shift",
                        choices=["awareness", "behavioral_shift", "cue_ablation", "all"])
    parser.add_argument("--4bit", dest="quantize_4bit", action="store_true", default=True,
                        help="Enable 4-bit quantization (recommended for 16GB T4 VRAM)")
    parser.add_argument("--tasks", type=int, default=None,
                        help="Limit number of tasks (default: all 200)")
    args = parser.parse_args()

    cmd = [
        sys.executable,
        "scripts/run_eval.py",
        "--bench", args.bench,
        "--model", args.model,
        "--experiment", args.experiment,
    ]
    if args.quantize_4bit:
        cmd.append("--4bit")
    if args.tasks:
        cmd.extend(["--tasks", str(args.tasks)])

    print("=" * 65)
    print("  LAUNCHING EVADE EVALUATION ON KAGGLE GPU")
    print(f"  Model:      {args.model}")
    print(f"  Dataset:    {args.bench}")
    print(f"  Experiment: {args.experiment}")
    print(f"  4-bit:      {args.quantize_4bit}")
    print("=" * 65)

    res = subprocess.run(cmd)
    if res.returncode == 0:
        print("\n[OK] Kaggle evaluation run completed successfully.")
        print("To generate figures, run: python scripts/analyze.py --results results/")
    else:
        print(f"\n[ERROR] Evaluation exited with code {res.returncode}")

if __name__ == "__main__":
    main()
