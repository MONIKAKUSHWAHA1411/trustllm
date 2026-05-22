"""
Agent Evaluation Module — TrustLLM
====================================
Evaluates an AI agent's tool-selection accuracy + response quality against a
labelled test dataset. All metrics are measured (no random fallbacks):

    tool_accuracy       — fraction of test cases where the agent picked
                          the expected tool (exact match)
    avg_reasoning       — mean cosine similarity between each query and its
                          agent response embedding (how well the chosen
                          response aligns with the query intent)
    avg_groundedness    — fraction of responses scored "Grounded" by the
                          hallucination detector (1.0 = grounded, 0.5 =
                          possible hallucination, 0.0 = likely)

No external services beyond local ONNX embeddings are required.
"""

import json
import sys
from pathlib import Path

import numpy as np

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))


_HALLUC_TO_SCORE = {
    "Grounded": 1.0,
    "Possible Hallucination": 0.5,
    "Likely Hallucination": 0.0,
}


def _cosine(a, b) -> float:
    """Cosine similarity between two embedding vectors, clamped to [0, 1]."""
    va = np.asarray(a, dtype=np.float32)
    vb = np.asarray(b, dtype=np.float32)
    na, nb = np.linalg.norm(va), np.linalg.norm(vb)
    if na == 0 or nb == 0:
        return 0.0
    sim = float(np.dot(va, vb) / (na * nb))
    return max(0.0, min(1.0, sim))


def evaluate_agent(agent, dataset_path: str) -> dict:
    """Evaluate agent on a labelled test dataset.

    Parameters
    ----------
    agent        : object with a ``run(query: str) -> dict`` method.
                   The dict must contain ``tool_used`` and ``response``.
    dataset_path : path to JSON list of {"query": str, "expected_tool": str}.

    Returns
    -------
    dict with keys:
        tool_accuracy, avg_reasoning, avg_groundedness,
        total_tests, passed_tests, results
    """
    dataset_path = Path(dataset_path)
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    with open(dataset_path) as f:
        test_cases = json.load(f)

    if not test_cases:
        return {
            "tool_accuracy": 0.0,
            "avg_reasoning": 0.0,
            "avg_groundedness": 0.0,
            "total_tests": 0,
            "passed_tests": 0,
            "results": [],
        }

    # Run the agent on every case first so we can batch-embed below.
    raw = []
    for case in test_cases:
        out = agent.run(case["query"])
        raw.append({
            "query": case["query"],
            "expected_tool": case["expected_tool"],
            "tool_used": out.get("tool_used", "unknown"),
            "response": out.get("response", ""),
        })

    # Batch-embed [query, response] pairs in one call for speed.
    from rag.embeddings import embed_texts
    from evaluation_engine.hallucination_detector import detect_hallucination_regex

    texts = []
    for r in raw:
        texts.append(r["query"])
        texts.append(r["response"])
    vecs = embed_texts(texts)

    results = []
    passed = 0
    for i, r in enumerate(raw):
        q_vec = vecs[2 * i]
        r_vec = vecs[2 * i + 1]

        reasoning_score = round(_cosine(q_vec, r_vec), 3)
        halluc_label = detect_hallucination_regex(r["response"])
        groundedness_score = _HALLUC_TO_SCORE.get(halluc_label, 0.5)

        correct = r["tool_used"] == r["expected_tool"]
        if correct:
            passed += 1

        results.append({
            **r,
            "correct": correct,
            "reasoning_score": reasoning_score,
            "groundedness_score": groundedness_score,
            "hallucination_label": halluc_label,
        })

    total = len(test_cases)
    accuracy = round(passed / total, 4)
    avg_reasoning = round(sum(r["reasoning_score"] for r in results) / total, 4)
    avg_groundedness = round(sum(r["groundedness_score"] for r in results) / total, 4)

    return {
        "tool_accuracy": accuracy,
        "avg_reasoning": avg_reasoning,
        "avg_groundedness": avg_groundedness,
        "total_tests": total,
        "passed_tests": passed,
        "results": results,
    }
