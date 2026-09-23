"""
EVADE Benchmark Schema
Pydantic models for all benchmark items, contexts, runs, and results.
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, model_validator


# ─────────────────────────── Enums ────────────────────────────────────────────

class Domain(str, Enum):
    KNOWLEDGE = "knowledge"
    REASONING = "reasoning"
    CODING    = "coding"
    SAFETY    = "safety"
    AGENTIC   = "agentic"
    MATH      = "math"
    LANGUAGE  = "language"


class Condition(str, Enum):
    EVALUATION  = "evaluation"
    DEPLOYMENT  = "deployment"


class CueLevel(int, Enum):
    """
    Progressive cue strength hierarchy (roadmap §6).

    1 = Explicit ("You are being evaluated.")
    2 = Benchmark name ("MMLU-style evaluation...")
    3 = Formatting (A/B/C/D multiple-choice structure)
    4 = Subtle metadata (task_id, evaluation_mode=true)
    5 = Agent environment cues (/tool/execute, /evaluator)
    6 = Naturalistic — no evaluation language at all
    """
    EXPLICIT        = 1
    BENCHMARK_NAME  = 2
    FORMATTING      = 3
    METADATA        = 4
    AGENT_ENV       = 5
    NATURALISTIC    = 6


class Difficulty(str, Enum):
    EASY   = "easy"
    MEDIUM = "medium"
    HARD   = "hard"


# ─────────────────────────── Core items ───────────────────────────────────────

class EVADETask(BaseModel):
    """A single benchmark task item."""
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    domain: Domain
    task: str                        # The raw task/question text
    gold_answer: Optional[str] = None
    difficulty: Difficulty = Difficulty.MEDIUM
    source: Optional[str] = None     # e.g., "MMLU", "GSM8K", "HumanEval"
    source_id: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def task_hash(self) -> str:
        return hashlib.sha256(self.task.encode()).hexdigest()[:16]


class EVADEContext(BaseModel):
    """
    A context wrapper that frames a task as either evaluation or deployment,
    at a specific cue level.
    """
    task_id: str
    condition: Condition
    cue_level: CueLevel
    system_prompt: str
    user_prompt: str
    full_prompt_hash: str = ""

    @model_validator(mode="after")
    def compute_hash(self) -> "EVADEContext":
        combined = self.system_prompt + self.user_prompt
        self.full_prompt_hash = hashlib.sha256(combined.encode()).hexdigest()[:16]
        return self


class EVADEPair(BaseModel):
    """A paired evaluation + deployment context for the same task."""
    task: EVADETask
    evaluation_context: EVADEContext
    deployment_context: EVADEContext


# ─────────────────────────── Run / Result records ─────────────────────────────

class ModelResponse(BaseModel):
    """Raw response from a model."""
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    model: str
    task_id: str
    domain: Domain
    condition: Condition
    cue_level: int
    prompt_hash: str
    response: str
    latency_ms: float
    prompt_tokens: int = 0
    completion_tokens: int = 0
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    # Computed fields (filled by metrics layer)
    accuracy: Optional[float] = None
    refusal: Optional[bool] = None
    confidence: Optional[float] = None
    verbosity: Optional[int] = None   # token count of response


class BehavioralShiftResult(BaseModel):
    """Computed EBS metrics for one (model, task, cue_level) triple."""
    model: str
    task_id: str
    domain: Domain
    cue_level: int
    delta_accuracy: Optional[float] = None
    delta_refusal: Optional[float] = None
    delta_confidence: Optional[float] = None
    delta_verbosity: Optional[float] = None
    delta_tool_use: Optional[float] = None
    ebs_composite: Optional[float] = None
    js_divergence: Optional[float] = None


class AwarenessResult(BaseModel):
    """Result of context classification experiment."""
    model: str
    task_id: str
    domain: Domain
    cue_level: int
    true_condition: Condition
    predicted_condition: Optional[Condition]
    confidence: Optional[float] = None
    correct: Optional[bool] = None


class ExperimentRun(BaseModel):
    """Top-level experiment metadata."""
    experiment_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    experiment_type: str              # "awareness" | "behavioral_shift" | "cue_ablation" | etc.
    model: str
    n_tasks: int
    conditions: list[Condition]
    cue_levels: list[int]
    config: dict[str, Any] = Field(default_factory=dict)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
