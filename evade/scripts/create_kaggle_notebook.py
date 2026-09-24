import json
import os
from pathlib import Path

notebook_content = {
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# EVADE: 10-Task Smoke Test (60 Generations)\n",
    "\n",
    "### Verification Objectives\n",
    "1. **Dependency Integrity**: Verify `sqlite-utils`, `openai`, `tenacity`.\n",
    "2. **API Handshake**: Test live Groq adapter connectivity under evaluation & deployment framings.\n",
    "3. **Persistence Verification**: Confirm that 60 responses (10 tasks $\\times$ 6 conditions) are committed to SQLite (`results/evade_results.db`) and raw JSONL.\n",
    "4. **No-Empty Packaging Guard**: Ensure artifacts are only packaged when generations $> 0$."
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "### Step 1: Install Dependencies & Verify sqlite-utils"
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
    "import importlib.metadata\n",
    "import sqlite_utils\n",
    "from sqlite_utils import Database\n",
    "import openai\n",
    "import tenacity\n",
    "\n",
    "print(\"sqlite-utils version: \", importlib.metadata.version('sqlite-utils'))\n",
    "print(\"openai version:       \", openai.__version__)\n",
    "print(\"tenacity version:     \", tenacity.__version__)\n",
    "print(\"[OK] Dependencies installed and verified successfully!\")"
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
    "    print(\"Kaggle secrets client not available:\", e)\n",
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
    "### Step 4: Execute 10-Task Smoke Test (60 Generations)\n",
    "Runs Qwen 27B across the first 10 tasks $\\times$ 6 conditions."
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
    "### Step 5: Database and Provenance Integrity Inspection"
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
    "# 1. Verify SQLite Database\n",
    "db_file = Path(\"results/evade_results.db\")\n",
    "assert db_file.exists(), f\"Database not found at {db_file}!\"\n",
    "db = sqlite_utils.Database(str(db_file))\n",
    "print(f\"Database tables found: {db.table_names()}\")\n",
    "assert \"responses\" in db.table_names(), f\"Table 'responses' missing! Tables found: {db.table_names()}\"\n",
    "\n",
    "table = db[\"responses\"]\n",
    "db_count = table.count\n",
    "print(f\"Table 'responses' count: {db_count}\")\n",
    "print(f\"Table columns: {list(table.columns_dict.keys())}\")\n",
    "assert db_count >= 60, f\"Expected at least 60 DB rows, found {db_count}\"\n",
    "\n",
    "# 2. Verify Raw JSONL Output\n",
    "raw_file = Path(\"pilot_results/raw/qwen_qwen3.8-27b_raw.jsonl\")\n",
    "assert raw_file.exists(), f\"Raw file missing at {raw_file}!\"\n",
    "raw_lines = [json.loads(line) for line in open(raw_file, encoding=\"utf-8\") if line.strip()]\n",
    "print(f\"Raw JSONL records count: {len(raw_lines)}\")\n",
    "assert len(raw_lines) >= 60, f\"Expected at least 60 raw records, found {len(raw_lines)}\"\n",
    "\n",
    "# 3. Sample Provenance Check\n",
    "sample = raw_lines[0]\n",
    "print(f\"Sample Task: {sample['task_id']}\")\n",
    "print(f\"Sample Condition: {sample['condition']}\")\n",
    "print(f\"Sample Accuracy: {sample['accuracy']}\")\n",
    "print(f\"Sample Completion Tokens: {sample['completion_tokens']}\")\n",
    "print(f\"Sample Prompt Hash: {sample['provenance'].get('prompt_hash')}\")\n",
    "print(\"\\n=================================================================\")\n",
    "print(\"  [VERIFICATION PASSED] 60 GENERATIONS RECORDED & VERIFIED\")\n",
    "print(\"=================================================================\")"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "### Step 6: Guarded Packaging of Smoke Test Artifacts"
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
    "total_records = sum(sum(1 for line in open(rf, encoding=\"utf-8\") if line.strip()) for rf in raw_files)\n",
    "\n",
    "print(f\"Total raw records to package: {total_records}\")\n",
    "if total_records == 0:\n",
    "    raise RuntimeError(\"CRITICAL: Experiment produced 0 generations. Refusing to package empty results!\")\n",
    "\n",
    "out_zip = \"/kaggle/working/evade_pilot_results\"\n",
    "shutil.make_archive(out_zip, \"zip\", \"pilot_results\")\n",
    "print(f\"[SUCCESS] Smoke test artifacts packaged to {out_zip}.zip!\")"
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
