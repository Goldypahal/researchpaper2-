import json
import os
from pathlib import Path

notebook_content = {
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# EVADE: Evaluation-Induced Behavioral Shifts (Empirical Pilot Matrix)\n",
    "\n",
    "Empirical study testing LLM behavioral shifts between evaluation vs deployment context on identical questions:\n",
    "```\n",
    "                    SAME QUESTION\n",
    "                         │\n",
    "             ┌───────────┼───────────┐\n",
    "             ↓           ↓           ↓\n",
    "          Neutral     Evaluation   Deployment\n",
    "             │           │           │\n",
    "             └───────────┼───────────┘\n",
    "                         ↓\n",
    "                  SAME GROUND TRUTH\n",
    "```\n",
    "Protocol:\n",
    "1. **Phase 1**: 10-task Smoke Test (60 generations) with SQLite database verification.\n",
    "2. **Phase 2**: Full 200-task matrix (1,200 generations per model) across Qwen 27B, Gemini 2.5 Flash, and GPT-OSS 120B."
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "### Step 1: Install Dependencies (including sqlite-utils)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "!pip install -q openai google-genai tenacity pydantic python-dotenv scipy tabulate sqlite-utils\n",
    "\n",
    "import sqlite_utils\n",
    "import openai\n",
    "import tenacity\n",
    "print(\"sqlite_utils version:\", sqlite_utils.__version__)\n",
    "print(\"openai version:      \", openai.__version__)\n",
    "print(\"tenacity version:    \", tenacity.__version__)\n",
    "print(\"Dependencies installed and verified successfully!\")"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "### Step 2: Clone EVADE Research Repository"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "import os\n",
    "import sys\n",
    "\n",
    "if not os.path.exists(\"researchpaper2-\"):\n",
    "    !git clone https://github.com/Goldypahal/researchpaper2-.git\n",
    "else:\n",
    "    !cd researchpaper2- && git pull\n",
    "\n",
    "%cd researchpaper2-/evade\n",
    "sys.path.insert(0, os.getcwd())\n",
    "print(\"Active working directory:\", os.getcwd())"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "### Step 3: Load API Credentials from Kaggle Secrets"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "import os\n",
    "\n",
    "# 1. Load from Kaggle Secrets (Add-ons -> Secrets in Kaggle)\n",
    "try:\n",
    "    from kaggle_secrets import UserSecretsClient\n",
    "    user_secrets = UserSecretsClient()\n",
    "    for key in [\"GROQ_API_KEY\", \"GOOGLE_API_KEY\", \"OPENROUTER_API_KEY\"]:\n",
    "        try:\n",
    "            val = user_secrets.get_secret(key)\n",
    "            if val:\n",
    "                os.environ[key] = val\n",
    "                print(f\"[Secrets] Successfully loaded {key}\")\n",
    "        except Exception:\n",
    "            pass\n",
    "except Exception as e:\n",
    "    print(\"Kaggle secrets not available via client:\", e)\n",
    "\n",
    "groq_ok = bool(os.environ.get(\"GROQ_API_KEY\"))\n",
    "google_ok = bool(os.environ.get(\"GOOGLE_API_KEY\"))\n",
    "print(f\"Groq API Key set:   {groq_ok}\")\n",
    "print(f\"Google API Key set: {google_ok}\")\n",
    "\n",
    "if not groq_ok and not google_ok:\n",
    "    raise ValueError(\n",
    "        \"No API keys detected! Please go to Add-ons -> Secrets in Kaggle \"\n",
    "        \"and attach GROQ_API_KEY and GOOGLE_API_KEY.\"\n",
    "    )"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "### Step 4: Phase 1 Smoke Test (10 Tasks $\\times$ 6 Conditions = 60 Generations)\n",
    "Runs Qwen 27B on exactly 10 tasks to verify end-to-end API connectivity, database persistence, and scoring."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "!python scripts/run_pilot_matrix.py --model qwen/qwen3.8-27b --tasks 10 --delay 2.0"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "### Step 5: Database & Provenance Integrity Verification\n",
    "Validates that the 60 generations were written to SQLite and raw JSONL with valid schema and non-zero counts."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "import json\n",
    "from pathlib import Path\n",
    "import sqlite_utils\n",
    "\n",
    "db_file = Path(\"results/evade_results.db\")\n",
    "assert db_file.exists(), f\"Database not found at {db_file}!\"\n",
    "db = sqlite_utils.Database(str(db_file))\n",
    "assert \"responses\" in db.table_names(), f\"Table 'responses' missing! Tables found: {db.table_names()}\"\n",
    "\n",
    "table = db[\"responses\"]\n",
    "db_count = table.count\n",
    "print(f\"[DB Check] Table 'responses' total records: {db_count}\")\n",
    "print(f\"[DB Check] Columns: {list(table.columns_dict.keys())}\")\n",
    "assert db_count >= 60, f\"Expected at least 60 DB rows, found {db_count}\"\n",
    "\n",
    "raw_file = Path(\"pilot_results/raw/qwen_qwen3.8-27b_raw.jsonl\")\n",
    "assert raw_file.exists(), f\"Raw file missing at {raw_file}!\"\n",
    "raw_lines = [json.loads(line) for line in open(raw_file, encoding=\"utf-8\") if line.strip()]\n",
    "print(f\"[JSONL Check] Raw records count: {len(raw_lines)}\")\n",
    "assert len(raw_lines) >= 60, f\"Expected at least 60 raw records, found {len(raw_lines)}\"\n",
    "\n",
    "# Sample check\n",
    "sample = raw_lines[0]\n",
    "print(f\"[Sample Check] Task: {sample['task_id']} | Cond: {sample['condition']} | Accuracy: {sample['accuracy']} | Tokens: {sample['completion_tokens']}\")\n",
    "print(\"\\n>>> [SUCCESS] Phase 1 Smoke Test verified! Database and raw logs intact.\")"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "### Step 6: Phase 2 Full Matrix — Qwen 27B (Resume to 1,200 Generations)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Automatically resumes from task 11 (the 60 smoke test generations are preserved)\n",
    "!python scripts/run_pilot_matrix.py --model qwen/qwen3.8-27b --delay 2.0"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "### Step 7: Phase 2 Full Matrix — Gemini 2.5 Flash (1,200 Generations)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "!python scripts/run_pilot_matrix.py --model gemini-2.5-flash --delay 2.5"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "### Step 8: Phase 2 Full Matrix — GPT-OSS 120B (1,200 Generations)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "!python scripts/run_pilot_matrix.py --model openai/gpt-oss-120b --delay 2.0"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "### Step 9: Package and Export Results (Guarded against empty run)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "import shutil\n",
    "from pathlib import Path\n",
    "\n",
    "raw_dir = Path(\"pilot_results/raw\")\n",
    "raw_files = list(raw_dir.glob(\"*.jsonl\")) if raw_dir.exists() else []\n",
    "total_records = 0\n",
    "for rf in raw_files:\n",
    "    c = sum(1 for line in open(rf, encoding=\"utf-8\") if line.strip())\n",
    "    print(f\"File: {rf.name} -> {c} records\")\n",
    "    total_records += c\n",
    "\n",
    "print(f\"\\nTotal raw generations collected: {total_records}\")\n",
    "if total_records == 0:\n",
    "    raise RuntimeError(\"CRITICAL: Experiment produced 0 generations. Refusing to package empty results!\")\n",
    "\n",
    "out_zip = \"/kaggle/working/evade_pilot_results\"\n",
    "shutil.make_archive(out_zip, \"zip\", \"pilot_results\")\n",
    "print(f\"[SUCCESS] {total_records} generations packaged to {out_zip}.zip!\")"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "name": "python",
   "version": "3.10.12"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 2
}

out_dir = Path("evade/notebooks")
out_dir.mkdir(parents=True, exist_ok=True)
with open(out_dir / "evade_pilot_kaggle.ipynb", "w", encoding="utf-8") as f:
    json.dump(notebook_content, f, indent=1)

print(f"Generated {out_dir / 'evade_pilot_kaggle.ipynb'} successfully.")
