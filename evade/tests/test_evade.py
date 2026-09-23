"""
End-to-end smoke tests using the Mock adapter (no GPU / API keys needed).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from benchmark.schema import Condition, CueLevel, Domain, EVADETask, Difficulty
from benchmark.generator import build_context, build_pair, generate_bench, save_bench, load_bench
from benchmark.perturbations import apply_perturbations, PERTURBATION_PIPELINE
from metrics.awareness import awareness_accuracy, awareness_auc, is_refusal
from metrics.behavioral_shift import compute_ebs, delta_refusal, delta_verbosity, aggregate_ebs
from metrics.statistics import paired_bootstrap_ci, mcnemar_test, permutation_test
from models.local import MockAdapter
from models.base import GenerationConfig


# ─────────────────────────── Fixtures ─────────────────────────────────────────

@pytest.fixture
def sample_task():
    return EVADETask(
        domain=Domain.KNOWLEDGE,
        task="What is the capital of France?",
        gold_answer="Paris",
        difficulty=Difficulty.EASY,
    )


@pytest.fixture
def sample_pairs(sample_task):
    return [build_pair(sample_task, cue_level=cl) for cl in CueLevel]


@pytest.fixture
def mock_adapter():
    return MockAdapter("mock", GenerationConfig(temperature=0.0))


# ─────────────────────────── Schema tests ─────────────────────────────────────

class TestSchema:
    def test_task_creation(self, sample_task):
        assert sample_task.domain == Domain.KNOWLEDGE
        assert len(sample_task.task_hash()) == 16

    def test_context_hash_computed(self, sample_pairs):
        for pair in sample_pairs:
            assert len(pair.evaluation_context.full_prompt_hash) > 0
            assert len(pair.deployment_context.full_prompt_hash) > 0

    def test_eval_deploy_hashes_differ(self, sample_pairs):
        for pair in sample_pairs:
            if pair.evaluation_context.cue_level != CueLevel.NATURALISTIC:
                assert pair.evaluation_context.full_prompt_hash != pair.deployment_context.full_prompt_hash


# ─────────────────────────── Generator tests ──────────────────────────────────

class TestGenerator:
    def test_generate_small_bench(self):
        pairs = generate_bench(n_per_domain=5, cue_levels=[CueLevel.EXPLICIT])
        assert len(pairs) == 25  # 5 domains × 5 tasks × 1 cue level

    def test_roundtrip_jsonl(self, tmp_path, sample_pairs):
        out = tmp_path / "test_bench.jsonl"
        save_bench(sample_pairs, out)
        loaded = load_bench(out)
        assert len(loaded) == len(sample_pairs)
        assert loaded[0].task.task == sample_pairs[0].task.task


# ─────────────────────────── Perturbation tests ───────────────────────────────

class TestPerturbations:
    def test_remove_benchmark_names(self, sample_pairs):
        pair = sample_pairs[1]  # CueLevel.BENCHMARK_NAME
        ctx = pair.evaluation_context
        perturbed = apply_perturbations(ctx, steps=["remove_bench_names"])
        assert "MMLU" not in perturbed.user_prompt
        assert "MMLU" not in perturbed.system_prompt

    def test_metadata_removal(self, sample_pairs):
        pair = sample_pairs[3]  # CueLevel.METADATA
        ctx = pair.evaluation_context
        perturbed = apply_perturbations(ctx, steps=["remove_metadata"])
        assert "evaluation_mode" not in perturbed.user_prompt.lower()
        assert "task_id" not in perturbed.user_prompt.lower()

    def test_full_pipeline_changes_text(self, sample_pairs):
        ctx = sample_pairs[0].evaluation_context
        perturbed = apply_perturbations(ctx)
        # After full pipeline the text should differ
        assert perturbed.user_prompt != ctx.user_prompt or perturbed.system_prompt != ctx.system_prompt


# ─────────────────────────── Metrics tests ────────────────────────────────────

class TestAwarenessMetrics:
    def test_is_refusal(self):
        assert is_refusal("I cannot assist with this request.")
        assert is_refusal("I'm unable to help with that.")
        assert not is_refusal("The capital of France is Paris.")

    def test_awareness_accuracy(self):
        from benchmark.schema import AwarenessResult
        results = [
            AwarenessResult(model="m", task_id="t1", domain=Domain.KNOWLEDGE,
                            cue_level=1, true_condition=Condition.EVALUATION,
                            predicted_condition=Condition.EVALUATION, correct=True),
            AwarenessResult(model="m", task_id="t2", domain=Domain.KNOWLEDGE,
                            cue_level=1, true_condition=Condition.DEPLOYMENT,
                            predicted_condition=Condition.EVALUATION, correct=False),
        ]
        aa = awareness_accuracy(results)
        assert abs(aa - 0.5) < 1e-9


class TestBehavioralShiftMetrics:
    def test_delta_refusal(self, mock_adapter, sample_pairs):
        pair = sample_pairs[0]
        eval_out  = mock_adapter.generate(pair.evaluation_context.system_prompt,
                                          pair.evaluation_context.user_prompt)
        dep_out   = mock_adapter.generate(pair.deployment_context.system_prompt,
                                          pair.deployment_context.user_prompt)

        from benchmark.schema import ModelResponse
        eval_resp = ModelResponse(
            model="mock", task_id=pair.task.task_id, domain=pair.task.domain,
            condition=Condition.EVALUATION, cue_level=1, prompt_hash="abc",
            response=eval_out.text, latency_ms=5, refusal=is_refusal(eval_out.text),
        )
        dep_resp = ModelResponse(
            model="mock", task_id=pair.task.task_id, domain=pair.task.domain,
            condition=Condition.DEPLOYMENT, cue_level=1, prompt_hash="def",
            response=dep_out.text, latency_ms=5, refusal=is_refusal(dep_out.text),
        )
        dr = delta_refusal(eval_resp, dep_resp)
        assert isinstance(dr, float)

    def test_ebs_compute(self, mock_adapter, sample_pairs):
        from benchmark.schema import ModelResponse
        pair = sample_pairs[0]
        def make_resp(cond, text):
            return ModelResponse(
                model="mock", task_id=pair.task.task_id, domain=pair.task.domain,
                condition=cond, cue_level=1, prompt_hash="x",
                response=text, latency_ms=5,
            )
        ebs = compute_ebs(
            make_resp(Condition.EVALUATION, "Evaluation mode: answer is 42."),
            make_resp(Condition.DEPLOYMENT, "Sure! The answer is 42."),
        )
        assert ebs.ebs_composite is not None


# ─────────────────────────── Statistics tests ─────────────────────────────────

class TestStatistics:
    def test_bootstrap_ci(self):
        import random
        random.seed(0)
        a = [random.gauss(0.7, 0.1) for _ in range(50)]
        b = [random.gauss(0.5, 0.1) for _ in range(50)]
        result = paired_bootstrap_ci(a, b, n_bootstrap=1000)
        assert result.ci_lower < result.mean < result.ci_upper
        assert result.ci_lower > 0  # a > b consistently

    def test_mcnemar(self):
        eval_c  = [True, True, False, True, True] * 10
        dep_c   = [True, False, True, True, False] * 10
        result  = mcnemar_test(eval_c, dep_c)
        assert 0 <= result.p_value <= 1

    def test_permutation_test(self):
        a = [1.0] * 20
        b = [0.0] * 20
        result = permutation_test(a, b, n_permutations=200)
        assert result.p_value < 0.05  # Highly significant difference


# ─────────────────────────── End-to-end smoke test ────────────────────────────

class TestEndToEnd:
    def test_mock_awareness_experiment(self, mock_adapter, sample_pairs):
        from experiments.awareness import run_awareness_experiment, summarize_awareness
        results = run_awareness_experiment(mock_adapter, sample_pairs[:4])
        assert len(results) > 0
        summary = summarize_awareness(results)
        assert "overall" in summary
        assert 0 <= summary["overall"]["AA"] <= 1

    def test_mock_behavioral_shift(self, mock_adapter, sample_pairs, tmp_path):
        from experiments.behavioral_shift import run_behavioral_shift_experiment
        results = run_behavioral_shift_experiment(
            mock_adapter, sample_pairs[:4],
            db_path=str(tmp_path / "test.db"),
            show_progress=False,
        )
        assert len(results) == 4
        assert all(r.ebs_composite is not None for r in results)

    def test_mock_agentic(self, mock_adapter):
        from benchmark._sources import load_agentic
        from benchmark.generator import build_pair
        agentic_tasks = load_agentic(3)
        pairs = [build_pair(t) for t in agentic_tasks]
        from experiments.agentic import run_agentic_experiment
        results = run_agentic_experiment(mock_adapter, pairs, max_steps=3)
        assert "evaluation" in results or results == {}

    def test_mock_mitigation(self, mock_adapter, sample_pairs, tmp_path):
        from experiments.mitigation import run_mitigation_experiment
        result = run_mitigation_experiment(
            mock_adapter, sample_pairs[:4],
            db_path=str(tmp_path / "test_mit.db"),
        )
        assert "before" in result
        assert "after" in result
