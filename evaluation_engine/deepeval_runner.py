"""
evaluation_engine/deepeval_runner.py — TrustLLM × DeepEval
===========================================================
Runs the open-source **DeepEval** framework over the model responses, giving
TrustLLM a second, industry-standard opinion on GenAI response quality:

    * AnswerRelevancyMetric — does the answer address the question?
    * BiasMetric            — does the answer contain social bias?
    * ToxicityMetric        — is the answer toxic / harassing?
    * FaithfulnessMetric    — (RAG only) is the answer grounded in context?

DeepEval's metrics are themselves LLM-judged. By default DeepEval uses OpenAI,
but this module ships a **custom Groq-backed judge** (``GroqDeepEvalLLM``) so it
reuses the same Groq key the rest of TrustLLM already relies on — no extra
provider required.

Design notes
------------
* ``deepeval`` is an **optional** dependency. Every import of it is deferred
  into a function body, so importing this module never fails even when the
  package isn't installed. ``run_deepeval`` then returns a ``skipped`` summary
  with an install hint.
* Judge selection: Groq (if GROQ_API_KEY) → DeepEval default (if OPENAI_API_KEY)
  → skip.

Run it::

    pip install deepeval
    export GROQ_API_KEY=gsk_...
    python -m evaluation_engine.deepeval_runner
"""

import json
import os
import re
from pathlib import Path

REPORT_DIR = Path(__file__).resolve().parents[1] / "reports"
INPUT_FILE = REPORT_DIR / "evaluated_results.json"
OUTPUT_FILE = REPORT_DIR / "deepeval_results.json"

DEFAULT_JUDGE_MODEL = "llama-3.1-8b-instant"


def _build_groq_model(model_id: str = DEFAULT_JUDGE_MODEL):
    """Construct a DeepEval custom model backed by Groq.

    Defined lazily so ``deepeval`` is only imported when actually used. Returns
    a ``GroqDeepEvalLLM`` instance, or ``None`` if no GROQ_API_KEY is set.
    """
    if not os.getenv("GROQ_API_KEY"):
        return None

    from deepeval.models import DeepEvalBaseLLM

    class GroqDeepEvalLLM(DeepEvalBaseLLM):
        """Adapts TrustLLM's Groq client to DeepEval's judge interface."""

        def __init__(self, model: str):
            self.model = model
            self._client = None

        def load_model(self):
            if self._client is None:
                from rag.rag_pipeline import _get_groq_client
                self._client = _get_groq_client()
            return self._client

        def _complete(self, prompt: str) -> str:
            client = self.load_model()
            resp = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=800,
            )
            return resp.choices[0].message.content

        def generate(self, prompt: str, schema=None):
            """Return raw text, or a populated pydantic ``schema`` instance.

            Newer DeepEval versions pass a pydantic ``schema`` and expect an
            instance back; older versions call without one and parse the string
            themselves. Both paths are supported here.
            """
            if schema is None:
                return self._complete(prompt)

            instruction = (
                prompt
                + "\n\nRespond with ONLY a valid JSON object matching this schema:\n"
                + json.dumps(schema.model_json_schema())
            )
            text = self._complete(instruction)
            match = re.search(r"\{.*\}", text, re.DOTALL)
            data = json.loads(match.group()) if match else {}
            return schema(**data)

        async def a_generate(self, prompt: str, schema=None):
            return self.generate(prompt, schema)

        def get_model_name(self) -> str:
            return f"Groq:{self.model}"

    return GroqDeepEvalLLM(model_id)


def _select_judge(model_id: str = DEFAULT_JUDGE_MODEL):
    """Pick a DeepEval judge model. Returns (model_or_None, name, available)."""
    groq_model = _build_groq_model(model_id)
    if groq_model is not None:
        return groq_model, groq_model.get_model_name(), True
    if os.getenv("OPENAI_API_KEY"):
        # None tells DeepEval to use its built-in default (OpenAI).
        return None, "deepeval-default(openai)", True
    return None, "none", False


def run_deepeval(
    input_path: Path = INPUT_FILE,
    output_path: Path = OUTPUT_FILE,
    threshold: float = 0.5,
    model_id: str = DEFAULT_JUDGE_MODEL,
) -> dict:
    """Evaluate every response with DeepEval metrics and write a JSON report.

    Returns a summary dict. Degrades gracefully:
      * deepeval not installed -> {"status": "skipped", ...}
      * no judge key available -> {"status": "skipped", ...}
    """
    try:
        from deepeval.test_case import LLMTestCase
        from deepeval.metrics import (
            AnswerRelevancyMetric,
            BiasMetric,
            ToxicityMetric,
        )
    except ImportError:
        summary = {
            "status": "skipped",
            "reason": "deepeval is not installed — run `pip install deepeval`",
            "results": [],
        }
        _write(output_path, summary)
        print(summary["reason"])
        return summary

    judge, judge_name, available = _select_judge(model_id)
    if not available:
        summary = {
            "status": "skipped",
            "reason": "no judge key found — set GROQ_API_KEY (preferred) or OPENAI_API_KEY",
            "results": [],
        }
        _write(output_path, summary)
        print(summary["reason"])
        return summary

    with open(input_path) as f:
        items = json.load(f)

    # Build metrics. Passing model=None lets DeepEval use its own default.
    metric_kwargs = {"threshold": threshold}
    if judge is not None:
        metric_kwargs["model"] = judge

    def _new_metrics():
        return {
            "answer_relevancy": AnswerRelevancyMetric(**metric_kwargs),
            "bias": BiasMetric(**metric_kwargs),
            "toxicity": ToxicityMetric(**metric_kwargs),
        }

    detailed = []
    sums = {"answer_relevancy": 0.0, "bias": 0.0, "toxicity": 0.0}
    counts = {"answer_relevancy": 0, "bias": 0, "toxicity": 0}

    for item in items:
        prompt = item.get("prompt", "")
        response = item.get("response") or item.get("model_response") or ""
        if not prompt or not response:
            continue

        test_case = LLMTestCase(input=prompt, actual_output=response)
        scores, reasons, success = {}, {}, {}

        for name, metric in _new_metrics().items():
            try:
                metric.measure(test_case)
                scores[name] = round(float(metric.score), 3)
                reasons[name] = getattr(metric, "reason", None)
                success[name] = bool(metric.is_successful())
                sums[name] += scores[name]
                counts[name] += 1
            except Exception as e:  # one metric failing shouldn't kill the run
                scores[name] = None
                reasons[name] = f"error: {type(e).__name__}: {e}"
                success[name] = None

        detailed.append({
            "id": item.get("id"),
            "category": item.get("category"),
            "prompt": prompt,
            "response": response,
            "scores": scores,
            "success": success,
            "reasons": reasons,
        })

    aggregate = {
        f"{k}_avg": (round(sums[k] / counts[k], 3) if counts[k] else None)
        for k in sums
    }
    summary = {
        "status": "ok",
        "judge": judge_name,
        "threshold": threshold,
        "metrics": list(sums.keys()),
        "evaluated": len(detailed),
        "aggregate": aggregate,
        "results": detailed,
    }
    _write(output_path, summary)
    print(f"DeepEval completed — {len(detailed)} cases judged by {judge_name}")
    print(f"Aggregate: {aggregate}")
    return summary


def _write(output_path: Path, payload: dict) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(payload, f, indent=2)


if __name__ == "__main__":
    run_deepeval()
