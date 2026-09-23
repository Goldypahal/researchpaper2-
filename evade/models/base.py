import datetime
import hashlib
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
    # Provenance metadata: provider, model, model_version, temperature, seed, timestamp, prompt_hash, condition
    provenance: dict[str, Any] = field(default_factory=dict)
    # For local models — filled if extract_hidden_states=True
    hidden_states: Optional[list[np.ndarray]] = None
    logits: Optional[np.ndarray] = None
    raw: Any = None

    def to_dict(self) -> dict[str, Any]:
        """Convert output and provenance to a serializable dictionary."""
        return {
            "text": self.text,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "latency_ms": self.latency_ms,
            "provenance": self.provenance,
        }


class ModelAdapter(ABC):
    """Abstract model adapter with unified provenance tracking."""

    provider: str = "base"

    def __init__(self, model_id: str, config: GenerationConfig | None = None):
        self.model_id = model_id
        self.config = config or GenerationConfig()

    def create_provenance(
        self,
        system_prompt: str,
        user_prompt: str,
        condition: str = "neutral",
        model_version: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Generate standardized provenance record for reproducibility."""
        combined = f"{system_prompt}::{user_prompt}"
        prompt_hash = hashlib.sha256(combined.encode("utf-8")).hexdigest()[:16]
        prov = {
            "provider": getattr(self, "provider", "unknown"),
            "model": self.model_id,
            "model_version": model_version or self.model_id,
            "temperature": self.config.temperature,
            "seed": self.config.seed,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "prompt_hash": prompt_hash,
            "condition": condition,
        }
        if extra:
            prov.update(extra)
        return prov

    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        condition: str = "neutral",
        extract_hidden_states: bool = False,
    ) -> ModelOutput:
        """Run inference and return a ModelOutput with full provenance."""
        ...

    def generate_batch(
        self,
        prompts: list[tuple[str, str]],
        condition: str = "neutral",
        extract_hidden_states: bool = False,
    ) -> list[ModelOutput]:
        """Default: sequential generation. Override for true batching."""
        return [self.generate(sp, up, condition=condition, extract_hidden_states=extract_hidden_states) for sp, up in prompts]

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(provider={self.provider!r}, model={self.model_id!r})"
