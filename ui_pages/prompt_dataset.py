"""
ui_pages/prompt_dataset.py — TrustLLM Prompt Dataset Evaluation
================================================================
Upload a CSV or JSON dataset of prompt/expected_answer pairs,
run them through the RAG pipeline in batch, and display:
    - Dataset Accuracy
    - Average Similarity
    - Hallucination Rate
    - Per-row results table
"""

import json
import sys
from pathlib import Path
from datetime import datetime

import streamlit as st

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

REPORT_PATH  = BASE_DIR / "reports" / "batch_eval_results.json"
PASS_THRESHOLD = 0.55   # cosine sim above this = pass

AVAILABLE_MODELS = ["phi3:mini", "mistral:instruct", "phi3", "phi", "mistral"]


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

def _parse_dataset(file) -> list[dict]:
    """Parse uploaded CSV or JSON into list of {prompt, expected_answer}."""
    name = file.name.lower()
    if name.endswith(".json"):
        data = json.loads(file.read().decode())
        if isinstance(data, list):
            return data
        raise ValueError("JSON must be a list of objects with 'prompt' and 'expected_answer'.")
    elif name.endswith(".csv"):
        import csv, io
        content = file.read().decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
        if not rows or "prompt" not in rows[0]:
            raise ValueError("CSV must have a 'prompt' column (and optionally 'expected_answer').")
        return rows
    raise ValueError(f"Unsupported file type: {file.name}")


def _cosine_sim(a, b) -> float:
    import numpy as np
    va, vb = np.array(a, dtype=np.float32), np.array(b, dtype=np.float32)
    na, nb = np.linalg.norm(va), np.linalg.norm(vb)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(va, vb) / (na * nb))


def _run_batch(dataset: list[dict], model: str, top_k: int) -> list[dict]:
    """Run every prompt through the RAG pipeline and evaluate."""
    from rag.rag_pipeline import run_rag_query
    from rag.embeddings import embed_texts

    results = []
    for row in dataset:
        prompt   = str(row.get("prompt", "")).strip()
        expected = str(row.get("expected_answer", "")).strip()
        if not prompt:
            continue

        try:
            rag_out  = run_rag_query(prompt, model=model, top_k=top_k)
            answer   = rag_out["answer"]
            latency  = rag_out.get("latency", {}).get("total_time", 0)
            hall_risk = 0.5   # default if we can't compute

            # Semantic similarity between expected and actual
            if expected:
                vecs = embed_texts([expected, answer])
                sim  = round(_cosine_sim(vecs[0], vecs[1]), 4)
            else:
                sim = None

            passed = (sim is not None and sim >= PASS_THRESHOLD)

            results.append({
                "prompt": prompt,
                "expected_answer": expected,
                "model_answer": answer,
                "similarity": sim,
                "passed": passed,
                "latency_s": round(latency, 2),
                "sources": [
                    f"{s['metadata'].get('source', '?')} – chunk {s['metadata'].get('chunk_index', '?')}, page {s['metadata'].get('page', '?')}"
                    for s in rag_out.get("sources", [])
                ],
            })

        except Exception as e:
            results.append({
                "prompt": prompt,
                "expected_answer": expected,
                "model_answer": f"[ERROR] {e}",
                "similarity": None,
                "passed": False,
                "latency_s": 0,
                "sources": [],
            })

    return results


# -----------------------------------------------------------------------
# Render
# -----------------------------------------------------------------------

def render():
    st.title("Prompt Dataset Evaluation")
    st.caption("Upload a CSV or JSON dataset to run batch RAG evaluation across all prompts.")
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    # --- Upload ---
    st.subheader("Upload Dataset")
    st.markdown(
        "File must have a **`prompt`** column/key and optionally **`expected_answer`**.\n\n"
        "```\nprompt,expected_answer\n"
        "What is RAG?,Retrieval Augmented Generation\n"
        "What is TrustLLM?,AI evaluation platform\n```"
    )

    uploaded = st.file_uploader("Upload dataset", type=["csv", "json"],
                                label_visibility="collapsed")

    cc1, cc2 = st.columns([2, 1])
    with cc1:
        model = st.selectbox("Model", AVAILABLE_MODELS, key="ds_model")
    with cc2:
        top_k = st.slider("Context chunks (top-k)", 1, 4, 2, key="ds_top_k")

    run_btn = st.button("▶ Run Batch Evaluation", type="primary",
                        disabled=not uploaded)

    if run_btn and uploaded:
        try:
            dataset = _parse_dataset(uploaded)
        except Exception as e:
            st.error(f"Parse error: {e}")
            return

        st.info(f"Running **{len(dataset)}** prompts on **{model}** …")
        progress = st.progress(0)
        results_accum = []

        for i, row in enumerate(dataset):
            row_result = _run_batch([row], model, top_k)
            results_accum.extend(row_result)
            progress.progress((i + 1) / len(dataset))

        # Persist
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(REPORT_PATH, "w") as f:
            json.dump(results_accum, f, indent=2)

        st.session_state["batch_results"] = results_accum
        # Set session state for leaderboard tracking
        st.session_state["current_dataset_name"] = uploaded.name.replace("." + uploaded.name.split(".")[-1], "")
        st.session_state["current_model"] = model
        st.success(f"Evaluation complete — {len(results_accum)} prompts processed.")

    # --- Load stored results if available ---
    if "batch_results" not in st.session_state and REPORT_PATH.exists():
        with open(REPORT_PATH) as f:
            st.session_state["batch_results"] = json.load(f)

    results = st.session_state.get("batch_results")
    if not results:
        return

    # --- Summary metrics ---
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("Results Summary")

    scored   = [r for r in results if r["similarity"] is not None]
    passed   = [r for r in results if r["passed"]]
    avg_sim  = round(sum(r["similarity"] for r in scored) / len(scored), 4) if scored else 0
    pass_rate = round(len(passed) / len(results), 4) if results else 0
    hall_rate = round(1 - avg_sim, 4) if avg_sim else 0
    avg_lat   = round(sum(r["latency_s"] for r in results) / len(results), 2) if results else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Accuracy",    f"{pass_rate:.0%} ({len(passed)} / {len(results)} prompts passed)")
    m2.metric("📐 Avg Similarity",      f"{avg_sim:.2%}",  "vs expected answers")
    m3.metric("🚨 Hallucination Rate",  f"{hall_rate:.0%}", "estimated")
    m4.metric("⏱ Avg Latency",          f"{avg_lat:.1f}s", "per prompt")

    # --- Prepare raw dataframe (needed for both sorting and export) ---
    import pandas as pd
    df_raw = pd.DataFrame([
        {
            "_prompt_full": r["prompt"],
            "_expected_full": r["expected_answer"],
            "_answer_full": r["model_answer"],
            "_passed": r["passed"],
            "Prompt":       r["prompt"][:80],
            "Expected":     r["expected_answer"][:60] or "—",
            "Model Answer": r["model_answer"][:80],
            "Similarity":   r["similarity"] if r["similarity"] is not None else 0.0,
            "_sim_fmt":     f"{r['similarity']:.2%}" if r["similarity"] is not None else "—",
            "Pass":         "✅" if r["passed"] else "❌",
            "Latency (s)":  r["latency_s"],
        }
        for r in results
    ])

    # --- Export Evaluation Report ---
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("Export Evaluation Report")
    st.caption("Download this evaluation in CSV, JSON, or PDF format.")

    dataset_name = st.session_state.get("current_dataset_name", "rag_eval")
    model_name = st.session_state.get("current_model", "unknown")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from export_report import export_csv, export_json, export_pdf

    e1, e2, e3 = st.columns(3)
    with e1:
        export_csv(results, df_raw, dataset_name, timestamp)
    with e2:
        export_json(results, model_name, dataset_name, timestamp, pass_rate, hall_rate, avg_sim, avg_lat)
    with e3:
        export_pdf(results, model_name, dataset_name, timestamp, pass_rate, hall_rate, avg_sim, avg_lat, len(results))
    
    # --- Per-row table ---
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("Per-Prompt Results")

    # Sort options
    sc1, sc2 = st.columns([1, 1])
    with sc1:
        sort_by = st.selectbox(
            "Sort by",
            ["Score (Similarity)", "Latency", "Failure Severity"]
        )
    with sc2:
        sort_order = st.radio(
            "Order",
            ["Descending", "Ascending"],
            horizontal=True,
            label_visibility="collapsed"
        )

    # Apply sorting
    if sort_by == "Score (Similarity)":
        df_raw = df_raw.sort_values("Similarity", ascending=(sort_order == "Ascending"))
    elif sort_by == "Latency":
        df_raw = df_raw.sort_values("Latency (s)", ascending=(sort_order == "Ascending"))
    elif sort_by == "Failure Severity":
        # Failures first (passed=False), then by similarity ascending (worst first)
        df_raw = df_raw.sort_values(
            ["_passed", "Similarity"],
            ascending=[True, (sort_order == "Ascending")]
        )

    # Build display dataframe with formatted similarity
    df_display = df_raw[["Prompt", "Expected", "Model Answer", "_sim_fmt", "Pass", "Latency (s)"]].copy()
    df_display.columns = ["Prompt", "Expected", "Model Answer", "Similarity", "Pass", "Latency (s)"]

    # Highlight failed rows with slightly red background using pandas Styler
    def _highlight_failures(row):
        return ["background-color: #3b0f0f" if row["Pass"] == "❌" else "" for _ in row]

    st.dataframe(df_display.style.apply(_highlight_failures, axis=1), use_container_width=True)

    if st.button("🗑 Clear Results"):
        del st.session_state["batch_results"]
        if REPORT_PATH.exists():
            REPORT_PATH.unlink()
        st.rerun()
