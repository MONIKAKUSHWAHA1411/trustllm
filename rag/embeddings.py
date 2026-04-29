"""
rag/embeddings.py — TrustLLM RAG Module
=========================================
Provides a shared embedding function backed by ChromaDB's built-in
ONNX runtime (all-MiniLM-L6-v2).  No torch/GPU required.

The function is instantiated once and cached so it is not reloaded on
every call (lazy singleton pattern).
"""

import chromadb.utils.embedding_functions as ef

_embedding_fn = None


def get_embedding_function():
    """
    Return a ChromaDB-compatible embedding function.

    Uses the default ``all-MiniLM-L6-v2`` model via ONNX runtime —
    lightweight, CPU-friendly, no PyTorch dependency.
    """
    global _embedding_fn
    if _embedding_fn is None:
        _embedding_fn = ef.DefaultEmbeddingFunction()
    return _embedding_fn


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Embed a list of strings and return a list of float vectors.

    Useful for standalone cosine-similarity evaluation without needing
    the full ChromaDB collection.
    """
    fn = get_embedding_function()
    return fn(texts)
