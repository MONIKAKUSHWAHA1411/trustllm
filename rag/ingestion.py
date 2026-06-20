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
import re
import shutil
import uuid
from pathlib import Path

import chromadb
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .embeddings import get_embedding_function, DEFAULT_EMBEDDING

BASE_DIR = Path(__file__).resolve().parents[1]
VECTOR_DB_PATH = str(BASE_DIR / "vector_db")

# Persistent location for uploaded source PDFs so they can be re-served
# for preview/download from the Failure Analysis and RAG Chat pages.
# Must match rag_page._uploads_dir().
UPLOADED_PDF_DIR = BASE_DIR / "data" / "uploads"

# Chunking parameters
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# Default ChromaDB collection name
DEFAULT_COLLECTION = "trustllm_rag"


def get_source_pdf_path(source_name: str) -> Path:
    """Return the on-disk path where the source PDF was persisted (may not exist)."""
    return UPLOADED_PDF_DIR / source_name


def collection_signature(
    embedding_model: str = DEFAULT_EMBEDDING,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> str:
    """
    Deterministic ChromaDB collection name for an *index-time* config.

    Index-time parameters (embedding model, chunk size, overlap) fully
    determine the contents of a collection; query-time parameters (top_k,
    prompt variant, generation model) do not. The RAG Debugger keys
    collections on this signature so a given (embedding, chunk, overlap)
    combination is embedded once and reused across query-time variations.

    Example
    -------
    >>> collection_signature("minilm", 500, 50)
    'exp_minilm_cs500_co50'
    """
    safe_model = re.sub(r"[^a-z0-9]", "", str(embedding_model).lower()) or "model"
    return f"exp_{safe_model}_cs{int(chunk_size)}_co{int(chunk_overlap)}"


def ingest_documents(
    file_path: str,
    collection_name: str = DEFAULT_COLLECTION,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
    embedding_model: str = DEFAULT_EMBEDDING,
) -> dict:
    """
    Load a PDF, split into chunks, embed, and upsert into ChromaDB.

    Parameters
    ----------
    file_path       : path to a PDF file
    collection_name : ChromaDB collection to store chunks in
    chunk_size      : characters per chunk (RecursiveCharacterTextSplitter)
    chunk_overlap   : overlapping characters between adjacent chunks
    embedding_model : embedding registry key (see rag.embeddings)

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

    # --- 1b. Persist a copy of the source PDF so it can be served back later ---
    try:
        UPLOADED_PDF_DIR.mkdir(parents=True, exist_ok=True)
        target = UPLOADED_PDF_DIR / source_name
        if str(Path(file_path).resolve()) != str(target.resolve()):
            shutil.copyfile(file_path, target)
    except Exception:
        # Persistence failure is non-fatal — indexing still proceeds.
        pass

    if not pages:
        raise ValueError(f"No content extracted from {source_name}")

    # --- 2. Split ---
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""],
    )
    chunks = splitter.split_documents(pages)

    if not chunks:
        raise ValueError("Document splitting produced no chunks.")

    # --- 3. Embed & store ---
    client = chromadb.PersistentClient(path=VECTOR_DB_PATH)
    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=get_embedding_function(embedding_model),
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


def ensure_indexed(
    file_path: str,
    embedding_model: str = DEFAULT_EMBEDDING,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> dict:
    """
    Index ``file_path`` into the collection for this index-time config, but
    **skip the work if that source is already present** in the collection.

    Used by the RAG Debugger so sweeping query-time knobs (top_k, prompt)
    against the same (embedding, chunk, overlap) does not re-embed the PDF.

    Returns the same dict as :func:`ingest_documents`, plus ``reused`` (bool).
    """
    file_path = str(file_path)
    source_name = os.path.basename(file_path)
    collection_name = collection_signature(embedding_model, chunk_size, chunk_overlap)

    client = chromadb.PersistentClient(path=VECTOR_DB_PATH)
    try:
        existing = [c.name for c in client.list_collections()]
    except Exception:
        existing = []

    if collection_name in existing:
        try:
            collection = client.get_collection(
                name=collection_name,
                embedding_function=get_embedding_function(embedding_model),
            )
            hit = collection.get(where={"source": source_name}, limit=1)
            if hit and hit.get("ids"):
                return {
                    "chunks_created": 0,
                    "collection_name": collection_name,
                    "source": source_name,
                    "reused": True,
                }
        except Exception:
            # Fall through to a fresh ingest if the existence check fails.
            pass

    result = ingest_documents(
        file_path,
        collection_name=collection_name,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        embedding_model=embedding_model,
    )
    result["reused"] = False
    return result
