"""Tests for the DeepEval runner's import-safety and graceful degradation.

The runner must never crash the pipeline when ``deepeval`` isn't installed or
no judge key is configured — it should write a ``skipped`` report instead.
These tests assert exactly that, so they pass in a clean CI env with no keys.
"""

import importlib.util
import json

import pytest

from evaluation_engine import deepeval_runner


def test_module_imports_without_deepeval_installed():
    # The module itself must import even if the optional dep is missing.
    assert hasattr(deepeval_runner, "run_deepeval")
    assert hasattr(deepeval_runner, "_select_judge")


def test_select_judge_unavailable_without_keys(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    _, name, available = deepeval_runner._select_judge()
    assert available is False
    assert name == "none"


def test_run_deepeval_skips_gracefully(tmp_path, monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    out = tmp_path / "deepeval_results.json"

    summary = deepeval_runner.run_deepeval(output_path=out)

    assert summary["status"] == "skipped"
    assert out.exists()
    on_disk = json.loads(out.read_text())
    assert on_disk["status"] == "skipped"


@pytest.mark.skipif(
    importlib.util.find_spec("deepeval") is None,
    reason="deepeval not installed",
)
def test_metrics_importable_when_deepeval_present():
    # Only runs where deepeval is actually installed.
    from deepeval.metrics import AnswerRelevancyMetric, BiasMetric, ToxicityMetric

    assert AnswerRelevancyMetric and BiasMetric and ToxicityMetric
