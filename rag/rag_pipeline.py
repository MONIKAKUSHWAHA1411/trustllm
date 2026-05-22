"""
rag/rag_pipeline.py — TrustLLM RAG Module
==========================================
Combines document retrieval (ChromaDB) with cloud LLM generation
(Groq) to answer user queries grounded in uploaded documents.

Pipeline:
    User Query -> Retriever (ChromaDB) -> Top-K chunks
               -> Prompt assembly -> Groq LLM -> Answer

Set `GROQ_API_KEY` in Streamlit secrets (`.streamlit/secrets.toml`)
or as an environment variable. Free tier supports Llama 3 / Mixtral
models with generous rate limits — no local GPU needed.
"""

import os
import time

from .retriever import retrieve_documents, TOP_K

# Groq model IDs — free tier (production models, mixtral decommissioned 2025)
AVAILABLE_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
]
DEFAULT_MODEL = AVAILABLE_MODELS[0]


def _get_api_key() -> str:
    """Read GROQ_API_KEY from Streamlit secrets or environment."""
    try:
        import streamlit as st
        key = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY", ""))
    except Exception:
        key = os.getenv("GROQ_API_KEY", "")
    return key or ""


def _get_groq_client():
    """Build a Groq client. Raises RuntimeError when the key is missing."""
    api_key = _get_api_key()
    if not api_key:
        raise RuntimeError(
            "**GROQ_API_KEY not set.**\n\n"
            "Add it to your Streamlit secrets (`.streamlit/secrets.toml`):\n\n"
            "```toml\nGROQ_API_KEY = \"gsk_...\"\n```\n\n"
            "Get a free key at https://console.groq.com/keys"
        )
    from groq import Groq
    return Groq(api_key=api_key)


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
    model   : Groq model name
    top_k   : number of context chunks to retrieve

    Returns
    -------
    dict
        answer  - str, LLM-generated answer
        sources - list of source dicts from the retriever
        model   - str, model used
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

    # --- 3. Generate via Groq ---
    t_gen = time.perf_counter()
    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1024,
        )
        answer = response.choices[0].message.content.strip()
        token_usage = getattr(response, "usage", None)
        completion_tokens = token_usage.completion_tokens if token_usage else None
    except RuntimeError:
        # Missing API key — surface directly
        raise
    except Exception as exc:
        answer = f"[Groq error] {exc}"
        completion_tokens = None

    generation_time = round(time.perf_counter() - t_gen, 3)
    total_time = round(time.perf_counter() - t_start, 3)

    # Use actual token count from Groq when available
    if completion_tokens is not None:
        estimated_tokens = completion_tokens
    else:
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
