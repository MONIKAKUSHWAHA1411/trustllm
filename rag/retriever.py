"""
rag/retriever.py — TrustLLM RAG Module
=========================================
Loads the persistent ChromaDB vector store and retrieves the most
relevant document chunks for a given query.
"""

from pathlib import Path

import chromadb

from .embeddings import get_embedding_function
from .ingestion import DEFAULT_COLLECTION, VECTOR_DB_PATH

TOP_K = 3


def load_vector_store(collection_name: str = DEFAULT_COLLECTION):
    """
    Return the ChromaDB collection object.

    Raises RuntimeError if the vector store has not been initialised yet
    (no documents ingested).
    """
    client = chromadb.PersistentClient(path=VECTOR_DB_PATH)
    existing = [c.name for c in client.list_collections()]
    if collection_name not in existing:
        raise RuntimeError(
            f"Collection '{collection_name}' not found. "
            "Please upload and index documents first."
        )
    return client.get_collection(
        name=collection_name,
        embedding_function=get_embedding_function(),
    )


def get_retriever(collection_name: str = DEFAULT_COLLECTION):
    """
    Return a callable retriever.

    The returned function accepts a query string and returns the top-K
    results from ``retrieve_documents``.
    """
    def retriever(query: str, top_k: int = TOP_K):
        return retrieve_documents(query, top_k=top_k, collection_name=collection_name)

    return retriever


def retrieve_documents(
    query: str,
    top_k: int = TOP_K,
    collection_name: str = DEFAULT_COLLECTION,
) -> list[dict]:
    """
    Query the vector store and return the top-k most relevant chunks.

    Parameters
    ----------
    query           : natural-language query string
    top_k           : number of chunks to return
    collection_name : ChromaDB collection to search

    Returns
    -------
    list of dicts, each containing:
        text       – str
        score      – float  (distance; lower = more similar)
        metadata   – dict   (source, page, chunk_index)
        chunk_id   – str
    """
    collection = load_vector_store(collection_name)

    results = collection.query(
        query_texts=[query],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    docs = []
    for text, meta, dist, chunk_id in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
        results["ids"][0],
    ):
        # ChromaDB distances are squared L2 by default; convert to a
        # 0-1 similarity score for readability
        similarity = round(max(0.0, 1.0 - dist / 2.0), 4)
        docs.append(
            {
                "text": text,
                "score": similarity,
                "metadata": meta,
                "chunk_id": chunk_id,
            }
        )

    # Sort highest similarity first
    docs.sort(key=lambda d: d["score"], reverse=True)
    return docs
