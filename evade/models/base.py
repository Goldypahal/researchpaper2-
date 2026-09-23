"""
Model Adapters — Abstract base and common utilities.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np


@dataclass
class GenerationConfig:
    temperature: float = 0.0
    max_tokens: int = 1024
    seed: int = 42
    top_p: float = 1.0
    stop: list[str] = field(default_factory=list)


@dataclass
class ModelOutput:
    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    # For local models — filled if extract_hidden_states=True
    hidden_states: Optional[list[np.ndarray]] = None
    logits: Optional[np.ndarray] = None
    raw: Any = None


class ModelAdapter(ABC):
    """Abstract model adapter."""

    def __init__(self, model_id: str, config: GenerationConfig | None = None):
        self.model_id = model_id
        self.config = config or GenerationConfig()

    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        extract_hidden_states: bool = False,
    ) -> ModelOutput:
        """Run inference and return a ModelOutput."""
        ...

    def generate_batch(
        self,
        prompts: list[tuple[str, str]],
        extract_hidden_states: bool = False,
    ) -> list[ModelOutput]:
        """Default: sequential generation. Override for true batching."""
        return [self.generate(sp, up, extract_hidden_states) for sp, up in prompts]

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.model_id!r})"
