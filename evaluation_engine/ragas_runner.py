"""
evaluation_engine/ragas_runner.py — TrustLLM × RAGAS
=====================================================
Scores RAG answers with the **RAGAS** framework — the standard the
RAG Debugger uses to say *why* an answer got better or worse:

    * faithfulness       — is the answer grounded in the retrieved context?
    * answer_relevancy   — does the answer actually address the question?
    * context_precision  — (needs reference) are the retrieved chunks on-point?
    * context_recall     — (needs reference) did retrieval cover the answer?

RAGAS metrics are LLM-judged. By default RAGAS uses OpenAI, but this module
reuses TrustLLM's **Groq** key via ``langchain-groq`` + RAGAS's
``LangchainLLMWrapper`` — no extra provider required. Embeddings (needed by
``answer_relevancy``) come from a local HuggingFace MiniLM via
``LangchainEmbeddingsWrapper``.

Design notes
------------
* ``ragas`` and friends are **optional**. Every import is deferred into a
  function body, so importing this module never fails when the package isn't
  installed — ``score_samples`` then returns a ``skipped`` summary with a hint.
  This mirrors :mod:`evaluation_engine.deepeval_runner`.
* RAGAS + non-OpenAI judges can be flaky (JSON parsing / NaN). Failures are
  caught and surfaced as ``status="error"`` rather than crashing the sweep,
  and the RAG Debugger always shows its fast embedding metrics regardless.

Run it::

    pip install ragas langchain-groq sentence-transformers
    export GROQ_API_KEY=gsk_...
    python -m evaluation_engine.ragas_runner
"""

import os
from typing import List, Optional

# Quieter, no phone-home, when RAGAS is present.
os.environ.setdefault("RAGAS_DO_NOT_TRACK", "true")

# A 70B judge produces more reliable structured output than the 8B for RAGAS.
DEFAULT_JUDGE_MODEL = "llama-3.3-70b-versatile"
DEFAULT_EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def _get_groq_key() -> str:
    """Read GROQ_API_KEY from Streamlit secrets or environment."""
    try:
        from rag.rag_pipeline import _get_api_key
        return _get_api_key()
    except Exception:
        return os.getenv("GROQ_API_KEY", "")


def _build_ragas_llm(model_id: str):
    """Wrap Groq as a RAGAS judge. Returns wrapper or None if unavailable."""
    key = _get_groq_key()
    if not key:
        return None
    try:
        from langchain_groq import ChatGroq
        from ragas.llms import LangchainLLMWrapper
    except ImportError:
        return None
    chat = ChatGroq(model=model_id, temperature=0.0, api_key=key)
    return LangchainLLMWrapper(chat)


def _build_ragas_embeddings(model_name: str):
    """Wrap a local HF embedding model for RAGAS. Returns wrapper or None."""
    try:
        from ragas.embeddings import LangchainEmbeddingsWrapper
    except ImportError:
        return None
    HuggingFaceEmbeddings = None
    try:  # preferred package
        from langchain_huggingface import HuggingFaceEmbeddings
    except ImportError:
        try:  # legacy location
            from langchain_community.embeddings import HuggingFaceEmbeddings
        except ImportError:
            return None
    try:
        return LangchainEmbeddingsWrapper(HuggingFaceEmbeddings(model_name=model_name))
    except Exception:
        return None


def _make_dataset(samples: List[dict], has_reference: bool, style: str):
    """Build a HF Dataset using new-style (0.2+) or legacy (0.1) column names."""
    from datasets import Dataset

    questions = [s.get("question", "") for s in samples]
    answers = [s.get("answer", "") for s in samples]
    contexts = [list(s.get("contexts") or []) for s in samples]

    if style == "new":
        data = {
            "user_input": questions,
            "response": answers,
            "retrieved_contexts": contexts,
        }
        if has_reference:
            data["reference"] = [s.get("reference", "") for s in samples]
    else:  # legacy
        data = {
            "question": questions,
            "answer": answers,
            "contexts": contexts,
        }
        if has_reference:
            data["ground_truth"] = [s.get("reference", "") for s in samples]
    return Dataset.from_dict(data)


def score_samples(
    samples: List[dict],
    judge_model: str = DEFAULT_JUDGE_MODEL,
    embed_model: str = DEFAULT_EMBED_MODEL,
) -> dict:
    """
    Score a list of RAG samples with RAGAS.

    Parameters
    ----------
    samples : list of dicts, each with keys:
        question  : str
        answer    : str
        contexts  : list[str]   (retrieved chunk texts)
        reference : str | None  (ground truth; enables context metrics)

    Returns
    -------
    dict
        status    : "ok" | "skipped" | "error"
        judge     : judge name (when ok)
        metrics   : list of metric names computed
        aggregate : {f"{metric}_avg": float|None}
        results   : list[dict] aligned with ``samples`` (per-metric scores)
        reason    : explanation (when skipped/error)
    """
    if not samples:
        return {"status": "skipped", "reason": "no samples", "results": []}

    # --- import guard (optional dependency) ---
    try:
        from ragas import evaluate
        from ragas.metrics import (
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
        )
        import datasets  # noqa: F401  (ensures HF datasets is present)
    except ImportError:
        return {
            "status": "skipped",
            "reason": "RAGAS not installed — run `pip install ragas datasets`",
            "results": [],
        }

    # --- judge + embeddings ---
    llm = _build_ragas_llm(judge_model)
    if llm is None:
        return {
            "status": "skipped",
            "reason": "no GROQ_API_KEY (or langchain-groq missing) for the RAGAS judge",
            "results": [],
        }
    emb = _build_ragas_embeddings(embed_model)

    # --- choose metrics based on what inputs/components we have ---
    has_reference = all((s.get("reference") or "").strip() for s in samples)
    metrics = [faithfulness]
    metric_cols = ["faithfulness"]
    if emb is not None:
        metrics.append(answer_relevancy)
        metric_cols.append("answer_relevancy")
    if has_reference:
        metrics += [context_precision, context_recall]
        metric_cols += ["context_precision", "context_recall"]

    # --- evaluate (try modern then legacy column conventions) ---
    df = None
    last_err: Optional[Exception] = None
    for style in ("new", "legacy"):
        try:
            dataset = _make_dataset(samples, has_reference, style)
            kwargs = {"metrics": metrics, "llm": llm}
            if emb is not None:
                kwargs["embeddings"] = emb
            result = evaluate(dataset, **kwargs)
            df = result.to_pandas()
            break
        except Exception as exc:  # try the other column style, else report
            last_err = exc
            df = None
    if df is None:
        return {
            "status": "error",
            "reason": f"ragas evaluate failed: {type(last_err).__name__}: {last_err}",
            "results": [],
        }

    # --- extract per-sample + aggregate (NaN -> None) ---
    import pandas as pd

    results: List[dict] = []
    for _, prow in df.iterrows():
        entry = {}
        for col in metric_cols:
            if col in df.columns:
                val = prow[col]
                entry[col] = None if pd.isna(val) else round(float(val), 4)
        results.append(entry)

    aggregate = {}
    for col in metric_cols:
        vals = [r[col] for r in results if r.get(col) is not None]
        aggregate[f"{col}_avg"] = round(sum(vals) / len(vals), 4) if vals else None

    return {
        "status": "ok",
        "judge": f"Groq:{judge_model}",
        "metrics": metric_cols,
        "evaluated": len(results),
        "aggregate": aggregate,
        "results": results,
    }


if __name__ == "__main__":
    # Tiny self-test — prints a skipped summary if RAGAS/key are unavailable.
    demo = [
        {
            "question": "What is the capital of Australia?",
            "answer": "The capital of Australia is Canberra.",
            "contexts": ["Canberra is the capital city of Australia."],
            "reference": "Canberra",
        }
    ]
    summary = score_samples(demo)
    print("status:", summary["status"])
    if summary["status"] == "ok":
        print("judge:", summary["judge"])
        print("aggregate:", summary["aggregate"])
        print("per-sample:", summary["results"])
    else:
        print("reason:", summary.get("reason"))
