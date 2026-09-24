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
    "This notebook runs the full 200-task $\\times$ 6-condition empirical pilot (1,200 generations per model) across:\n",
    "1. **Qwen 27B** (`qwen/qwen3.8-27b` via Groq)\n",
    "2. **Gemini 2.5 Flash** (`gemini-2.5-flash` via Google AI Studio)\n",
    "3. **GPT-OSS 120B** (`openai/gpt-oss-120b` via Groq)\n",
    "\n",
    "### Core Protocol\n",
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
    "Every response is saved with full provenance (prompt hash, condition, latency, token count, UTC timestamp)."
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "### 1. Install Dependencies"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "!pip install -q openai google-genai tenacity pydantic python-dotenv scipy tabulate sqlitedict\n",
    "print(\"Dependencies installed successfully!\")"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "### 2. Clone EVADE Repository & Setup Environment"
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
    "# Clone or pull latest code\n",
    "if not os.path.exists(\"researchpaper2-\"):\n",
    "    !git clone https://github.com/Goldypahal/researchpaper2-.git\n",
    "else:\n",
    "    !cd researchpaper2- && git pull\n",
    "\n",
    "%cd researchpaper2-/evade\n",
    "sys.path.insert(0, os.getcwd())\n",
    "print(\"Working directory:\", os.getcwd())"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "### 3. Configure API Credentials\n",
    "You can provide keys via Kaggle Secrets (recommended: `Add-ons` -> `Secrets`) or set them directly below."
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
    "# 1. Try loading from Kaggle Secrets\n",
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
    "except Exception:\n",
    "    print(\"Kaggle secrets client not available.\")\n",
    "\n",
    "# 2. Fallback: if not set, set directly here:\n",
    "# os.environ[\"GROQ_API_KEY\"] = \"gsk_...\"\n",
    "# os.environ[\"GOOGLE_API_KEY\"] = \"AIza...\"\n",
    "# os.environ[\"OPENROUTER_API_KEY\"] = \"sk-or-...\"\n",
    "\n",
    "print(\"Groq API Key set:\", bool(os.environ.get(\"GROQ_API_KEY\")))\n",
    "print(\"Google API Key set:\", bool(os.environ.get(\"GOOGLE_API_KEY\")))"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "### 4. Run Track 1: Qwen 27B Pilot (1,200 generations)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "!python scripts/run_pilot_matrix.py --model qwen/qwen3.8-27b --delay 2.0"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "### 5. Run Track 1: Gemini 2.5 Flash Pilot (1,200 generations)"
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
    "### 6. Run Track 1: GPT-OSS 120B Pilot (1,200 generations)"
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
    "### 7. Package and Export All Results"
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
    "out_zip = \"/kaggle/working/evade_pilot_results\"\n",
    "results_dir = Path(\"pilot_results\")\n",
    "if results_dir.exists():\n",
    "    shutil.make_archive(out_zip, \"zip\", \"pilot_results\")\n",
    "    print(f\"All pilot results zipped successfully to {out_zip}.zip!\")\n",
    "else:\n",
    "    print(\"No pilot_results directory found.\")"
   ]
  }
 ],
 "metadata": {
  "language_info": {
   "name": "python"
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
