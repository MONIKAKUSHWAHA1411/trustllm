# rag/__init__.py — Core RAG imports.
# rag_pipeline and evaluator are imported on-demand inside the functions
# that need them to keep the top-level import lightweight.
from .ingestion import ingest_documents
from .retriever import retrieve_documents
