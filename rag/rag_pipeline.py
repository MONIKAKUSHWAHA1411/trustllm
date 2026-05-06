"""
rag/rag_pipeline.py — TrustLLM RAG Module
==========================================
Combines document retrieval (ChromaDB) with local LLM generation
(Ollama) to answer user queries grounded in uploaded documents.

Pipeline:
    User Query → Retriever (ChromaDB) → Top-K chunks
               → Prompt assembly → Ollama LLM → Answer

Cloud deployments: set `OLLAMA_HOST` (e.g. via Streamlit secrets) to a
reachable Ollama endpoint such as an ngrok tunnel pointing at a local
Ollama instance — `https://<your-tunnel>.ngrok-free.app`. If unset, the
pipeline falls back to `http://localhost:11434` and surfaces a clear
"LLM backend unreachable" error when the connection fails.
"""

import os
import time

import ollama

from .retriever import retrieve_documents, TOP_K

# Default model — must be available via `ollama list`
DEFAULT_MODEL = "mistral"


def _get_ollama_client():
    """
    Build an Ollama client using OLLAMA_HOST from Streamlit secrets or env.
    Falls back to the package default (http://localhost:11434).
    """
    host = None
    try:
        import streamlit as st
        host = st.secrets.get("OLLAMA_HOST", os.getenv("OLLAMA_HOST"))
    except Exception:
        host = os.getenv("OLLAMA_HOST")

    if host:
        return ollama.Client(host=host)
    return ollama  # module-level functions hit localhost by default


def _is_connection_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(
        kw in msg
        for kw in ("connection refused", "connecterror", "max retries",
                   "name or service not known", "connection error",
                   "failed to establish", "could not connect")
    )

PROMPT_TEMPLATE = """\
You are a helpful assistant. Answer the question below using ONLY the
context provided. If the context does not contain enough information,
say "I don't have enough information in the provided documents."

--- CONTEXT ---
{context}
--- END CONTEXT ---

Question: {question}

Answer:"""


def run_rag_query(
    query: str,
    model: str = DEFAULT_MODEL,
    top_k: int = TOP_K,
) -> dict:
    """
    Run a full RAG query: retrieve relevant chunks then generate an answer.

    Parameters
    ----------
    query   : user question
    model   : Ollama model name (must be pulled locally)
    top_k   : number of context chunks to retrieve

    Returns
    -------
    dict
        answer  – str, LLM-generated answer
        sources – list of source dicts from the retriever
        model   – str, model used
    """
    t_start = time.perf_counter()

    # --- 1. Retrieve ---
    t_ret = time.perf_counter()
    source_docs = retrieve_documents(query, top_k=top_k)
    retrieval_time = round(time.perf_counter() - t_ret, 3)

    if not source_docs:
        return {
            "answer": "No documents found in the knowledge base. Please upload documents first.",
            "sources": [],
            "model": model,
            "latency": {"retrieval_time": retrieval_time, "generation_time": 0,
                        "total_time": retrieval_time, "estimated_tokens": 0,
                        "context_chunks": 0},
        }

    # --- 2. Assemble prompt ---
    context_blocks = []
    for i, doc in enumerate(source_docs, 1):
        src = doc["metadata"].get("source", "unknown")
        page = doc["metadata"].get("page", "?")
        context_blocks.append(
            f"[{i}] (Source: {src}, Page: {page})\n{doc['text']}"
        )
    context = "\n\n".join(context_blocks)
    prompt = PROMPT_TEMPLATE.format(context=context, question=query)

    # --- 3. Generate via Ollama ---
    t_gen = time.perf_counter()
    try:
        client = _get_ollama_client()
        response = client.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        answer = response["message"]["content"].strip()
    except Exception as exc:
        if _is_connection_error(exc):
            answer = (
                "**LLM backend unreachable.**\n\n"
                "The RAG retrieval succeeded — the relevant document chunks are "
                "shown in the *Sources* section below — but no Ollama server "
                "is reachable to generate an answer.\n\n"
                "**On Streamlit Cloud**: Ollama runs locally on your machine, "
                "not on Streamlit's servers. To use the chat tab, expose your "
                "local Ollama via a tunnel (e.g. `ngrok http 11434`) and add "
                "the tunnel URL to your app secrets as:\n\n"
                "```toml\nOLLAMA_HOST = \"https://your-tunnel.ngrok-free.app\"\n```\n"
                "Then reboot the app.\n\n"
                "**Locally**: make sure `ollama serve` is running and the "
                f"selected model (`{model}`) has been pulled via `ollama pull {model}`."
            )
        else:
            answer = f"[Ollama error] {exc}"
    generation_time = round(time.perf_counter() - t_gen, 3)
    total_time = round(time.perf_counter() - t_start, 3)

    # Rough token estimate: ~0.75 words per token (GPT-style)
    estimated_tokens = max(1, int(len(answer.split()) / 0.75))

    return {
        "answer": answer,
        "sources": source_docs,
        "model": model,
        "latency": {
            "retrieval_time": retrieval_time,
            "generation_time": generation_time,
            "total_time": total_time,
            "estimated_tokens": estimated_tokens,
            "context_chunks": len(source_docs),
        },
    }
