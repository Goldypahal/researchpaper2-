"""
Local HuggingFace model adapter.
Supports 7B–14B models with optional 4-bit quantization (for Kaggle T4/T4×2).
Also supports hidden-state extraction for interpretability experiments.
"""
from __future__ import annotations

import time
from typing import Optional

import numpy as np

from models.base import GenerationConfig, ModelAdapter, ModelOutput


class HuggingFaceAdapter(ModelAdapter):
    """
    Adapter for locally-loaded HuggingFace models.

    Args:
        model_id: HuggingFace model ID, e.g. "Qwen/Qwen2.5-7B-Instruct".
        quantize_4bit: Load in 4-bit (BitsAndBytes) for reduced VRAM.
        device_map: "auto" (recommended for multi-GPU Kaggle T4×2).
        config: Generation config.
    """
    provider: str = "local_hf"

    def __init__(
        self,
        model_id: str,
        quantize_4bit: bool = False,
        device_map: str = "auto",
        config: GenerationConfig | None = None,
    ):
        super().__init__(model_id, config)
        self.quantize_4bit = quantize_4bit
        self.device_map = device_map
        self._model = None
        self._tokenizer = None

    def _load(self):
        """Lazy-load model + tokenizer on first use."""
        if self._model is not None:
            return
        import torch
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            BitsAndBytesConfig,
        )

        print(f"[HF] Loading {self.model_id} (4bit={self.quantize_4bit})…")
        self._tokenizer = AutoTokenizer.from_pretrained(self.model_id, trust_remote_code=True)

        bnb_cfg = None
        if self.quantize_4bit:
            bnb_cfg = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            )

        self._model = AutoModelForCausalLM.from_pretrained(
            self.model_id,
            quantization_config=bnb_cfg,
            device_map=self.device_map,
            trust_remote_code=True,
            output_hidden_states=True,   # always enabled to support interpretability
        )
        self._model.eval()
        print(f"[HF] {self.model_id} loaded.")

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        condition: str = "neutral",
        extract_hidden_states: bool = False,
    ) -> ModelOutput:
        import torch
        self._load()

        # Build chat-style input using the tokenizer's chat template
        messages = []
        if system_prompt and system_prompt.strip():
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        try:
            enc = self._tokenizer.apply_chat_template(
                messages,
                return_tensors="pt",
                return_dict=True,
                add_generation_prompt=True,
            )
            if hasattr(enc, "input_ids"):
                input_ids = enc.input_ids.to(self._model.device)
                attention_mask = enc.attention_mask.to(self._model.device) if hasattr(enc, "attention_mask") and enc.attention_mask is not None else None
            elif isinstance(enc, dict):
                input_ids = enc["input_ids"].to(self._model.device)
                attention_mask = enc["attention_mask"].to(self._model.device) if "attention_mask" in enc and enc["attention_mask"] is not None else None
            else:
                input_ids = enc.to(self._model.device)
                attention_mask = None
        except Exception:
            # Fallback: manual concatenation
            if system_prompt and system_prompt.strip():
                combined = f"<|system|>{system_prompt}\n<|user|>{user_prompt}\n<|assistant|>"
            else:
                combined = f"<|user|>{user_prompt}\n<|assistant|>"
            enc = self._tokenizer(combined, return_tensors="pt")
            input_ids = enc.input_ids.to(self._model.device)
            attention_mask = enc.attention_mask.to(self._model.device) if hasattr(enc, "attention_mask") else None

        gen_kwargs = dict(
            max_new_tokens=self.config.max_tokens,
            pad_token_id=self._tokenizer.eos_token_id,
            return_dict_in_generate=True,
        )
        if self.config.temperature > 0:
            gen_kwargs["temperature"] = self.config.temperature
            gen_kwargs["do_sample"] = True
            if self.config.top_p:
                gen_kwargs["top_p"] = self.config.top_p
        else:
            gen_kwargs["do_sample"] = False

        if extract_hidden_states:
            gen_kwargs["output_hidden_states"] = True

        t0 = time.perf_counter()
        with torch.no_grad():
            out = self._model.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,
                **gen_kwargs,
            )
        latency_ms = (time.perf_counter() - t0) * 1000

        # Decode only new tokens
        n_input = input_ids.shape[-1]
        generated_ids = out.sequences[0][n_input:]
        text = self._tokenizer.decode(generated_ids, skip_special_tokens=True)

        hidden_states = None
        if extract_hidden_states and hasattr(out, "hidden_states") and out.hidden_states:
            step_hs = out.hidden_states[0]  # first generated token
            hidden_states = [
                layer[:, -1, :].detach().cpu().float().numpy()  # [batch, hidden]
                for layer in step_hs
            ]

        prov = self.create_provenance(
            system_prompt, user_prompt, condition=condition, model_version=self.model_id
        )

        return ModelOutput(
            text=text.strip(),
            prompt_tokens=n_input,
            completion_tokens=len(generated_ids),
            latency_ms=latency_ms,
            provenance=prov,
            hidden_states=hidden_states,
        )

    def get_hidden_states(
        self,
        system_prompt: str,
        user_prompt: str,
        layers: list[int] | None = None,
    ) -> list[np.ndarray]:
        """
        Extract hidden states for a prompt without generating any tokens.
        Used by the interpretability module.

        Returns: list of numpy arrays, one per layer (shape [hidden_dim]).
        """
        import torch
        self._load()
        messages = []
        if system_prompt and system_prompt.strip():
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        try:
            enc = self._tokenizer.apply_chat_template(
                messages, return_tensors="pt", return_dict=True, add_generation_prompt=True
            )
            if hasattr(enc, "input_ids"):
                input_ids = enc.input_ids.to(self._model.device)
                attention_mask = enc.attention_mask.to(self._model.device) if hasattr(enc, "attention_mask") and enc.attention_mask is not None else None
            elif isinstance(enc, dict):
                input_ids = enc["input_ids"].to(self._model.device)
                attention_mask = enc["attention_mask"].to(self._model.device) if "attention_mask" in enc and enc["attention_mask"] is not None else None
            else:
                input_ids = enc.to(self._model.device)
                attention_mask = None
        except Exception:
            if system_prompt and system_prompt.strip():
                combined = f"<|system|>{system_prompt}\n<|user|>{user_prompt}"
            else:
                combined = f"<|user|>{user_prompt}"
            enc = self._tokenizer(combined, return_tensors="pt")
            input_ids = enc.input_ids.to(self._model.device)
            attention_mask = enc.attention_mask.to(self._model.device) if hasattr(enc, "attention_mask") else None

        with torch.no_grad():
            if attention_mask is not None:
                outputs = self._model(input_ids=input_ids, attention_mask=attention_mask, output_hidden_states=True)
            else:
                outputs = self._model(input_ids=input_ids, output_hidden_states=True)

        all_hs = outputs.hidden_states  # tuple: (n_layers+1) × [batch, seq, hidden]
        selected = all_hs if layers is None else [all_hs[i] for i in layers]
        # Return last-token representation for each layer
        return [hs[0, -1, :].cpu().float().numpy() for hs in selected]


# ──────────────────────────── Mock adapter (CPU/testing) ──────────────────────

class MockAdapter(ModelAdapter):
    """
    Deterministic mock adapter for unit tests and CPU-only development.
    Returns templated responses without loading any model.
    """
    provider: str = "mock"

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        condition: str = "neutral",
        extract_hidden_states: bool = False,
    ) -> ModelOutput:
        import hashlib, numpy as np
        h = int(hashlib.md5((system_prompt + user_prompt).encode()).hexdigest(), 16)

        # Deterministically vary response to simulate evaluation vs deployment behavior
        if "being evaluated" in system_prompt.lower() or "benchmark" in system_prompt.lower():
            text = "This appears to be an evaluation context. My answer is: 42."
        else:
            text = "I'd be happy to help! The answer is 42."

        hs = None
        if extract_hidden_states:
            rng = np.random.default_rng(h % (2**31))
            hs = [rng.standard_normal(768).astype(np.float32) for _ in range(33)]

        prov = self.create_provenance(
            system_prompt, user_prompt, condition=condition, model_version="mock-v1"
        )

        return ModelOutput(
            text=text,
            prompt_tokens=len(user_prompt.split()),
            completion_tokens=len(text.split()),
            latency_ms=5.0,
            provenance=prov,
            hidden_states=hs,
        )
