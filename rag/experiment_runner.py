"""
rag/experiment_runner.py — TrustLLM RAG Debugger core
======================================================
Runs the **same question across a matrix of RAG configs** and returns a
comparison table. This is the "change one variable → re-measure → compare"
loop: vary chunk size, overlap, top-k, embedding model, and prompt, then
score each run with fast embedding metrics (always) and RAGAS (optional).

Design
------
* An index-time signature ``(embedding_model, chunk_size, chunk_overlap)``
  fully determines a ChromaDB collection, so each unique signature is built
  **once** via ``ensure_indexed``; query-time knobs (top_k, prompt, model)
  reuse it. ``index_signatures`` reports how many builds a matrix implies.
* Pure logic — **no Streamlit** — so it is unit-testable and runnable from
  the CLI (``python -m rag.experiment_runner``).
"""

import itertools
from typing import Dict, List, Optional

from .ingestion import (
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    collection_signature,
    ensure_indexed,
)
from .embeddings import DEFAULT_EMBEDDING, embedding_available
from .rag_pipeline import DEFAULT_MODEL, DEFAULT_PROMPT_VARIANT, run_rag_query
from .retriever import TOP_K
from .evaluator import evaluate_rag

# Dimensions enumerated for every config, in a stable, human-friendly order.
_DIMENSIONS = [
    "embedding_model",
    "chunk_size",
    "chunk_overlap",
    "top_k",
    "prompt_variant",
    "gen_model",
]

# Per-dimension fallback when a matrix omits a dimension (single value).
DEFAULT_MATRIX: Dict[str, list] = {
    "embedding_model": [DEFAULT_EMBEDDING],
    "chunk_size": [CHUNK_SIZE],
    "chunk_overlap": [CHUNK_OVERLAP],
    "top_k": [TOP_K],
    "prompt_variant": [DEFAULT_PROMPT_VARIANT],
    "gen_model": [DEFAULT_MODEL],
}


def build_configs(matrix: Dict[str, list]) -> List[dict]:
    """
    Cartesian product of ``matrix`` → list of fully-specified configs.

    Dimensions absent from ``matrix`` (or empty) fall back to ``DEFAULT_MATRIX``.
    Each returned config carries all six dimensions plus a ``collection_name``.
    """
    merged = {dim: list(matrix.get(dim) or DEFAULT_MATRIX[dim]) for dim in _DIMENSIONS}
    configs = []
    for combo in itertools.product(*(merged[d] for d in _DIMENSIONS)):
        cfg = dict(zip(_DIMENSIONS, combo))
        cfg["collection_name"] = collection_signature(
            cfg["embedding_model"], cfg["chunk_size"], cfg["chunk_overlap"]
        )
        configs.append(cfg)
    return configs


def index_signatures(configs: List[dict]) -> List[tuple]:
    """
    Unique ``(embedding_model, chunk_size, chunk_overlap)`` signatures.

    These are the combinations that require (re)building a ChromaDB
    collection. Order-preserving and de-duplicated, so ``len(...)`` is the
    number of (re)index builds a sweep will trigger.
    """
    seen: List[tuple] = []
    for cfg in configs:
        sig = (cfg["embedding_model"], cfg["chunk_size"], cfg["chunk_overlap"])
        if sig not in seen:
            seen.append(sig)
    return seen


def config_label(cfg: dict) -> str:
    """Compact one-line label for a config (used in tables and charts)."""
    return (
        f"{cfg['embedding_model']} · cs{cfg['chunk_size']}/co{cfg['chunk_overlap']} · "
        f"k{cfg['top_k']} · {cfg['prompt_variant']}"
    )


def run_experiment(
    question: str,
    source_pdf: str,
    matrix: Dict[str, list],
    reference_answer: Optional[str] = None,
    score_ragas: bool = True,
    progress=None,
) -> dict:
    """
    Run the full sweep and return configs + per-config metric rows.

    Parameters
    ----------
    question         : the question asked of every config
    source_pdf       : path to the PDF to (re)index per index-signature
    matrix           : dict of dimension → list of values
    reference_answer : optional ground truth (enables RAGAS context metrics)
    score_ragas      : attempt RAGAS scoring (graceful if unavailable)
    progress         : optional callback(done, total, label) for UI progress

    Returns
    -------
    dict with keys: question, source, configs, rows, ragas
    """
    all_configs = build_configs(matrix)

    # --- 0. Drop configs whose embedding can't load here (e.g. BGE without
    #        sentence-transformers) so one unavailable model never crashes the
    #        whole sweep — it's reported as skipped instead. ---
    configs: List[dict] = []
    skipped: List[dict] = []
    for cfg in all_configs:
        if embedding_available(cfg["embedding_model"]):
            configs.append(cfg)
        else:
            skipped.append({
                "label": config_label(cfg),
                "reason": (
                    f"'{cfg['embedding_model']}' embedding unavailable here "
                    "(needs sentence-transformers / torch — runs locally)"
                ),
            })

    if not configs:
        return {
            "question": question,
            "source": source_pdf,
            "configs": [],
            "rows": [],
            "skipped": skipped,
            "ragas": {"status": "skipped", "reason": "no runnable configs"},
        }

    # --- 1. Build each unique collection once (skip a signature on failure) ---
    failed_sigs = set()
    sigs = index_signatures(configs)
    for i, (emb, cs, co) in enumerate(sigs):
        if progress:
            progress(i, len(sigs), f"indexing {emb} cs{cs}/co{co}")
        try:
            ensure_indexed(source_pdf, embedding_model=emb, chunk_size=cs, chunk_overlap=co)
        except Exception as exc:
            failed_sigs.add((emb, cs, co))
            skipped.append({
                "label": f"{emb} · cs{cs}/co{co}",
                "reason": f"indexing failed: {type(exc).__name__}: {exc}",
            })

    # --- 2. Run every runnable config + fast embedding metrics ---
    rows: List[dict] = []
    runnable = [
        c for c in configs
        if (c["embedding_model"], c["chunk_size"], c["chunk_overlap"]) not in failed_sigs
    ]
    total = len(runnable)
    for idx, cfg in enumerate(runnable):
        if progress:
            progress(idx, total, config_label(cfg))
        try:
            result = run_rag_query(
                question,
                model=cfg["gen_model"],
                top_k=cfg["top_k"],
                collection_name=cfg["collection_name"],
                embedding_model=cfg["embedding_model"],
                prompt_variant=cfg["prompt_variant"],
            )
            fast = evaluate_rag(question, result.get("answer", ""), result.get("sources", []))
            rows.append(
                {
                    "config_id": idx,
                    "label": config_label(cfg),
                    "collection_name": cfg["collection_name"],
                    **{k: cfg[k] for k in _DIMENSIONS},
                    "answer": result.get("answer", ""),
                    "contexts": result.get("contexts", []),
                    "sources": result.get("sources", []),
                    "latency": result.get("latency", {}),
                    **fast,  # context_relevance, faithfulness, hallucination_risk, recall_at_k, precision
                }
            )
        except Exception as exc:
            skipped.append({
                "label": config_label(cfg),
                "reason": f"run failed: {type(exc).__name__}: {exc}",
            })

    # --- 3. Optional RAGAS scoring ---
    ragas_summary = {"status": "skipped", "reason": "score_ragas=False"}
    if score_ragas and rows:
        ragas_summary = _attach_ragas(rows, question, reference_answer)

    if progress:
        progress(total, total, "done")

    return {
        "question": question,
        "source": source_pdf,
        "configs": configs,
        "rows": rows,
        "skipped": skipped,
        "ragas": ragas_summary,
    }


def best_row(rows: List[dict], metric: str = "faithfulness") -> Optional[dict]:
    """Return the row with the highest value for ``metric`` (or None)."""
    scored = [r for r in rows if isinstance(r.get(metric), (int, float))]
    return max(scored, key=lambda r: r[metric]) if scored else None


def biggest_single_variable_delta(
    rows: List[dict], metric: str = "faithfulness"
) -> Optional[dict]:
    """
    Largest change in ``metric`` attributable to changing **exactly one**
    dimension between two configs — the core "why did it get better/worse"
    insight. Returns a dict describing the change, or None.
    """
    best = None
    for a, b in itertools.combinations(rows, 2):
        diffs = [d for d in _DIMENSIONS if a.get(d) != b.get(d)]
        if len(diffs) != 1:
            continue
        va, vb = a.get(metric), b.get(metric)
        if not isinstance(va, (int, float)) or not isinstance(vb, (int, float)):
            continue
        delta = abs(va - vb)
        if best is None or delta > best["delta"]:
            lo, hi = (a, b) if va <= vb else (b, a)
            dim = diffs[0]
            best = {
                "dimension": dim,
                "from_value": lo.get(dim),
                "to_value": hi.get(dim),
                "from_score": lo.get(metric),
                "to_score": hi.get(metric),
                "delta": round(delta, 4),
                "metric": metric,
            }
    return best


def _attach_ragas(rows: List[dict], question: str, reference_answer: Optional[str]) -> dict:
    """Score each row with RAGAS and merge results in-place. Graceful."""
    try:
        from evaluation_engine.ragas_runner import score_samples
    except Exception as exc:  # ragas_runner itself never hard-fails, but be safe
        return {"status": "skipped", "reason": f"ragas_runner import failed: {exc}"}

    samples = [
        {
            "question": question,
            "answer": row.get("answer", ""),
            "contexts": row.get("contexts", []),
            "reference": reference_answer,
        }
        for row in rows
    ]
    try:
        summary = score_samples(samples)
    except Exception as exc:
        # RAGAS must never crash the sweep — fast metrics still stand.
        return {
            "status": "error",
            "reason": f"ragas scoring failed: {type(exc).__name__}: {exc}",
            "results": [],
        }
    if summary.get("status") == "ok":
        for row, scored in zip(rows, summary.get("results", [])):
            for k, v in (scored or {}).items():
                row[f"ragas_{k}"] = v
    return summary


# ---------------------------------------------------------------------------
# CLI smoke test:  python -m rag.experiment_runner --pdf path.pdf --question "..."
# ---------------------------------------------------------------------------
def _find_sample_pdf() -> Optional[str]:
    from .ingestion import UPLOADED_PDF_DIR

    if UPLOADED_PDF_DIR.exists():
        pdfs = sorted(UPLOADED_PDF_DIR.glob("*.pdf"))
        if pdfs:
            return str(pdfs[0])
    return None


def _print_table(result: dict) -> None:
    rows = result["rows"]
    print(f"\nQuestion: {result['question']}")
    print(f"Source:   {result['source']}")
    print(f"RAGAS:    {result['ragas'].get('status')} "
          f"({result['ragas'].get('reason', result['ragas'].get('judge', ''))})")
    print("-" * 90)
    print(f"{'config':<50}{'faith':>9}{'ctx_rel':>9}{'recall':>9}")
    print("-" * 90)
    for r in rows:
        print(
            f"{r['label']:<50}"
            f"{r.get('faithfulness', 0):>9.3f}"
            f"{r.get('context_relevance', 0):>9.3f}"
            f"{r.get('recall_at_k', 0):>9.3f}"
        )
    delta = biggest_single_variable_delta(rows)
    if delta:
        print("-" * 90)
        print(
            f"Biggest delta: {delta['dimension']} "
            f"{delta['from_value']}→{delta['to_value']} moved faithfulness "
            f"{delta['from_score']:.3f}→{delta['to_score']:.3f} (Δ{delta['delta']:.3f})"
        )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="TrustLLM RAG Debugger — sweep runner")
    parser.add_argument("--pdf", default=None, help="Path to a source PDF")
    parser.add_argument("--question", default="What is this document about?")
    parser.add_argument("--chunk-sizes", default="300,1000")
    parser.add_argument("--top-k", default="3,5")
    parser.add_argument("--prompts", default="grounded,cot")
    parser.add_argument("--embeddings", default="minilm")
    parser.add_argument("--no-ragas", action="store_true")
    args = parser.parse_args()

    pdf = args.pdf or _find_sample_pdf()
    if not pdf:
        print(
            "No PDF found. Pass --pdf <path>, or upload one in the RAG Testing "
            "page first (it persists to data/uploads/)."
        )
        raise SystemExit(1)

    matrix = {
        "embedding_model": args.embeddings.split(","),
        "chunk_size": [int(x) for x in args.chunk_sizes.split(",")],
        "top_k": [int(x) for x in args.top_k.split(",")],
        "prompt_variant": args.prompts.split(","),
    }
    try:
        res = run_experiment(
            args.question,
            pdf,
            matrix,
            score_ragas=not args.no_ragas,
            progress=lambda d, t, label: print(f"[{d}/{t}] {label}"),
        )
    except RuntimeError as exc:
        # Most commonly a missing GROQ_API_KEY surfaced from generation.
        print(f"\nSweep could not complete: {exc}")
        raise SystemExit(1)
    _print_table(res)
