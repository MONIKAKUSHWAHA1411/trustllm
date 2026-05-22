"""
evaluation_engine/llm_judge.py — TrustLLM CLI judge step
==========================================================
Batch step in the offline evaluation pipeline.

Reads  : reports/evaluated_results.json
Writes : reports/judged_results.json

For each item with a ``prompt`` and ``response`` (or ``model_response``),
asks Groq to score the response on six trust dimensions:
truthfulness, safety, fairness, privacy, robustness, ethics.

Requires GROQ_API_KEY (Streamlit secret or environment variable).
"""

import json
import sys
import time
from pathlib import Path

from .judge import judge_response, DIMENSIONS


REPORT_DIR = Path(__file__).resolve().parents[1] / "reports"
INPUT_FILE = REPORT_DIR / "evaluated_results.json"
OUTPUT_FILE = REPORT_DIR / "judged_results.json"


def _get_response_text(item: dict) -> str:
    """Pipeline files have used both keys at different points — accept either."""
    return item.get("response") or item.get("model_response") or ""


def judge_responses(input_path: Path = INPUT_FILE, output_path: Path = OUTPUT_FILE) -> None:
    if not input_path.exists():
        print(f"Input not found: {input_path}", file=sys.stderr)
        print("Run the test runner first to produce evaluated_results.json.", file=sys.stderr)
        sys.exit(1)

    with open(input_path) as f:
        results = json.load(f)

    if not results:
        print("Input file is empty — nothing to judge.")
        return

    judged = []
    failures = 0

    for i, item in enumerate(results, start=1):
        prompt = item.get("prompt", "")
        response = _get_response_text(item)

        if not prompt or not response:
            for k in DIMENSIONS:
                item[k] = 0.0
            item["judge_status"] = "skipped: missing prompt or response"
            judged.append(item)
            print(f"[{i}/{len(results)}] skipped — missing prompt or response")
            continue

        try:
            scores = judge_response(prompt, response)
            item.update(scores)
            item["judge_status"] = "ok"
            avg = round(sum(scores.values()) / 6, 3)
            print(f"[{i}/{len(results)}] judged · avg={avg} · {scores}")
        except Exception as e:
            for k in DIMENSIONS:
                item[k] = 0.0
            item["judge_status"] = f"error: {type(e).__name__}: {e}"
            failures += 1
            print(f"[{i}/{len(results)}] ERROR — {type(e).__name__}: {e}", file=sys.stderr)

        judged.append(item)
        time.sleep(0.15)  # rate-limit cushion for Groq free tier

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(judged, f, indent=2)

    summary = f"LLM judging completed — {len(judged)} items, {failures} failures"
    print(summary)
    print(f"Output: {output_path}")


if __name__ == "__main__":
    judge_responses()
