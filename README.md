# TrustLLM — AI Evaluation & RAG Testing Platform

TrustLLM is a local-first AI evaluation platform designed to test and analyse LLM behaviour across prompts, datasets, and RAG pipelines.

## Features

- Prompt Testing & Evaluation
- Prompt Dataset Upload & Batch Evaluation
- RAG Testing with Local LLM (Ollama)
- Retrieval Debugger
- Failure Analysis Dashboard
- Hallucination & Faithfulness Metrics
- Latency & Performance Tracking

## Tech Stack

- Python (Streamlit)
- LangChain
- Ollama (Local LLMs)
- Chroma (Vector DB)
- Sentence Transformers

## Key Capabilities

- Evaluate LLM responses using datasets
- Detect hallucinations vs retrieval failures
- Analyze per-prompt performance
- Debug RAG pipelines with source tracing

## Demo

(Add screenshots here)

## How to Run

```bash
pip install -r requirements.txt
streamlit run app.py
