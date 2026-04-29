"""
run_agent_eval.py — TrustLLM Phase 8
=====================================
Runs the agentic evaluation pipeline and prints tool-selection metrics.

Usage
-----
    python run_agent_eval.py
    python run_agent_eval.py --dataset datasets/agent_test_cases.json
    python run_agent_eval.py --save            # also writes reports/agent_eval_results.json
"""

import argparse
import json
import os
from pathlib import Path

from agents.hr_agent import HRAgent
from evaluators.agent_eval import evaluate_agent

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATASET = BASE_DIR / "datasets" / "agent_test_cases.json"
REPORT_PATH = BASE_DIR / "reports" / "agent_eval_results.json"


def main():
    parser = argparse.ArgumentParser(description="TrustLLM — Agent Evaluation")
    parser.add_argument(
        "--dataset",
        default=str(DEFAULT_DATASET),
        help="Path to agent test-case JSON dataset",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Write detailed results to reports/agent_eval_results.json",
    )
    args = parser.parse_args()

    print("Running Agent Evaluation...")
    print(f"Dataset : {args.dataset}")
    print("-" * 40)

    agent = HRAgent()
    metrics = evaluate_agent(agent, args.dataset)

    total   = metrics["total_tests"]
    passed  = metrics["passed_tests"]
    accuracy = metrics["tool_accuracy"]

    print(f"Total Tests  : {total}")
    print(f"Passed       : {passed}")
    print(f"Tool Accuracy: {accuracy:.2%}")
    print("-" * 40)

    # Per-case breakdown
    print("\nPer-case results:")
    for r in metrics["results"]:
        status = "✓" if r["correct"] else "✗"
        print(
            f"  [{status}] {r['query']!r:50s}"
            f"  expected={r['expected_tool']}  got={r['tool_used']}"
        )

    if args.save:
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        # Strip per-case results for a compact summary report
        summary = {k: v for k, v in metrics.items() if k != "results"}
        summary["results"] = metrics["results"]
        with open(REPORT_PATH, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"\nDetailed results saved to {REPORT_PATH}")


if __name__ == "__main__":
    main()
