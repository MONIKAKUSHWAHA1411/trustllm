"""
ui_pages/experiments.py — TrustLLM RAG Debugger
================================================
The "change one variable → re-measure → compare" loop.

Pick a PDF + question, define a matrix over chunk size / overlap / top-k /
prompt / embedding model, run the sweep, and compare every config side by
side. Each run is scored with fast embedding metrics (always) and RAGAS
(optional). Runs persist per-user so they can be reloaded later.

Exposes a single ``render()`` called by app.py (matches the page convention).
"""

import json
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parents[1]

from rag.ingestion import UPLOADED_PDF_DIR
from rag.embeddings import AVAILABLE_EMBEDDINGS, embedding_available
from rag.rag_pipeline import AVAILABLE_MODELS, PROMPT_VARIANTS
from rag.experiment_runner import (
    run_experiment,
    build_configs,
    index_signatures,
    best_row,
    biggest_single_variable_delta,
)

# Matrix option menus.
_CHUNK_SIZES = [200, 300, 500, 800, 1000, 1200]
_OVERLAPS = [0, 50, 100]
_TOP_KS = [1, 3, 5, 10]
_PROMPTS = list(PROMPT_VARIANTS.keys())
_EMBEDDINGS = list(AVAILABLE_EMBEDDINGS.keys())


# -----------------------------------------------------------------------
# Per-user persistence (mirrors ui_pages/run_eval.py)
# -----------------------------------------------------------------------
def _runs_dir() -> Path:
    user_id = st.session_state.get("user", {}).get("id", "default")
    safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in user_id)
    path = BASE_DIR / "reports" / safe_id / "rag_experiments"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _save_run(result: dict, matrix: dict) -> Path:
    payload = {
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "matrix": matrix,
        "result": result,
    }
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = _runs_dir() / f"{run_id}.json"
    with open(path, "w") as f:
        json.dump(payload, f, indent=2, default=str)
    return path


def _list_pdfs() -> list:
    if UPLOADED_PDF_DIR.exists():
        return sorted(p.name for p in UPLOADED_PDF_DIR.glob("*.pdf"))
    return []


# -----------------------------------------------------------------------
# Results rendering
# -----------------------------------------------------------------------
def _primary_faithfulness(row: dict) -> float:
    """Prefer RAGAS faithfulness when present, else the fast metric."""
    rf = row.get("ragas_faithfulness")
    return rf if isinstance(rf, (int, float)) else row.get("faithfulness", 0.0)


def _results_table(rows: list) -> pd.DataFrame:
    base_cols = [
        "label", "embedding_model", "chunk_size", "chunk_overlap", "top_k",
        "prompt_variant", "faithfulness", "context_relevance", "recall_at_k",
        "precision", "hallucination_risk",
    ]
    ragas_cols = sorted({c for r in rows for c in r if c.startswith("ragas_")})
    records = []
    for r in rows:
        rec = {c: r.get(c) for c in base_cols + ragas_cols}
        rec["total_s"] = (r.get("latency") or {}).get("total_time")
        records.append(rec)
    return pd.DataFrame(records)


def _render_results(result: dict):
    rows = result.get("rows", [])
    skipped = result.get("skipped") or []
    if not rows:
        st.warning("No runnable configs in this sweep.")
        for s in skipped:
            st.caption(f"• {s.get('label', '?')} — {s.get('reason', '')}")
        return

    if skipped:
        with st.expander(f"⚠️ {len(skipped)} config(s) skipped (not runnable here)", expanded=False):
            for s in skipped:
                st.caption(f"• {s.get('label', '?')} — {s.get('reason', '')}")

    ragas = result.get("ragas", {})
    if ragas.get("status") == "ok":
        st.success(f"RAGAS scored with {ragas.get('judge')} · metrics: {', '.join(ragas.get('metrics', []))}")
    elif ragas.get("status") == "error":
        st.warning(f"RAGAS error (fast metrics still shown): {ragas.get('reason')}")
    elif ragas.get("status") == "skipped" and ragas.get("reason") != "score_ragas=False":
        st.info(f"RAGAS skipped — {ragas.get('reason')}")

    # --- Headline callouts ---
    best = best_row(rows, "faithfulness")
    delta = biggest_single_variable_delta(rows, "faithfulness")
    c1, c2 = st.columns(2)
    with c1:
        if best:
            st.metric(
                "Best config (faithfulness)",
                f"{_primary_faithfulness(best):.3f}",
                help="Highest faithfulness across the swept configs.",
            )
            st.caption(f"🏆 {best['label']}")
    with c2:
        if delta:
            st.metric(
                f"Biggest single-variable swing · {delta['dimension']}",
                f"Δ {delta['delta']:.3f}",
            )
            st.caption(
                f"{delta['dimension']} {delta['from_value']} → {delta['to_value']} "
                f"moved faithfulness {delta['from_score']:.3f} → {delta['to_score']:.3f}"
            )
        else:
            st.caption("Sweep two or more configs differing by one knob to see attribution.")

    # --- Comparison table ---
    st.subheader("Comparison")
    df = _results_table(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # --- Chart: faithfulness per config (fast vs RAGAS when present) ---
    chart_records = []
    for r in rows:
        chart_records.append({"config": r["label"], "metric": "faithfulness (fast)",
                              "score": r.get("faithfulness", 0.0)})
        if isinstance(r.get("ragas_faithfulness"), (int, float)):
            chart_records.append({"config": r["label"], "metric": "faithfulness (RAGAS)",
                                  "score": r["ragas_faithfulness"]})
    try:
        import plotly.express as px
        fig = px.bar(
            pd.DataFrame(chart_records),
            x="config", y="score", color="metric", barmode="group",
            range_y=[0, 1],
        )
        fig.update_layout(xaxis_title="", legend_title="", height=380, margin=dict(t=10))
        st.plotly_chart(fig, use_container_width=True)
    except Exception:
        st.bar_chart(df.set_index("label")[["faithfulness"]])

    # --- Per-config drill-down ---
    st.subheader("Per-config drill-down")
    for r in rows:
        with st.expander(f"{r['label']}  ·  faithfulness {r.get('faithfulness', 0):.3f}"):
            st.markdown("**Answer**")
            st.write(r.get("answer", ""))
            srcs = r.get("sources", [])
            st.markdown(f"**Retrieved chunks ({len(srcs)})**")
            try:
                from ui_pages.rag_page import _highlight_keywords
            except Exception:
                _highlight_keywords = None
            for j, doc in enumerate(srcs, 1):
                meta = doc.get("metadata", {})
                score = doc.get("score", 0.0)
                st.caption(f"[{j}] score {score:.3f} · {meta.get('source', '?')} p.{meta.get('page', '?')}")
                text = doc.get("text", "")
                if _highlight_keywords:
                    st.markdown(_highlight_keywords(text, result.get("question", "")),
                                unsafe_allow_html=True)
                else:
                    st.write(text)


# -----------------------------------------------------------------------
# Main page
# -----------------------------------------------------------------------
def render():
    st.title("🧪 RAG Debugger")
    st.caption(
        "Change one variable → re-measure → compare. Run the same question "
        "across chunking, top-k, prompt, and embedding configs, then see which "
        "choice moved faithfulness — verified with RAGAS."
    )

    pdfs = _list_pdfs()
    if not pdfs:
        st.info(
            "No indexed PDFs yet. Go to **RAG Testing → Document Upload** to add "
            "one — it persists to `data/uploads/` and will appear here."
        )
        if st.button("Go to RAG Testing"):
            st.session_state["nav_page"] = "RAG Testing"
            st.rerun()
        return

    # --- Setup ---
    st.subheader("1 · Setup")
    col_a, col_b = st.columns([2, 3])
    with col_a:
        source_pdf = st.selectbox("Source PDF", pdfs)
    with col_b:
        question = st.text_input("Question", value="What is this document about?")
    with st.expander("Optional: reference answer (enables RAGAS context precision/recall)"):
        reference_answer = st.text_area("Ground-truth answer", value="", height=80)

    # --- Matrix ---
    st.subheader("2 · Variables to sweep")
    m1, m2, m3 = st.columns(3)
    with m1:
        chunk_sizes = st.multiselect("Chunk size", _CHUNK_SIZES, default=[300, 1000])
        overlaps = st.multiselect("Chunk overlap", _OVERLAPS, default=[50])
    with m2:
        top_ks = st.multiselect("Top-K", _TOP_KS, default=[3, 5])
        prompts = st.multiselect("Prompt variant", _PROMPTS, default=["grounded", "cot"])
    with m3:
        embeddings = st.multiselect(
            "Embedding model", _EMBEDDINGS, default=["minilm"],
            format_func=lambda k: AVAILABLE_EMBEDDINGS.get(k, {}).get("label", k),
        )
        gen_model = st.selectbox("Generation model", AVAILABLE_MODELS)

    score_ragas = st.checkbox("Score with RAGAS (slower, needs GROQ_API_KEY)", value=True)

    matrix = {
        "embedding_model": embeddings or ["minilm"],
        "chunk_size": chunk_sizes or [500],
        "chunk_overlap": overlaps or [50],
        "top_k": top_ks or [3],
        "prompt_variant": prompts or ["grounded"],
        "gen_model": [gen_model],
    }

    # --- Preview cost ---
    configs = build_configs(matrix)
    n_builds = len(index_signatures(configs))
    st.markdown(
        f"**{len(configs)} configs** · **{n_builds} collection build(s)** "
        f"(unique embedding × chunk × overlap)"
    )
    unavailable = [e for e in (embeddings or []) if not embedding_available(e)]
    if unavailable:
        names = ", ".join(AVAILABLE_EMBEDDINGS.get(e, {}).get("label", e) for e in unavailable)
        st.warning(
            f"⚠️ {names} isn't available on this deployment (needs `sentence-transformers`). "
            "Those configs will be **skipped** here — install `requirements-dev.txt` locally "
            "for the full embedding comparison. The sweep still runs the others."
        )
    elif "bge" in (embeddings or []):
        st.caption("⚠️ BGE loads `sentence-transformers` (torch) on first use — the initial build is slower.")
    if len(configs) > 16:
        st.warning(f"{len(configs)} configs is a lot of LLM calls — consider narrowing the matrix.")

    # --- Run ---
    if st.button("▶ Run sweep", type="primary"):
        total_calls = n_builds + len(configs) + 1
        bar = st.progress(0.0)
        status = st.empty()
        counter = {"n": 0}

        def _progress(done, total, label):
            counter["n"] += 1
            bar.progress(min(counter["n"] / max(total_calls, 1), 1.0))
            status.caption(f"⏳ {label}")

        t0 = time.perf_counter()
        try:
            result = run_experiment(
                question,
                str(UPLOADED_PDF_DIR / source_pdf),
                matrix,
                reference_answer=reference_answer.strip() or None,
                score_ragas=score_ragas,
                progress=_progress,
            )
        except Exception as exc:
            bar.empty()
            status.empty()
            st.error(f"Sweep failed: {type(exc).__name__}: {exc}")
            return

        bar.empty()
        status.empty()
        elapsed = time.perf_counter() - t0
        saved = _save_run(result, matrix)
        st.session_state["rag_debugger_result"] = result
        st.success(f"Done in {elapsed:.1f}s · saved to {saved.relative_to(BASE_DIR)}")

    # --- Show latest result (from this session) ---
    if "rag_debugger_result" in st.session_state:
        st.divider()
        _render_results(st.session_state["rag_debugger_result"])

    # --- Past runs ---
    runs = sorted(_runs_dir().glob("*.json"), reverse=True)
    if runs:
        st.divider()
        st.subheader("Past runs")
        labels = [p.stem for p in runs]
        chosen = st.selectbox("Reload a saved run", ["—"] + labels)
        if chosen != "—":
            with open(_runs_dir() / f"{chosen}.json") as f:
                payload = json.load(f)
            st.caption(f"Saved {payload.get('saved_at')} · question: {payload['result'].get('question')}")
            _render_results(payload["result"])
