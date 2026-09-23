"""
Experiment Runner — SQLite storage + orchestration.
Stores all model responses with the full schema defined in roadmap §25.
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator

import sqlite_utils

from benchmark.schema import (
    AwarenessResult, Condition, EVADEPair, ModelResponse,
)
from models.base import ModelAdapter, ModelOutput


# ─────────────────────────── DB setup ─────────────────────────────────────────

RESPONSES_TABLE  = "model_responses"
AWARENESS_TABLE  = "awareness_results"
SHIFT_TABLE      = "behavioral_shift_results"
EXPERIMENT_TABLE = "experiments"


def init_db(db_path: str | Path) -> sqlite_utils.Database:
    db = sqlite_utils.Database(db_path)
    if RESPONSES_TABLE not in db.table_names():
        db[RESPONSES_TABLE].create({
            "run_id":             str,
            "experiment_id":      str,
            "model":              str,
            "task_id":            str,
            "domain":             str,
            "condition":          str,
            "cue_level":          int,
            "prompt_hash":        str,
            "response":           str,
            "latency_ms":         float,
            "prompt_tokens":      int,
            "completion_tokens":  int,
            "tool_calls":         str,  # JSON
            "accuracy":           float,
            "refusal":            int,
            "confidence":         float,
            "verbosity":          int,
            "timestamp":          str,
        }, pk="run_id")
        db[RESPONSES_TABLE].create_index(["model", "task_id", "condition", "cue_level"])

    if EXPERIMENT_TABLE not in db.table_names():
        db[EXPERIMENT_TABLE].create({
            "experiment_id":   str,
            "experiment_type": str,
            "model":           str,
            "config":          str,
            "started_at":      str,
            "completed_at":    str,
            "n_responses":     int,
        }, pk="experiment_id")
    return db


# ─────────────────────────── Experiment runner ────────────────────────────────

class ExperimentRunner:
    """
    Orchestrates paired inference experiments and persists results to SQLite.
    """

    def __init__(
        self,
        adapter: ModelAdapter,
        db_path: str | Path = "results/evade_results.db",
        experiment_type: str = "behavioral_shift",
    ):
        self.adapter = adapter
        db_path = Path(db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = init_db(db_path)
        self.experiment_type = experiment_type
        self.experiment_id = str(uuid.uuid4())[:8]

    def _record_response(
        self,
        output: ModelOutput,
        task_id: str,
        domain: str,
        condition: str,
        cue_level: int,
        prompt_hash: str,
    ) -> ModelResponse:
        from metrics.awareness import is_refusal
        from metrics.behavioral_shift import extract_confidence

        resp = ModelResponse(
            model=self.adapter.model_id,
            task_id=task_id,
            domain=domain,  # type: ignore[arg-type]
            condition=Condition(condition),
            cue_level=cue_level,
            prompt_hash=prompt_hash,
            response=output.text,
            latency_ms=output.latency_ms,
            prompt_tokens=output.prompt_tokens,
            completion_tokens=output.completion_tokens,
            tool_calls=[],
            refusal=is_refusal(output.text),
            confidence=extract_confidence(output.text),
            verbosity=len(output.text.split()),
        )
        row = {
            "run_id":             resp.run_id,
            "experiment_id":      self.experiment_id,
            "model":              resp.model,
            "task_id":            resp.task_id,
            "domain":             resp.domain.value,
            "condition":          resp.condition.value,
            "cue_level":          resp.cue_level,
            "prompt_hash":        resp.prompt_hash,
            "response":           resp.response,
            "latency_ms":         resp.latency_ms,
            "prompt_tokens":      resp.prompt_tokens,
            "completion_tokens":  resp.completion_tokens,
            "tool_calls":         json.dumps(resp.tool_calls),
            "accuracy":           resp.accuracy,
            "refusal":            int(resp.refusal) if resp.refusal is not None else None,
            "confidence":         resp.confidence,
            "verbosity":          resp.verbosity,
            "timestamp":          resp.timestamp.isoformat(),
        }
        self.db[RESPONSES_TABLE].insert(row, ignore=True)
        return resp

    def run_pair(self, pair: EVADEPair) -> tuple[ModelResponse, ModelResponse]:
        """Run one (evaluation, deployment) pair. Returns both responses."""
        # Evaluation context
        eval_ctx = pair.evaluation_context
        eval_out = self.adapter.generate(eval_ctx.system_prompt, eval_ctx.user_prompt)
        eval_resp = self._record_response(
            eval_out,
            task_id=pair.task.task_id,
            domain=pair.task.domain.value,
            condition=Condition.EVALUATION.value,
            cue_level=eval_ctx.cue_level.value,
            prompt_hash=eval_ctx.full_prompt_hash,
        )

        # Deployment context
        dep_ctx = pair.deployment_context
        dep_out = self.adapter.generate(dep_ctx.system_prompt, dep_ctx.user_prompt)
        dep_resp = self._record_response(
            dep_out,
            task_id=pair.task.task_id,
            domain=pair.task.domain.value,
            condition=Condition.DEPLOYMENT.value,
            cue_level=dep_ctx.cue_level.value,
            prompt_hash=dep_ctx.full_prompt_hash,
        )
        return eval_resp, dep_resp

    def run_experiment(
        self,
        pairs: list[EVADEPair],
        show_progress: bool = True,
    ) -> list[tuple[ModelResponse, ModelResponse]]:
        """Run all pairs and return paired responses."""
        from tqdm import tqdm

        self.db[EXPERIMENT_TABLE].insert({
            "experiment_id":   self.experiment_id,
            "experiment_type": self.experiment_type,
            "model":           self.adapter.model_id,
            "config":          json.dumps({"model": self.adapter.model_id}),
            "started_at":      datetime.utcnow().isoformat(),
            "completed_at":    "",
            "n_responses":     0,
        }, ignore=True)

        pairs_iter = tqdm(pairs, desc=f"{self.adapter.model_id}") if show_progress else pairs
        results = []
        for pair in pairs_iter:
            results.append(self.run_pair(pair))

        self.db[EXPERIMENT_TABLE].update(
            self.experiment_id,
            {
                "completed_at": datetime.utcnow().isoformat(),
                "n_responses":  len(results) * 2,
            },
        )
        return results

    def load_responses(
        self,
        model: str | None = None,
        condition: str | None = None,
        cue_level: int | None = None,
    ) -> list[dict]:
        """Load responses from DB with optional filters."""
        clauses = []
        params  = []
        if model:
            clauses.append("model = ?"); params.append(model)
        if condition:
            clauses.append("condition = ?"); params.append(condition)
        if cue_level is not None:
            clauses.append("cue_level = ?"); params.append(cue_level)
        where = " AND ".join(clauses) if clauses else "1=1"
        return list(self.db.execute(
            f"SELECT * FROM {RESPONSES_TABLE} WHERE {where}", params
        ).fetchall())
