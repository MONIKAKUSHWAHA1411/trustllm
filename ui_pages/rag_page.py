"""
ui_pages/rag_page.py — TrustLLM RAG Testing Page
==================================================
Four-tab Streamlit page:
    1. Document Upload    — ingest PDFs into ChromaDB
    2. RAG Chat           — query + highlighted sources + latency
    3. Evaluation         — confidence score, latency metrics, warning banner
    4. Retrieval Debugger — collapsible chunk viewer

Extra: query history in sidebar, low-confidence warning.
"""

import sys
import tempfile
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

# Available Ollama models — phi3:mini and mistral:instruct for faster demos
AVAILABLE_MODELS = ["phi3:mini", "mistral:instruct", "phi3", "phi", "mistral"]
DEFAULT_TOP_K    = 2   # keep context window small for speed

# Confidence tiers
CONFIDENCE_HIGH = 0.70   # ≥ this → 🟢 High
CONFIDENCE_MED  = 0.40   # ≥ this → 🟡 Medium  (below → 🔴 Low)


def _confidence_score(faithfulness: float, context_relevance: float, hallucination_risk: float) -> float:
    """Composite TrustLLM confidence score."""
    return round(
        0.4 * faithfulness +
        0.4 * context_relevance +
        0.2 * (1.0 - hallucination_risk),
        4,
    )


def _confidence_tier(score: float) -> tuple[str, str, str]:
    """Return (colour_hex, emoji_label, text_label) for a confidence score."""
    if score >= CONFIDENCE_HIGH:
        return "#22c55e", "🟢", "High Confidence"
    if score >= CONFIDENCE_MED:
        return "#f59e0b", "🟡", "Medium Confidence"
    return "#ef4444", "🔴", "Low Confidence"


def _highlight_keywords(text: str, query: str) -> str:
    """Wrap query keywords (>3 chars) in a yellow highlight span."""
    import re
    keywords = {w.lower() for w in query.split() if len(w) > 3}
    for kw in sorted(keywords, key=len, reverse=True):  # longest first
        text = re.sub(
            r'(?i)(\b' + re.escape(kw) + r'\b)',
            r'<mark style="background:#fef08a;color:#1e293b;border-radius:3px;'
            r'padding:0 2px;font-weight:600;">\1</mark>',
            text,
        )
    return text


def _copy_button(text: str):
    """Render a JS clipboard copy button."""
    import json
    import streamlit.components.v1 as components
    escaped = json.dumps(text)
    components.html(
        f"""
        <button
          onclick="navigator.clipboard.writeText({escaped});
                   this.textContent='✓ Copied!';
                   setTimeout(()=>this.textContent='📋 Copy Response',2000);"
          style="background:#334155;color:#e2e8f0;border:1px solid #475569;
                 padding:6px 18px;border-radius:6px;cursor:pointer;
                 font-size:13px;font-family:sans-serif;">
          📋 Copy Response
        </button>
        """,
        height=44,
    )


def _push_query_history(query: str):
    """Append a query to session-state history (max 10)."""
    history = st.session_state.setdefault("rag_query_history", [])
    if not history or history[-1] != query:
        history.append(query)
    st.session_state["rag_query_history"] = history[-10:]  # keep last 10


def _render_query_history():
    """Render query history in the sidebar."""
    history = st.session_state.get("rag_query_history", [])
    if not history:
        return
    st.sidebar.divider()
    st.sidebar.markdown("**🕘 Recent RAG Queries**")
    for q in reversed(history):
        st.sidebar.caption(f"• {q[:55]}{'…' if len(q) > 55 else ''}")


# -----------------------------------------------------------------------
# Tab 1 — Document Upload
# -----------------------------------------------------------------------
def _tab_upload():
    st.subheader("Upload Knowledge Base")
    st.caption("Upload one or more PDF files. They will be chunked and indexed into the vector database.")

    uploaded = st.file_uploader(
        "Upload Knowledge Base",
        type=["pdf"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    col_btn, col_info = st.columns([1, 3])
    with col_btn:
        run_index = st.button("⚡ Index Documents", type="primary", disabled=not uploaded)

    if run_index and uploaded:
        from rag.ingestion import ingest_documents

        total_chunks = 0
        progress = st.progress(0)
        status = st.empty()

        for i, f in enumerate(uploaded):
            status.info(f"Indexing **{f.name}** …")
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(f.read())
                tmp_path = tmp.name

            try:
                result = ingest_documents(tmp_path)
                total_chunks += result["chunks_created"]
                st.toast(f"✓ {f.name} — {result['chunks_created']} chunks", icon="✅")
            except Exception as e:
                st.error(f"Error indexing {f.name}: {e}")

            progress.progress((i + 1) / len(uploaded))

        status.empty()
        st.success(
            f"**Documents indexed successfully!**  "
            f"Chunks created: **{total_chunks}** from {len(uploaded)} file(s)"
        )
        st.session_state["rag_indexed"] = True

    # Show current collection stats
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("Vector Store Status")
    try:
        import chromadb
        from rag.ingestion import VECTOR_DB_PATH, DEFAULT_COLLECTION
        from rag.embeddings import get_embedding_function

        client = chromadb.PersistentClient(path=VECTOR_DB_PATH)
        existing = [c.name for c in client.list_collections()]

        if DEFAULT_COLLECTION in existing:
            col = client.get_collection(
                name=DEFAULT_COLLECTION,
                embedding_function=get_embedding_function(),
            )
            count = col.count()
            st.success(f"Collection **{DEFAULT_COLLECTION}** · **{count}** chunks indexed")

            # Show unique sources
            if count > 0:
                sample = col.get(limit=count, include=["metadatas"])
                sources = sorted({m.get("source", "unknown") for m in sample["metadatas"]})
                st.markdown("**Indexed files:**")
                for s in sources:
                    st.markdown(f"- 📄 `{s}`")

            if st.button("🗑 Clear Vector Store"):
                client.delete_collection(DEFAULT_COLLECTION)
                st.warning("Vector store cleared.")
                st.rerun()
        else:
            st.info("No documents indexed yet. Upload PDFs above to get started.")
    except Exception as e:
        st.error(f"Could not read vector store: {e}")


# -----------------------------------------------------------------------
# Tab 2 — RAG Chat
# -----------------------------------------------------------------------
def _render_sources(sources: list, query: str = ""):
    """Render a numbered, expandable source panel with keyword highlighting."""
    st.markdown("---")
    st.markdown("**Sources Used**")
    nums = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣"]
    for i, src in enumerate(sources, 1):
        meta  = src["metadata"]
        fname = meta.get("source", "unknown")
        chunk_idx = meta.get("chunk_index", "?")
        page  = meta.get("page", "?")
        score = src["score"]
        score_badge = "🟢" if score > 0.7 else ("🟡" if score > 0.4 else "🔴")
        num = nums[i - 1] if i <= len(nums) else f"{i}."
        label = (
            f"{num} &nbsp; `{fname}` &nbsp;·&nbsp; "
            f"**Rank #{i}** &nbsp;·&nbsp; Chunk {chunk_idx} &nbsp;·&nbsp; "
            f"Page {page} &nbsp;·&nbsp; {score_badge} `{score:.3f}`"
        )
        with st.expander(f"Rank #{i} · {fname} (Chunk {chunk_idx}, Page {page}) · {score_badge} {score:.3f}"):
            highlighted = _highlight_keywords(src["text"], query) if query else src["text"]
            st.markdown(
                f"<div style='background:#1e293b;border-radius:6px;padding:0.75rem 1rem;"
                f"font-size:0.85rem;color:#e2e8f0;line-height:1.6;'>{highlighted}</div>",
                unsafe_allow_html=True,
            )


def _run_query(query: str, model: str, top_k: int):
    """Execute query, persist result to session state, and log to history DB."""
    from rag.rag_pipeline import run_rag_query
    result = run_rag_query(query, model=model, top_k=top_k)
    st.session_state["rag_last_result"] = result
    st.session_state["rag_last_query"]  = query
    st.session_state["rag_last_model"]  = model
    st.session_state["rag_last_top_k"]  = top_k
    _push_query_history(query)

    # Persist to SQLite history
    try:
        from db.database import save_query as _save_query
        user = st.session_state.get("user", {})
        user_id = user.get("id", "")
        if user_id:
            _save_query(user_id, "RAG Testing", query, result.get("answer", ""))
    except Exception:
        pass  # never block the UI on history write failure

    return result


def _tab_chat():
    st.subheader("RAG Chat Playground")
    st.caption("Ask questions about your uploaded documents. Answers are generated by a local Ollama model.")

    cc1, cc2 = st.columns([2, 1])
    with cc1:
        model = st.selectbox("Model", AVAILABLE_MODELS, key="rag_model",
                             help="phi3 / phi are fastest for demos (~3-10s). mistral is slower but more capable.")
    with cc2:
        top_k = st.slider("Context chunks (top-k)", 1, 5, DEFAULT_TOP_K, key="rag_top_k")

    # Pre-fill from history reload (set by query_history.py)
    _reload = st.session_state.pop("history_reload", None)
    _prefill = ""
    if _reload and _reload.get("page") == "RAG Testing":
        _prefill = _reload.get("query", "")
        if _reload.get("response"):
            st.info(f"Reloaded query from history. Previous response shown below.")
            with st.expander("Previous response"):
                st.markdown(_reload["response"])

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    query = st.text_area(
        "Ask a Question",
        value=_prefill,
        placeholder="e.g. What is the main topic of this document?",
        key="rag_query_input",
        height=90,
    )

    btn_col, regen_col, _ = st.columns([1, 1, 4])
    ask_clicked    = btn_col.button("🔍 Ask",       type="primary",
                                    disabled=not query.strip())
    regen_clicked  = regen_col.button("🔄 Regenerate",
                                      disabled="rag_last_query" not in st.session_state)

    result = None
    if ask_clicked and query.strip():
        with st.spinner(f"Running on **{model}** …"):
            try:
                result = _run_query(query.strip(), model, top_k)
            except RuntimeError as e:
                st.error(str(e)); return
            except Exception as e:
                st.error(f"Unexpected error: {e}"); return

    elif regen_clicked:
        prev_q  = st.session_state.get("rag_last_query", "")
        prev_m  = st.session_state.get("rag_last_model", model)
        prev_k  = st.session_state.get("rag_last_top_k",  top_k)
        with st.spinner(f"Regenerating on **{prev_m}** …"):
            try:
                result = _run_query(prev_q, prev_m, prev_k)
            except Exception as e:
                st.error(f"Regenerate error: {e}"); return

    # Render result (new or previously stored)
    if result is None and "rag_last_result" in st.session_state:
        result = st.session_state["rag_last_result"]
        st.info(f"Last query: *{st.session_state.get('rag_last_query', '')}*")

    if result:
        latency = result.get("latency", {})
        last_q  = st.session_state.get("rag_last_query", query)

        st.markdown("### Answer")
        st.markdown(result["answer"])
        _copy_button(result["answer"])

        if result["sources"]:
            _render_sources(result["sources"], query=last_q)

        st.markdown("---")
        lc1, lc2, lc3 = st.columns(3)
        lc1.metric("⏱ Total Latency",   f"{latency.get('total_time', 0):.2f}s")
        lc2.metric("🔍 Retrieval Time", f"{latency.get('retrieval_time', 0):.2f}s")
        lc3.metric("🪙 Est. Tokens",    latency.get('estimated_tokens', '—'))


# -----------------------------------------------------------------------
# Tab 3 — Evaluation
# -----------------------------------------------------------------------
def _tab_evaluation():
    st.subheader("RAG Evaluation Dashboard")
    st.caption("TrustLLM evaluation metrics for the last RAG response.")

    if "rag_last_result" not in st.session_state:
        st.info("Run a query in the **RAG Chat** tab first to see evaluation metrics.")
        return

    result = st.session_state["rag_last_result"]
    query  = st.session_state.get("rag_last_query", "")

    with st.spinner("Computing evaluation metrics …"):
        try:
            from rag.evaluator import evaluate_rag
            metrics = evaluate_rag(query, result["answer"], result["sources"])
        except Exception as e:
            st.error(f"Evaluation error: {e}")
            return

    cr = metrics["context_relevance"]
    fa = metrics["faithfulness"]
    hr = metrics["hallucination_risk"]
    confidence = _confidence_score(fa, cr, hr)

    # --- Confidence score hero ---
    conf_color, conf_emoji, conf_label = _confidence_tier(confidence)

    st.markdown(
        f"""
        <div style="background:#1e293b;border-radius:10px;padding:1.2rem 1.5rem;
                    text-align:center;margin-bottom:1rem;">
            <div style="font-size:1rem;color:#94a3b8;margin-bottom:0.2rem;">
                TrustLLM Confidence Score
            </div>
            <div style="font-size:3rem;font-weight:800;color:{conf_color};">
                {confidence:.0%}
            </div>
            <div style="font-size:1.1rem;color:{conf_color};font-weight:600;margin-top:0.2rem;">
                {conf_emoji} {conf_label}
            </div>
            <div style="font-size:0.78rem;color:#64748b;margin-top:0.4rem;">
                0.4 × faithfulness + 0.4 × context relevance + 0.2 × (1 − hallucination)
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --- Warning banner ---
    if confidence < CONFIDENCE_MED:
        st.error(
            "🔴 **Low Confidence Response** — High hallucination risk detected. "
            "The answer is likely not grounded in the retrieved documents."
        )
    elif confidence < CONFIDENCE_HIGH:
        st.warning(
            "🟡 **Medium Confidence** — Some hallucination risk. "
            "Review the source chunks before trusting this answer."
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Individual metrics ---
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("🎯 Context Relevance", f"{cr:.2%}",
                  help="How relevant are retrieved chunks to the query?")
        st.progress(cr)
    with col2:
        st.metric("🔒 Faithfulness", f"{fa:.2%}",
                  help="Is the answer grounded in the retrieved context?")
        st.progress(fa)
    with col3:
        risk_color = "🟢" if hr < 0.2 else ("🟡" if hr < 0.5 else "🔴")
        st.metric(f"{risk_color} Hallucination Risk", f"{hr:.2%}",
                  help="Estimated probability of hallucination (lower = better)")
        st.progress(hr)

    # --- Latency metrics ---
    latency = result.get("latency", {})
    if latency:
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("Latency")
        lc1, lc2, lc3, lc4 = st.columns(4)
        lc1.metric("⏱ Response Time",   f"{latency.get('total_time', 0):.2f}s")
        lc2.metric("🔍 Retrieval Time",  f"{latency.get('retrieval_time', 0):.2f}s")
        lc3.metric("🤖 Generation Time", f"{latency.get('generation_time', 0):.2f}s")
        lc4.metric("🪙 Tokens Generated", latency.get('estimated_tokens', '—'))

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("**Evaluated query:**")
    st.info(query)
    st.markdown("**Generated answer:**")
    st.markdown(result["answer"])


# -----------------------------------------------------------------------
# Tab 4 — Retrieval Debugger
# -----------------------------------------------------------------------
def _tab_debugger():
    st.subheader("Retrieval Debugger")
    st.caption("Inspect exactly which document chunks are retrieved for a given query and their similarity scores.")

    debug_query = st.text_input(
        "Debug query",
        value=st.session_state.get("rag_last_query", ""),
        placeholder="Enter a query to inspect retrieved chunks …",
        key="rag_debug_query",
    )
    top_k_debug = st.slider("Top-k chunks to inspect", 1, 10, 5, key="rag_debug_top_k")

    if st.button("🔎 Retrieve Chunks", disabled=not debug_query.strip()):
        with st.spinner("Retrieving …"):
            try:
                from rag.retriever import retrieve_documents
                docs = retrieve_documents(debug_query, top_k=top_k_debug)
            except RuntimeError as e:
                st.error(str(e))
                return
            except Exception as e:
                st.error(f"Retrieval error: {e}")
                return

        if not docs:
            st.warning("No chunks retrieved.")
            return

        st.markdown(f"**Retrieved {len(docs)} chunks** for query: *{debug_query}*")
        st.markdown("---")

        for i, doc in enumerate(docs, 1):
            meta  = doc["metadata"]
            score = doc["score"]
            score_color = "🟢" if score > 0.7 else ("🟡" if score > 0.4 else "🔴")
            label = (
                f"{score_color} Chunk {i}  |  "
                f"`{meta.get('source', 'unknown')}`  ·  "
                f"Page {meta.get('page', '?')}  ·  "
                f"Score {score:.4f}"
            )
            with st.expander(label, expanded=(i == 1)):
                st.markdown(
                    f"<div style='background:#1e293b;border-radius:6px;"
                    f"padding:0.75rem 1rem;font-size:0.85rem;color:#e2e8f0;'>"
                    f"{doc['text']}"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                st.caption(
                    f"Chunk ID: `{doc['chunk_id']}` &nbsp;·&nbsp; "
                    f"Chunk index: `{meta.get('chunk_index', '?')}`"
                )


# -----------------------------------------------------------------------
# Main render
# -----------------------------------------------------------------------
def render():
    st.title("RAG Testing")
    st.caption("Build a vector knowledge base, query it with a local LLM, and evaluate response quality.")
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    # Query history in sidebar
    _render_query_history()

    tab1, tab2, tab3, tab4 = st.tabs([
        "📄 Document Upload",
        "💬 RAG Chat",
        "📊 Evaluation",
        "🔍 Retrieval Debugger",
    ])

    with tab1:
        _tab_upload()

    with tab2:
        _tab_chat()

    with tab3:
        _tab_evaluation()

    with tab4:
        _tab_debugger()
