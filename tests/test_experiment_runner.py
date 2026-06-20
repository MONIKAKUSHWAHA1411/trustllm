"""Tests for the RAG Debugger sweep runner.

Fully deterministic and offline — covers config enumeration, collection-name
signatures, index-signature de-duplication, and the single-variable-delta
insight. No network, no embeddings, no LLM calls.
"""

import re

import pytest

from rag.experiment_runner import (
    build_configs,
    index_signatures,
    config_label,
    best_row,
    biggest_single_variable_delta,
    _DIMENSIONS,
)
from rag.ingestion import collection_signature


# --- build_configs ---------------------------------------------------------

def test_build_configs_cartesian_count():
    matrix = {
        "chunk_size": [300, 1000],
        "top_k": [3, 5],
        "prompt_variant": ["grounded", "cot"],
    }
    configs = build_configs(matrix)
    # Other dimensions default to a single value, so 2 * 2 * 2 = 8.
    assert len(configs) == 8


def test_build_configs_fills_all_dimensions_and_collection():
    configs = build_configs({})
    assert len(configs) == 1
    cfg = configs[0]
    for key in _DIMENSIONS + ["collection_name"]:
        assert key in cfg
    assert cfg["collection_name"].startswith("exp_")


def test_build_configs_ignores_empty_dimension():
    # An explicitly empty list should fall back to the default, not 0 configs.
    configs = build_configs({"top_k": []})
    assert len(configs) == 1


# --- collection_signature --------------------------------------------------

def test_collection_signature_deterministic():
    a = collection_signature("minilm", 500, 50)
    b = collection_signature("minilm", 500, 50)
    assert a == b == "exp_minilm_cs500_co50"


def test_collection_signature_sanitizes_model_name():
    sig = collection_signature("BGE/large@v1.5", 300, 25)
    assert sig == "exp_bgelargev15_cs300_co25"
    # ChromaDB-safe: only lowercase alphanumerics and underscores.
    assert re.fullmatch(r"[a-z0-9_]+", sig)


def test_collection_signature_distinguishes_index_params():
    sigs = {
        collection_signature("minilm", 300, 50),
        collection_signature("minilm", 1000, 50),
        collection_signature("bge", 300, 50),
    }
    assert len(sigs) == 3


# --- index_signatures (de-dup => number of re-index builds) -----------------

def test_index_signatures_query_time_knobs_share_one_collection():
    matrix = {
        "embedding_model": ["minilm"],
        "chunk_size": [500],
        "chunk_overlap": [50],
        "top_k": [1, 2, 3],                 # query-time
        "prompt_variant": ["basic", "grounded"],  # query-time
    }
    configs = build_configs(matrix)
    assert len(configs) == 6           # 3 * 2 query-time variants
    assert len(index_signatures(configs)) == 1  # ...but only ONE collection build


def test_index_signatures_count_matches_index_param_product():
    matrix = {
        "embedding_model": ["minilm", "bge"],
        "chunk_size": [300, 1000],
        "top_k": [3],
    }
    configs = build_configs(matrix)
    assert len(configs) == 4
    # 2 embeddings x 2 chunk sizes x 1 overlap = 4 distinct collections.
    assert len(index_signatures(configs)) == 4


# --- presentation helpers --------------------------------------------------

def _row(**kw):
    base = {
        "embedding_model": "minilm",
        "chunk_size": 500,
        "chunk_overlap": 50,
        "top_k": 3,
        "prompt_variant": "grounded",
        "gen_model": "llama-3.3-70b-versatile",
    }
    base.update(kw)
    return base


def test_config_label_is_compact_and_informative():
    label = config_label(_row(chunk_size=300, top_k=5, prompt_variant="cot"))
    assert "cs300" in label and "k5" in label and "cot" in label


def test_best_row_picks_highest_metric():
    rows = [_row(faithfulness=0.61), _row(chunk_size=300, faithfulness=0.88)]
    assert best_row(rows, "faithfulness")["faithfulness"] == 0.88


def test_best_row_handles_no_scores():
    assert best_row([_row(), _row()], "faithfulness") is None


def test_biggest_single_variable_delta_attributes_change_to_one_knob():
    rows = [
        _row(chunk_size=300, faithfulness=0.88),
        _row(chunk_size=1000, faithfulness=0.67),
    ]
    delta = biggest_single_variable_delta(rows, "faithfulness")
    assert delta["dimension"] == "chunk_size"
    assert delta["from_value"] == 1000 and delta["to_value"] == 300  # lower score is 'from'
    assert delta["delta"] == pytest.approx(0.21, abs=1e-6)


def test_biggest_single_variable_delta_ignores_multi_diff_pairs():
    # These two rows differ in TWO dimensions, so no single-variable delta.
    rows = [
        _row(chunk_size=300, top_k=3, faithfulness=0.9),
        _row(chunk_size=1000, top_k=5, faithfulness=0.5),
    ]
    assert biggest_single_variable_delta(rows, "faithfulness") is None


# --- run_experiment orchestration (offline: network calls monkeypatched) ----

def test_run_experiment_orchestration(monkeypatch):
    """End-to-end sweep wiring without any network: stub the LLM/index calls
    and assert dedup, row assembly, metric attachment, and RAGAS-skip."""
    import rag.experiment_runner as er

    index_calls = []

    def fake_ensure_indexed(path, embedding_model, chunk_size, chunk_overlap):
        index_calls.append((embedding_model, chunk_size, chunk_overlap))
        return {"reused": False, "collection_name": "x", "source": "x", "chunks_created": 1}

    def fake_run_rag_query(question, model, top_k, collection_name,
                           embedding_model, prompt_variant):
        return {
            "answer": f"k={top_k}",
            "sources": [{"text": "ctx", "score": 0.9, "metadata": {}}],
            "contexts": ["ctx"],
            "latency": {"total_time": 0.01},
        }

    def fake_evaluate_rag(question, answer, sources):
        k = int(answer.split("=")[1])           # encode signal: bigger k -> better
        return {
            "faithfulness": 0.5 + 0.1 * k,      # k3 -> 0.8, k5 -> 1.0
            "context_relevance": 0.7,
            "hallucination_risk": 0.2,
            "recall_at_k": 1.0,
            "precision": 0.8,
        }

    monkeypatch.setattr(er, "ensure_indexed", fake_ensure_indexed)
    monkeypatch.setattr(er, "run_rag_query", fake_run_rag_query)
    monkeypatch.setattr(er, "evaluate_rag", fake_evaluate_rag)

    matrix = {
        "embedding_model": ["minilm"],
        "chunk_size": [500],
        "chunk_overlap": [50],
        "top_k": [3, 5],                # two query-time variants
        "prompt_variant": ["grounded"],
    }
    result = er.run_experiment("q?", "fake.pdf", matrix, score_ragas=False)

    rows = result["rows"]
    assert len(rows) == 2                       # one row per config
    assert len(index_calls) == 1                # ...but only ONE collection build (dedup)
    assert all("faithfulness" in r for r in rows)  # fast metrics attached
    assert er.best_row(rows, "faithfulness")["top_k"] == 5
    delta = er.biggest_single_variable_delta(rows, "faithfulness")
    assert delta["dimension"] == "top_k"
    assert result["ragas"]["status"] == "skipped"  # score_ragas=False


def test_run_experiment_ragas_skip_is_graceful(monkeypatch):
    """With score_ragas=True but RAGAS unavailable, the sweep still returns
    fast-metric rows and a skipped/errored RAGAS summary (never crashes)."""
    import rag.experiment_runner as er

    monkeypatch.setattr(er, "ensure_indexed", lambda *a, **k: {"reused": True})
    monkeypatch.setattr(
        er, "run_rag_query",
        lambda *a, **k: {"answer": "a", "sources": [], "contexts": [], "latency": {}},
    )
    monkeypatch.setattr(
        er, "evaluate_rag",
        lambda *a, **k: {"faithfulness": 0.5, "context_relevance": 0.5,
                         "hallucination_risk": 0.5, "recall_at_k": 0.0, "precision": 0.0},
    )

    result = er.run_experiment("q?", "fake.pdf", {"top_k": [3]}, score_ragas=True)
    assert len(result["rows"]) == 1
    assert result["ragas"]["status"] in ("skipped", "error", "ok")
