# rag/__init__.py — Lazy imports to avoid pulling in ollama at module level.
# Ollama is only available locally (not on Streamlit Cloud), so rag_pipeline
# and evaluator must be imported on-demand inside the functions that need them.
from .ingestion import ingest_documents
from .retriever import retrieve_documents
