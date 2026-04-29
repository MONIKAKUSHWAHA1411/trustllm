"""
rag/ingestion.py — TrustLLM RAG Module
=========================================
Loads PDFs, splits them into chunks, and stores them in a persistent
ChromaDB collection.

Pipeline:
    PDF file → PyPDFLoader → RecursiveCharacterTextSplitter
             → embeddings   → ChromaDB (./vector_db)
"""

import os
import uuid
from pathlib import Path

import chromadb
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .embeddings import get_embedding_function

BASE_DIR = Path(__file__).resolve().parents[1]
VECTOR_DB_PATH = str(BASE_DIR / "vector_db")

# Chunking parameters
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# Default ChromaDB collection name
DEFAULT_COLLECTION = "trustllm_rag"


def ingest_documents(file_path: str, collection_name: str = DEFAULT_COLLECTION) -> dict:
    """
    Load a PDF, split into chunks, embed, and upsert into ChromaDB.

    Parameters
    ----------
    file_path       : path to a PDF file
    collection_name : ChromaDB collection to store chunks in

    Returns
    -------
    dict
        chunks_created  – int
        collection_name – str
        source          – str (filename)
    """
    file_path = str(file_path)
    source_name = os.path.basename(file_path)

    # --- 1. Load PDF ---
    loader = PyPDFLoader(file_path)
    pages = loader.load()

    if not pages:
        raise ValueError(f"No content extracted from {source_name}")

    # --- 2. Split ---
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", " ", ""],
    )
    chunks = splitter.split_documents(pages)

    if not chunks:
        raise ValueError("Document splitting produced no chunks.")

    # --- 3. Embed & store ---
    client = chromadb.PersistentClient(path=VECTOR_DB_PATH)
    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=get_embedding_function(),
    )

    ids = [str(uuid.uuid4()) for _ in chunks]
    texts = [c.page_content for c in chunks]
    metadatas = [
        {
            "source": source_name,
            "page": c.metadata.get("page", 0),
            "chunk_index": i,
        }
        for i, c in enumerate(chunks)
    ]

    collection.upsert(ids=ids, documents=texts, metadatas=metadatas)

    return {
        "chunks_created": len(chunks),
        "collection_name": collection_name,
        "source": source_name,
    }
