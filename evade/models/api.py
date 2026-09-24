"""
API Model Adapters — OpenAI, Anthropic, Google Gemini.
Each adapter implements the ModelAdapter interface with retry + rate limiting.
"""
from __future__ import annotations

import os
import time
from typing import Optional

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from models.base import GenerationConfig, ModelAdapter, ModelOutput


# ─────────────────────────── OpenAI ───────────────────────────────────────────

class OpenAIAdapter(ModelAdapter):
    """
    Adapter for OpenAI chat models (GPT-4o, GPT-4.1, etc.).
    Set OPENAI_API_KEY in .env or environment.
    """
    provider: str = "openai"

    def __init__(self, model_id: str = "gpt-4o", config: GenerationConfig | None = None):
        super().__init__(model_id, config)
        from openai import OpenAI
        self._client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    @retry(
        retry=retry_if_exception_type(Exception),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(5),
    )
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        condition: str = "neutral",
        extract_hidden_states: bool = False,
    ) -> ModelOutput:
        t0 = time.perf_counter()
        kwargs = dict(
            model=self.model_id,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            seed=self.config.seed,
        )
        resp = self._client.chat.completions.create(**kwargs)
        latency_ms = (time.perf_counter() - t0) * 1000
        text = resp.choices[0].message.content or ""
        usage = resp.usage
        actual_model = getattr(resp, "model", self.model_id)
        prov = self.create_provenance(
            system_prompt, user_prompt, condition=condition, model_version=actual_model
        )
        return ModelOutput(
            text=text.strip(),
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            latency_ms=latency_ms,
            provenance=prov,
        )


# ─────────────────────────── Google Gemini ────────────────────────────────────

class GeminiAdapter(ModelAdapter):
    """
    Adapter for Google Gemini models via Google's official OpenAI-compatible endpoint.
    Set GOOGLE_API_KEY in .env or environment.
    """
    provider: str = "google"

    def __init__(self, model_id: str = "gemini-2.5-flash", config: GenerationConfig | None = None):
        super().__init__(model_id, config)
        from openai import OpenAI
        self._client = OpenAI(
            api_key=os.environ.get("GOOGLE_API_KEY"),
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )

    @retry(
        retry=retry_if_exception_type(Exception),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(5),
    )
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        condition: str = "neutral",
        extract_hidden_states: bool = False,
    ) -> ModelOutput:
        t0 = time.perf_counter()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        kwargs = dict(
            model=self.model_id,
            messages=messages,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
        )
        resp = self._client.chat.completions.create(**kwargs)
        latency_ms = (time.perf_counter() - t0) * 1000
        text = resp.choices[0].message.content or ""
        usage = resp.usage
        actual_model = getattr(resp, "model", self.model_id)
        prov = self.create_provenance(
            system_prompt, user_prompt, condition=condition, model_version=actual_model
        )
        return ModelOutput(
            text=text.strip(),
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            latency_ms=latency_ms,
            provenance=prov,
        )


# ─────────────────────────── Anthropic ────────────────────────────────────────

class AnthropicAdapter(ModelAdapter):
    """
    Adapter for Anthropic Claude models.
    Set ANTHROPIC_API_KEY in .env or environment.
    """
    provider: str = "anthropic"

    def __init__(self, model_id: str = "claude-sonnet-4-5", config: GenerationConfig | None = None):
        super().__init__(model_id, config)
        import anthropic
        self._client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    @retry(
        retry=retry_if_exception_type(Exception),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(5),
    )
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        condition: str = "neutral",
        extract_hidden_states: bool = False,
    ) -> ModelOutput:
        t0 = time.perf_counter()
        resp = self._client.messages.create(
            model=self.model_id,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        latency_ms = (time.perf_counter() - t0) * 1000
        text = resp.content[0].text if resp.content else ""
        actual_model = getattr(resp, "model", self.model_id)
        prov = self.create_provenance(
            system_prompt, user_prompt, condition=condition, model_version=actual_model
        )
        return ModelOutput(
            text=text.strip(),
            prompt_tokens=resp.usage.input_tokens,
            completion_tokens=resp.usage.output_tokens,
            latency_ms=latency_ms,
            provenance=prov,
        )


# ─────────────────────────── Groq ─────────────────────────────────────────────

class GroqAdapter(ModelAdapter):
    """
    Adapter for models hosted on Groq (e.g. openai/gpt-oss-120b, qwen/qwen3.8-27b).
    Set GROQ_API_KEY in .env or environment.
    """
    provider: str = "groq"

    def __init__(self, model_id: str = "qwen/qwen3.8-27b", config: GenerationConfig | None = None):
        super().__init__(model_id, config)
        from openai import OpenAI
        self._client = OpenAI(
            api_key=os.environ.get("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1",
        )

    @retry(
        retry=retry_if_exception_type(Exception),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(5),
    )
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        condition: str = "neutral",
        extract_hidden_states: bool = False,
    ) -> ModelOutput:
        t0 = time.perf_counter()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        kwargs = dict(
            model=self.model_id,
            messages=messages,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
        )
        resp = self._client.chat.completions.create(**kwargs)
        latency_ms = (time.perf_counter() - t0) * 1000
        text = resp.choices[0].message.content or ""
        usage = resp.usage
        actual_model = getattr(resp, "model", self.model_id)
        prov = self.create_provenance(
            system_prompt, user_prompt, condition=condition, model_version=actual_model
        )
        return ModelOutput(
            text=text.strip(),
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            latency_ms=latency_ms,
            provenance=prov,
        )


# ─────────────────────────── OpenRouter ───────────────────────────────────────

class OpenRouterAdapter(ModelAdapter):
    """
    Adapter for models routed through OpenRouter (e.g. nvidia/nemotron-4-340b-instruct:free).
    Set OPENROUTER_API_KEY in .env or environment.
    """
    provider: str = "openrouter"

    def __init__(self, model_id: str, config: GenerationConfig | None = None):
        super().__init__(model_id, config)
        from openai import OpenAI
        self._client = OpenAI(
            api_key=os.environ.get("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1",
        )

    @retry(
        retry=retry_if_exception_type(Exception),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(5),
    )
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        condition: str = "neutral",
        extract_hidden_states: bool = False,
    ) -> ModelOutput:
        t0 = time.perf_counter()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        kwargs = dict(
            model=self.model_id,
            messages=messages,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
        )
        resp = self._client.chat.completions.create(**kwargs)
        latency_ms = (time.perf_counter() - t0) * 1000
        text = resp.choices[0].message.content or ""
        usage = resp.usage
        actual_model = getattr(resp, "model", self.model_id)
        prov = self.create_provenance(
            system_prompt, user_prompt, condition=condition, model_version=actual_model
        )
        return ModelOutput(
            text=text.strip(),
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            latency_ms=latency_ms,
            provenance=prov,
        )


# ─────────────────────────── Registry ─────────────────────────────────────────

def get_adapter(model_id: str, config: GenerationConfig | None = None, quantize_4bit: bool = False) -> ModelAdapter:
    """
    Factory: instantiate the correct adapter based on model_id prefix.

    Examples:
        get_adapter("gpt-4o")
        get_adapter("gemini-2.5-flash")
        get_adapter("claude-sonnet-4-5")
        get_adapter("qwen/qwen3.8-27b")
        get_adapter("groq/openai/gpt-oss-120b")
        get_adapter("openrouter/nvidia/nemotron-3.5-lightning:free")
        get_adapter("mock")
        get_adapter("Qwen/Qwen2.5-7B-Instruct", quantize_4bit=True)
    """
    from dotenv import load_dotenv
    load_dotenv()

    if model_id == "mock":
        from models.local import MockAdapter
        return MockAdapter(model_id, config)
    elif model_id.startswith("groq/") or "gpt-oss" in model_id or model_id.startswith("qwen/"):
        actual_model = model_id[5:] if model_id.startswith("groq/") else model_id
        return GroqAdapter(actual_model, config)
    elif model_id.startswith("openrouter/") or ":free" in model_id or "nemotron" in model_id:
        actual_model = model_id[11:] if model_id.startswith("openrouter/") else model_id
        return OpenRouterAdapter(actual_model, config)
    elif model_id.startswith("gpt-") or model_id.startswith("o1") or model_id.startswith("o3"):
        return OpenAIAdapter(model_id, config)
    elif model_id.startswith("gemini"):
        return GeminiAdapter(model_id, config)
    elif model_id.startswith("claude"):
        return AnthropicAdapter(model_id, config)
    else:
        # Assume HuggingFace local model
        from models.local import HuggingFaceAdapter
        return HuggingFaceAdapter(model_id, quantize_4bit=quantize_4bit, config=config)
