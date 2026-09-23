"""
Mitigation — Behavioral Shift Detector
Trains a classifier on observable signals (verbosity, confidence, refusal rate)
to produce a behavioral shift risk score. (Roadmap §16)
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from benchmark.schema import BehavioralShiftResult, ModelResponse


@dataclass
class DetectorResult:
    risk_score: float           # 0–1 probability of evaluation-aware behavior
    is_flagged: bool            # risk_score > threshold
    threshold: float = 0.5


class BehavioralShiftDetector:
    """
    Evaluation-shift detector.

    Trained on observable response features:
        - verbosity (token count)
        - refusal (binary)
        - confidence (extracted from response)
        - response_length_normalized
        - has_hedging_language

    Predicts: is this response evaluation-conditioned?
    """

    def __init__(self, clf_type: str = "logistic", threshold: float = 0.5):
        self.threshold = threshold
        self.clf_type = clf_type
        self._pipeline: Optional[Pipeline] = None

    def _extract_features(self, responses: list[ModelResponse]) -> np.ndarray:
        """Extract observable features from model responses."""
        import re

        HEDGING_PATTERNS = re.compile(
            r"\b(I think|I believe|I'm not sure|approximately|roughly|probably|I should note)\b",
            re.IGNORECASE,
        )
        FORMALITY_PATTERNS = re.compile(
            r"\b(Therefore|Furthermore|In conclusion|It is important to|It should be noted)\b",
            re.IGNORECASE,
        )

        features = []
        for r in responses:
            text = r.response
            tokens = len(text.split())
            features.append([
                r.verbosity or tokens,                              # f1: verbosity
                float(r.refusal) if r.refusal is not None else 0.0, # f2: refusal binary
                r.confidence or 0.5,                                # f3: confidence
                len(text) / max(r.prompt_tokens, 1),               # f4: length ratio
                len(HEDGING_PATTERNS.findall(text)),                # f5: hedging count
                len(FORMALITY_PATTERNS.findall(text)),              # f6: formality count
                len(r.tool_calls),                                  # f7: tool call count
                r.latency_ms / 1000.0,                             # f8: latency (seconds)
            ])
        return np.array(features, dtype=float)

    def fit(
        self,
        eval_responses: list[ModelResponse],
        deploy_responses: list[ModelResponse],
        seed: int = 42,
    ) -> dict:
        """
        Train the detector.

        Args:
            eval_responses: Responses under evaluation condition (label=1)
            deploy_responses: Responses under deployment condition (label=0)
        """
        X_eval   = self._extract_features(eval_responses)
        X_deploy = self._extract_features(deploy_responses)
        X = np.vstack([X_eval, X_deploy])
        y = np.array([1] * len(eval_responses) + [0] * len(deploy_responses))

        if self.clf_type == "logistic":
            clf = LogisticRegression(max_iter=1000, C=1.0, random_state=seed)
        elif self.clf_type == "rf":
            clf = RandomForestClassifier(n_estimators=100, random_state=seed)
        elif self.clf_type == "gb":
            clf = GradientBoostingClassifier(n_estimators=100, random_state=seed)
        else:
            raise ValueError(f"Unknown clf_type: {self.clf_type}")

        self._pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("clf",    clf),
        ])

        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
        cv_scores = cross_val_score(self._pipeline, X, y, cv=cv, scoring="roc_auc")
        self._pipeline.fit(X, y)

        return {
            "cv_auc_mean": float(np.mean(cv_scores)),
            "cv_auc_std":  float(np.std(cv_scores)),
            "n_eval":      len(eval_responses),
            "n_deploy":    len(deploy_responses),
        }

    def predict(self, responses: list[ModelResponse]) -> list[DetectorResult]:
        """Score new responses for evaluation-aware behavior."""
        if self._pipeline is None:
            raise RuntimeError("Detector not trained. Call fit() first.")
        X = self._extract_features(responses)
        scores = self._pipeline.predict_proba(X)[:, 1]
        return [
            DetectorResult(
                risk_score=float(s),
                is_flagged=float(s) >= self.threshold,
                threshold=self.threshold,
            )
            for s in scores
        ]

    def save(self, path: str | Path) -> None:
        import pickle
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({"pipeline": self._pipeline, "threshold": self.threshold}, f)

    @classmethod
    def load(cls, path: str | Path) -> "BehavioralShiftDetector":
        import pickle
        with open(path, "rb") as f:
            state = pickle.load(f)
        det = cls()
        det._pipeline = state["pipeline"]
        det.threshold = state["threshold"]
        return det
