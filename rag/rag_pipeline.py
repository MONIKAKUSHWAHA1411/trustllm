"""
rag/rag_pipeline.py — TrustLLM RAG Module
==========================================
Combines document retrieval (ChromaDB) with local LLM generation
(Ollama) to answer user queries grounded in uploaded documents.

Pipeline:
    User Query → Retriever (ChromaDB) → Top-K chunks
               → Prompt assembly → Ollama LLM → Answer
"""

import time

import ollama

from .retriever import retrieve_documents, TOP_K

# Default model — must be available via `ollama list`
DEFAULT_MODEL = "mistral"

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
        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        answer = response["message"]["content"].strip()
    except Exception as exc:
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
