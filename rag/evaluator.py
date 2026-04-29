"""
rag/evaluator.py — TrustLLM RAG Module
=========================================
Computes three evaluation metrics for a RAG response using
cosine similarity on embeddings.  No external judge LLM needed.

Metrics
-------
context_relevance  : How relevant are the retrieved chunks to the query?
faithfulness       : Is the answer grounded in the retrieved context?
hallucination_risk : Estimated probability the answer contains hallucinations
                     (1 - faithfulness).
"""

import numpy as np

from .embeddings import embed_texts


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two embedding vectors."""
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    norm_a = np.linalg.norm(va)
    norm_b = np.linalg.norm(vb)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(va, vb) / (norm_a * norm_b))


def _mean_similarity(query_vec: list[float], doc_vecs: list[list[float]]) -> float:
    """Return the average cosine similarity of a query against a list of docs."""
    if not doc_vecs:
        return 0.0
    sims = [_cosine_similarity(query_vec, dv) for dv in doc_vecs]
    return round(float(np.mean(sims)), 4)


# -----------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------

def evaluate_rag(
    query: str,
    answer: str,
    context_docs: list[dict],
) -> dict:
    """
    Evaluate the quality of a RAG response.

    Parameters
    ----------
    query        : the original user question
    answer       : the LLM-generated answer
    context_docs : list of dicts returned by ``retrieve_documents``
                   (each must have a ``"text"`` key)

    Returns
    -------
    dict
        context_relevance  – float [0, 1]  higher = more relevant chunks
        faithfulness       – float [0, 1]  higher = answer stays on context
        hallucination_risk – float [0, 1]  lower = safer response
    """
    if not context_docs:
        return {
            "context_relevance": 0.0,
            "faithfulness": 0.0,
            "hallucination_risk": 1.0,
        }

    doc_texts = [d["text"] for d in context_docs]

    # Embed everything in one batch for efficiency
    all_texts = [query, answer] + doc_texts
    all_vecs = embed_texts(all_texts)

    query_vec = all_vecs[0]
    answer_vec = all_vecs[1]
    doc_vecs = all_vecs[2:]

    # --- Context Relevance ---
    # Average similarity between the query and each retrieved chunk
    context_relevance = _mean_similarity(query_vec, doc_vecs)

    # --- Faithfulness ---
    # Average similarity between the answer and each retrieved chunk.
    # A high score means the answer language closely mirrors the context,
    # indicating it is grounded rather than fabricated.
    faithfulness = _mean_similarity(answer_vec, doc_vecs)

    # Clamp to [0, 1] — cosine can technically be negative for dissimilar vectors
    context_relevance = max(0.0, min(1.0, context_relevance))
    faithfulness = max(0.0, min(1.0, faithfulness))
    hallucination_risk = round(1.0 - faithfulness, 4)

    return {
        "context_relevance": context_relevance,
        "faithfulness": faithfulness,
        "hallucination_risk": hallucination_risk,
    }
