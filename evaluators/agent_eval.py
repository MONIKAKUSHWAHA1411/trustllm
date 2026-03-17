"""
Agent Evaluation Module — TrustLLM Phase 8
==========================================
Evaluates an AI agent's tool-selection accuracy against a labelled
test dataset.  No external services are required.
"""

import json
import os
from pathlib import Path


def evaluate_agent(agent, dataset_path: str) -> dict:
    """
    Evaluate agent tool-selection accuracy.

    Parameters
    ----------
    agent       : object with a ``run(query: str) -> dict`` method
                  The dict must contain at least the key ``tool_used``.
    dataset_path: str | Path
                  Path to a JSON file that is a list of objects, each with
                  keys ``query`` (str) and ``expected_tool`` (str).

    Returns
    -------
    dict
        tool_accuracy  – float in [0, 1]
        total_tests    – int
        passed_tests   – int
        results        – list[dict], one entry per test case
    """
    dataset_path = Path(dataset_path)
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    with open(dataset_path) as f:
        test_cases = json.load(f)

    if not test_cases:
        return {"tool_accuracy": 0.0, "total_tests": 0, "passed_tests": 0, "results": []}

    results = []
    passed = 0

    for case in test_cases:
        query = case["query"]
        expected_tool = case["expected_tool"]

        agent_output = agent.run(query)
        tool_used = agent_output.get("tool_used", "unknown")

        correct = tool_used == expected_tool
        if correct:
            passed += 1

        results.append(
            {
                "query": query,
                "expected_tool": expected_tool,
                "tool_used": tool_used,
                "correct": correct,
                "response": agent_output.get("response", ""),
            }
        )

    total = len(test_cases)
    accuracy = round(passed / total, 4)

    return {
        "tool_accuracy": accuracy,
        "total_tests": total,
        "passed_tests": passed,
        "results": results,
    }
