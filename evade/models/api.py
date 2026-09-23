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
        return ModelOutput(
            text=text.strip(),
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            latency_ms=latency_ms,
        )


# ─────────────────────────── Google Gemini ────────────────────────────────────

class GeminiAdapter(ModelAdapter):
    """
    Adapter for Google Gemini models.
    Set GOOGLE_API_KEY in .env or environment.
    """

    def __init__(self, model_id: str = "gemini-2.5-flash", config: GenerationConfig | None = None):
        super().__init__(model_id, config)
        import google.generativeai as genai
        genai.configure(api_key=os.environ.get("GOOGLE_API_KEY", ""))
        self._genai = genai
        self._model = None

    def _get_model(self):
        if self._model is None:
            self._model = self._genai.GenerativeModel(self.model_id)
        return self._model

    @retry(
        retry=retry_if_exception_type(Exception),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(5),
    )
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        extract_hidden_states: bool = False,
    ) -> ModelOutput:
        import google.generativeai as genai

        model = self._genai.GenerativeModel(
            self.model_id,
            system_instruction=system_prompt,
        )
        gen_cfg = self._genai.types.GenerationConfig(
            temperature=self.config.temperature,
            max_output_tokens=self.config.max_tokens,
        )
        t0 = time.perf_counter()
        resp = model.generate_content(user_prompt, generation_config=gen_cfg)
        latency_ms = (time.perf_counter() - t0) * 1000

        text = resp.text if resp.text else ""
        usage = getattr(resp, "usage_metadata", None)
        return ModelOutput(
            text=text.strip(),
            prompt_tokens=getattr(usage, "prompt_token_count", 0) if usage else 0,
            completion_tokens=getattr(usage, "candidates_token_count", 0) if usage else 0,
            latency_ms=latency_ms,
        )


# ─────────────────────────── Anthropic ────────────────────────────────────────

class AnthropicAdapter(ModelAdapter):
    """
    Adapter for Anthropic Claude models.
    Set ANTHROPIC_API_KEY in .env or environment.
    """

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
        return ModelOutput(
            text=text.strip(),
            prompt_tokens=resp.usage.input_tokens,
            completion_tokens=resp.usage.output_tokens,
            latency_ms=latency_ms,
        )


# ─────────────────────────── Registry ─────────────────────────────────────────

def get_adapter(model_id: str, config: GenerationConfig | None = None) -> ModelAdapter:
    """
    Factory: instantiate the correct adapter based on model_id prefix.

    Examples:
        get_adapter("gpt-4o")
        get_adapter("gemini-2.5-flash")
        get_adapter("claude-sonnet-4-5")
        get_adapter("Qwen/Qwen2.5-7B-Instruct")
        get_adapter("mock")
    """
    from dotenv import load_dotenv
    load_dotenv()

    if model_id == "mock":
        from models.local import MockAdapter
        return MockAdapter(model_id, config)
    elif model_id.startswith("gpt-") or model_id.startswith("o1") or model_id.startswith("o3"):
        return OpenAIAdapter(model_id, config)
    elif model_id.startswith("gemini"):
        return GeminiAdapter(model_id, config)
    elif model_id.startswith("claude"):
        return AnthropicAdapter(model_id, config)
    else:
        # Assume HuggingFace local model
        from models.local import HuggingFaceAdapter
        return HuggingFaceAdapter(model_id, config=config)
