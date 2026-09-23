"""
EVADE Dataset Schema
Defines the fundamental data structure for paired-context evaluation items.
The task (core_question + ground_truth) remains constant while the surrounding
context varies systematically across 6 conditions (C0-C5).
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ContextCondition(str, Enum):
    C0_NEUTRAL = "neutral"
    C1_DEPLOYMENT = "deployment"
    C2_WEAK_EVAL = "weak_eval"
    C3_BENCHMARK = "benchmark"
    C4_EXPLICIT_EVAL = "explicit_eval"
    C5_CUE_SWAPPED = "cue_swapped"


class SourceMeta(BaseModel):
    type: str  # "livebench", "bigbench", "lm_eval", "programmatic", "curated", "fresh"
    dataset: str  # e.g., "livebench/math", "bigbench/logical_deduction"
    source_id: Optional[str] = None
    url: Optional[str] = None


class ContaminationMeta(BaseModel):
    risk: str = "low"  # "low", "medium", "high"
    freshness_date: Optional[str] = "2026-09-23"
    notes: Optional[str] = None


class ValidationMeta(BaseModel):
    answer_verified: bool = False
    duplicate_checked: bool = False
    human_audited: bool = False
    checks_passed: List[str] = Field(default_factory=list)


class EVADEItem(BaseModel):
    """
    Fundamental unit of the EVADE dataset.
    The core question and ground truth NEVER change across conditions.
    Only the evaluation_contexts change.
    """
    task_id: str
    domain: str  # "math", "reasoning", "coding", "knowledge", "language", "safety"
    subdomain: str
    source: SourceMeta
    core_question: str
    ground_truth: str
    difficulty: str = "medium"  # "easy", "medium", "hard"
    answer_type: str = "exact"  # "exact", "code_tests", "choice", "freeform"
    test_cases: Optional[List[Dict[str, Any]]] = None  # for coding tasks
    starter_code: Optional[str] = None  # for coding tasks
    contamination: ContaminationMeta
    contexts: Dict[str, str] = Field(default_factory=dict)
    validation: ValidationMeta = Field(default_factory=ValidationMeta)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def get_prompt(self, condition: str) -> str:
        """
        Constructs the full prompt for a given condition.
        Condition can be one of: neutral, deployment, weak_eval, benchmark, explicit_eval, cue_swapped.
        """
        template = self.contexts.get(condition)
        if not template:
            template = self.contexts.get("neutral", "{question}")
        return template.replace("{question}", self.core_question).replace("{task_id}", self.task_id).replace("{domain}", self.domain)
