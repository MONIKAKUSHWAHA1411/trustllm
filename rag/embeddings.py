"""
rag/embeddings.py — TrustLLM RAG Module
=========================================
Provides ChromaDB-compatible embedding functions, selectable by a short
``model_key``.  Functions are instantiated once per key and cached so they
are not reloaded on every call (lazy registry pattern).

Available models
----------------
``minilm`` : default ``all-MiniLM-L6-v2`` via ChromaDB's ONNX runtime —
             lightweight, CPU-friendly, **no PyTorch dependency**.
``bge``    : ``BAAI/bge-small-en-v1.5`` via ``sentence-transformers`` —
             stronger retrieval, but pulls in torch.  Loaded lazily so the
             torch dependency is only required when BGE is actually selected.

The RAG Debugger uses this registry to compare embedding models side by side.
"""

from typing import Dict, List

import chromadb.utils.embedding_functions as ef

# Default key — preserves the original MiniLM/ONNX behaviour for all
# existing callers that invoke get_embedding_function() with no arguments.
DEFAULT_EMBEDDING = "minilm"

# Public metadata for the UI (display labels + one-line descriptions).
AVAILABLE_EMBEDDINGS: Dict[str, dict] = {
    "minilm": {
        "label": "MiniLM (all-MiniLM-L6-v2)",
        "note": "ONNX · 384-dim · fast · no torch",
    },
    "bge": {
        "label": "BGE (bge-small-en-v1.5)",
        "note": "sentence-transformers · 384-dim · stronger retrieval · needs torch",
    },
}

# Cache of instantiated embedding functions, keyed by model_key.
_embedding_fns: Dict[str, object] = {}


def _build_embedding_function(model_key: str):
    """Construct (but do not cache) the embedding function for ``model_key``."""
    if model_key == "minilm":
        # ChromaDB's bundled ONNX MiniLM — no torch required.
        return ef.DefaultEmbeddingFunction()

    if model_key == "bge":
        try:
            return ef.SentenceTransformerEmbeddingFunction(
                model_name="BAAI/bge-small-en-v1.5"
            )
        except Exception as exc:  # pragma: no cover - depends on optional dep
            raise RuntimeError(
                "The 'bge' embedding model requires `sentence-transformers`.\n"
                "Install it with:  pip install sentence-transformers\n"
                f"(underlying error: {exc})"
            ) from exc

    raise ValueError(
        f"Unknown embedding model '{model_key}'. "
        f"Available: {', '.join(AVAILABLE_EMBEDDINGS)}"
    )


def get_embedding_function(model_key: str = DEFAULT_EMBEDDING):
    """
    Return a ChromaDB-compatible embedding function for ``model_key``.

    The function is cached per key so repeated calls (and repeated queries
    against the same collection) reuse a single loaded model.
    """
    if model_key not in _embedding_fns:
        _embedding_fns[model_key] = _build_embedding_function(model_key)
    return _embedding_fns[model_key]


def embed_texts(texts: List[str], model_key: str = DEFAULT_EMBEDDING) -> List[List[float]]:
    """
    Embed a list of strings and return a list of float vectors.

    Useful for standalone cosine-similarity evaluation without needing
    the full ChromaDB collection.
    """
    fn = get_embedding_function(model_key)
    return fn(texts)
