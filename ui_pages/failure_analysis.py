"""
ui_pages/failure_analysis.py — TrustLLM Failure Analysis
==========================================================
Shows all prompts where the RAG model failed (similarity below threshold),
with Query / Expected / Model Answer / Failure Reason.

Reads from reports/batch_eval_results.json produced by prompt_dataset.py.
"""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

BASE_DIR    = Path(__file__).resolve().parents[1]
PASS_THRESHOLD = 0.55   # must match prompt_dataset.py


def _report_path() -> Path:
    """Return the per-user batch eval report path."""
    user_id = st.session_state.get("user", {}).get("id", "default")
    safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in user_id)
    return BASE_DIR / "reports" / safe_id / "batch_eval_results.json"


# -----------------------------------------------------------------------
# Failure reason / severity / explanation
# -----------------------------------------------------------------------

def _failure_reason(row: dict) -> str:
    sim = row.get("similarity")
    answer = row.get("model_answer", "").lower()

    if "[error]" in answer:
        return "Pipeline error"
    if "not have enough information" in answer or "insufficient context" in answer:
        return "No answer / insufficient context"
    if sim is None:
        return "No expected answer provided"
    if sim < 0.25:
        return "Semantic mismatch — answer unrelated to expected"
    if sim < 0.40:
        return "Low similarity — partially incorrect answer"
    if sim < PASS_THRESHOLD:
        return "Borderline — answer close but below threshold"
    return "—"


def _failure_severity(row: dict):
    """
    Return (emoji, label) severity for a failed row.
    🔴 Critical  — hallucinated / completely wrong answer
    🟡 Medium    — borderline or partially correct
    🟢 Low       — safe fallback (no answer / retrieval miss)
    """
    sim = row.get("similarity")
    answer = row.get("model_answer", "").lower()

    if "not have enough information" in answer or "insufficient context" in answer:
        return "🟢", "Low"
    if sim is None or sim < 0.25:
        return "🔴", "Critical"
    if sim < 0.40:
        return "🔴", "Critical"
    return "🟡", "Medium"


_SEVERITY_ORDER = {"🔴 Critical": 0, "🟡 Medium": 1, "🟢 Low": 2}


# -----------------------------------------------------------------------
# Source rendering — chunk text preview + per-file PDF download
# -----------------------------------------------------------------------

def _normalise_source(src):
    """
    Accept either the old stringified format (`"file.pdf – chunk 4, page 2"`)
    or the new dict format with full chunk text. Always return a dict.
    """
    if isinstance(src, dict):
        return {
            "source":      src.get("source", "unknown"),
            "page":        src.get("page", "?"),
            "chunk_index": src.get("chunk_index", "?"),
            "score":       src.get("score"),
            "text":        src.get("text", ""),
        }
    # Legacy stringified format — extract source name only.
    txt = str(src)
    fname = txt.split("–")[0].strip() if "–" in txt else txt
    return {"source": fname, "page": "?", "chunk_index": "?", "score": None, "text": ""}


def _render_sources(sources, key_prefix: str = ""):
    """
    Per-source UI — renders as styled containers (NOT expanders) to avoid
    Streamlit's nested-expander restriction when called inside a parent expander.
    """
    from rag.ingestion import get_source_pdf_path

    seen_files = set()

    for j, raw in enumerate(sources, 1):
        s = _normalise_source(raw)
        fname  = s["source"]
        page   = s["page"]
        chunk  = s["chunk_index"]
        score  = s["score"]
        text   = s["text"]

        score_badge = ""
        if isinstance(score, (int, float)):
            score_badge = (
                "🟢" if score > 0.7 else ("🟡" if score > 0.4 else "🔴")
            ) + f" {score:.3f}"

        # Styled source card (no expander — avoids nesting violation)
        st.markdown(
            f"<div style='background:#1e293b;border:1px solid #334155;"
            f"border-radius:8px;padding:0.6rem 0.9rem;margin-bottom:0.5rem;'>"
            f"<div style='font-size:0.82rem;color:#94a3b8;font-weight:600;'>"
            f"📄 {fname} · Chunk {chunk} · Page {page}"
            f"{(' · ' + score_badge) if score_badge else ''}</div>"
            + (
                f"<div style='margin-top:0.4rem;font-size:0.8rem;color:#e2e8f0;"
                f"line-height:1.55;white-space:pre-wrap;max-height:120px;"
                f"overflow-y:auto;'>{text}</div>"
                if text else
                "<div style='margin-top:0.3rem;font-size:0.78rem;color:#64748b;'>"
                "Chunk text not stored — re-run evaluation to capture.</div>"
            )
            + "</div>",
            unsafe_allow_html=True,
        )

        # Download button for the original PDF (one per filename)
        if fname not in seen_files:
            seen_files.add(fname)
            pdf_path = get_source_pdf_path(fname)
            if pdf_path.exists():
                with open(pdf_path, "rb") as fh:
                    st.download_button(
                        label=f"⬇ Download {fname}",
                        data=fh.read(),
                        file_name=fname,
                        mime="application/pdf",
                        key=f"{key_prefix}_dl_{j}_{fname}",
                        use_container_width=False,
                    )


def _why_failed(row: dict) -> str:
    """
    Generate a concise one-line explanation of why the answer failed.
    Rule-based: compares similarity, answer content, and expected answer.
    """
    sim = row.get("similarity")
    answer = row.get("model_answer", "").lower()
    expected = row.get("expected_answer", "")

    if "[error]" in answer:
        return "A pipeline or runtime error prevented the model from generating a response."
    if "not have enough information" in answer or "insufficient context" in answer:
        return "The retrieved documents did not contain relevant context — this is a retrieval gap, not a hallucination."
    if sim is None:
        return "No expected answer was provided so similarity could not be computed."
    if sim < 0.25:
        expected_words = set(expected.lower().split())
        answer_words = set(row.get("model_answer", "").lower().split())
        overlap = expected_words & answer_words
        if not overlap:
            return "Answer shares no key terms with the expected response — likely off-topic or hallucinated."
        return f"Answer is semantically unrelated to expected (similarity {sim:.0%}) — likely incorrect facts."
    if sim < 0.40:
        return f"Answer partially addresses the question (similarity {sim:.0%}) but is missing key information from the expected answer."
    return f"Answer is close to expected (similarity {sim:.0%}) but fell just below the passing threshold — consider rephrasing the query or adjusting top-k."


# -----------------------------------------------------------------------
# Render
# -----------------------------------------------------------------------

def render():
    st.title("Failure Analysis")
    st.caption(
        "Cases where the model produced answers that diverged from expected. "
        "Run a dataset evaluation first via **Prompt Dataset** to populate this view."
    )
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    # Load results (user-specific file, evict if owned by a different user)
    rp = _report_path()
    current_uid = st.session_state.get("user", {}).get("id", "default")
    if st.session_state.get("batch_results_owner") != current_uid:
        st.session_state.pop("batch_results", None)
        st.session_state.pop("batch_results_owner", None)
    results = st.session_state.get("batch_results")
    if results is None and rp.exists():
        with open(rp) as f:
            results = json.load(f)
        st.session_state["batch_results"] = results
        st.session_state["batch_results_owner"] = current_uid

    if not results:
        st.info(
            "No batch evaluation results found. "
            "Go to **Prompt Dataset** and run an evaluation first."
        )
        return

    failures = [r for r in results if not r["passed"]]
    passes   = [r for r in results if r["passed"]]

    # --- Summary bar ---
    total = len(results)
    col1, col2, col3 = st.columns(3)
    col1.metric("❌ Failures",   len(failures), f"{len(failures)/total:.0%} of dataset")
    col2.metric("✅ Passed",     len(passes),   f"{len(passes)/total:.0%} of dataset")
    col3.metric("📋 Total Prompts", total)

    if not failures:
        st.success("🎉 No failures detected — all prompts passed!")
        return

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Pre-calculate failure reason counts for filter dropdown ---
    reason_counts = {}
    for r in failures:
        reason = _failure_reason(r)
        reason_counts[reason] = reason_counts.get(reason, 0) + 1

    # --- Sort and filter controls ---
    st.subheader("Sort & Filter")
    sf1, sf2, sf3 = st.columns([2, 2, 1])
    with sf1:
        sort_by = st.selectbox(
            "Sort by",
            ["Failure Severity", "Score (Similarity)", "Latency"],
            key="fa_sort",
        )
    with sf2:
        sort_order = st.radio(
            "Order",
            ["Descending", "Ascending"],
            horizontal=True,
            label_visibility="collapsed",
            key="fa_order",
        )
    with sf3:
        reason_filter = st.selectbox(
            "Filter by reason",
            ["All"] + sorted(reason_counts.keys()),
            key="fa_reason_filter",
        )

    sc1 = st.columns(1)
    with sc1[0]:
        search = st.text_input("Filter by keyword", placeholder="Search query text …",
                               key="fa_search")

    # Apply filters
    filtered = failures
    if search.strip():
        filtered = [r for r in filtered if search.lower() in r["prompt"].lower()]
    if reason_filter != "All":
        filtered = [r for r in filtered if _failure_reason(r) == reason_filter]

    # Apply sorting
    if sort_by == "Failure Severity":
        filtered = sorted(
            filtered,
            key=lambda r: _SEVERITY_ORDER.get(
                f"{_failure_severity(r)[0]} {_failure_severity(r)[1]}", 99
            ),
            reverse=(sort_order == "Descending"),
        )
    elif sort_by == "Score (Similarity)":
        filtered = sorted(filtered, key=lambda r: r.get("similarity", 0),
                         reverse=(sort_order == "Descending"))
    elif sort_by == "Latency":
        filtered = sorted(filtered, key=lambda r: r.get("latency_s", 0),
                         reverse=(sort_order == "Descending"))

    st.caption(f"Showing {len(filtered)} of {len(failures)} failures")

    # --- Failure reason breakdown ---
    st.subheader("Failure Reason Breakdown")
    reason_df = pd.DataFrame(
        [{"Failure Reason": k, "Count": v} for k, v in
         sorted(reason_counts.items(), key=lambda x: -x[1])]
    )
    st.dataframe(reason_df, use_container_width=True, hide_index=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Per-failure detail ---
    st.subheader("Failure Details")

    for i, row in enumerate(filtered, 1):
        sim = row.get("similarity")
        reason = _failure_reason(row)
        sim_str = f"{sim:.2%}" if sim is not None else "N/A"

        with st.expander(
            f"❌ #{i} — {row['prompt'][:70]}{'…' if len(row['prompt']) > 70 else ''}",
            expanded=(i <= 3),
        ):
            q1, q2 = st.columns(2)

            with q1:
                st.markdown("**Query**")
                st.info(row["prompt"])

                st.markdown("**Expected Answer**")
                st.success(row["expected_answer"] or "*(not provided)*")

            with q2:
                st.markdown("**Model Answer**")
                st.error(row["model_answer"][:500])

                st.markdown("**Failure Reason**")
                st.warning(f"⚠️ {reason}")

            st.caption(
                f"Similarity: `{sim_str}` &nbsp;·&nbsp; "
                f"Latency: `{row.get('latency_s', 0):.2f}s`"
            )

            # View Sources — chunks + downloadable PDFs
            sources = row.get('sources', [])
            if sources:
                st.markdown("**Retrieved Sources**")
                _render_sources(sources, key_prefix=f"fa_{i}")
            else:
                st.caption("No sources available")
