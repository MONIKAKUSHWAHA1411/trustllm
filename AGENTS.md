# AGENTS.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

TrustLLM is a Streamlit-based AI evaluation platform for testing LLM reliability, safety, and accuracy. It supports prompt injection detection, hallucination detection, RAG evaluation, and agentic tool-selection evaluation.

## Commands

**Install dependencies:**
```
pip install -r requirements.txt
```

**Run the Streamlit app:**
```
streamlit run app.py
```
or
```
python main.py
```
Default credentials: `TestUser` / `User123` (defined in `users.json`).

**Run the full offline evaluation pipeline** (operates on pre-existing data in `reports/`):
```
python -m evaluation_engine.evaluation_pipeline
```

**Run agent evaluation from the CLI:**
```
python run_agent_eval.py
python run_agent_eval.py --dataset datasets/agent_test_cases.json --save
```

**Run LLM prompts through Ollama and save raw results** (requires Ollama running):
```
# Must be run from the llm_runner/ directory due to relative paths
cd llm_runner && python test_runner.py
```

**Prerequisites — Ollama must be running locally:**
```
ollama serve
ollama pull mistral   # default model; also used: phi3, phi
```

## Architecture

### Data Flow

```
datasets/ → llm_runner/test_runner.py → reports/results.json (raw)
                                              ↓
                           evaluation_engine/evaluation_pipeline.py
                           (injection → hallucination → judge → merge → leaderboard)
                                              ↓
                                    reports/results.json (merged, with trust_score)
                                              ↓
                               analytics/ + ui_pages/ (read-only consumers)
```

RAG has its own parallel flow:
```
PDF upload → rag/ingestion.py → vector_db/ (ChromaDB)
                                      ↓
                            rag/retriever.py → rag/rag_pipeline.py (Ollama) → answer
                                                       ↓
                                            rag/evaluator.py (cosine-similarity metrics)
```

### Module Responsibilities

**`evaluation_engine/`** — Offline evaluation pipeline. Each step reads/writes JSON files in `reports/`:
- `prompt_injection_test.py`: Pattern-matches injection phrases in prompts → `reports/prompt_injection_results.json`
- `hallucination_detector.py`: Regex-matches vague claim patterns in responses → `reports/hallucination_results.json`
- `llm_judge.py`: Assigns scores for correctness, relevance, clarity, safety → `reports/judged_results.json` (currently simulated with `random.uniform`)
- `merge_results.py`: Joins all three reports and computes composite trust scores → `reports/results.json`. Trust score formula: `(halluc_score + correctness + relevance + clarity + safety) / 5`. For agent evals: `0.35 * semantic_avg + 0.35 * halluc_score + 0.30 * tool_accuracy`
- `model_leaderboard.py`: Aggregates trust scores per model → `reports/model_leaderboard.json`. Uses a separate weighted formula: `0.4 * correctness + 0.2 * relevance + 0.2 * clarity + 0.2 * safety`

**`rag/`** — RAG pipeline backed by ChromaDB + Ollama:
- `embeddings.py`: Singleton embedding function using ChromaDB's built-in ONNX runtime (`all-MiniLM-L6-v2`). No GPU/PyTorch needed.
- `ingestion.py`: PDF → PyPDFLoader → RecursiveCharacterTextSplitter (500 chars / 50 overlap) → ChromaDB upsert into collection `trustllm_rag` at `./vector_db`
- `retriever.py`: Queries collection, returns top-K chunks (default 3) sorted by cosine similarity
- `rag_pipeline.py`: Assembles a strict context-only prompt and calls `ollama.chat()`
- `evaluator.py`: Computes context_relevance, faithfulness, and hallucination_risk using cosine similarity between embeddings of the query, answer, and retrieved chunks — no external LLM judge

**`agents/` + `evaluators/`** — Agent evaluation subsystem:
- `agents/hr_agent.py`: Deterministic simulated HR agent. Routes queries to `workday_api`, `servicenow_api`, or `policy_retriever` using regex keyword matching
- `evaluators/agent_eval.py`: Measures tool-selection accuracy against a labelled JSON dataset
- `datasets/agent_test_cases.json`: 10 labelled queries for HR agent evaluation

**`analytics/`** — Read-only analytics helpers that operate on `reports/results.json`:
- `metrics.py`: Top-level KPIs (avg trust score, hallucination rate, safety average, total prompts)
- `aggregations.py`: Per-model groupings and hallucination heatmap pivot table
- Trust score < 0.7 is treated as a "failure" in `visual_data.py`; < 0.6 in `failing_prompts.py`

**`ui_pages/`** — Each file exports a single `render()` function, called by `app.py`'s page router. Pages are stateless except for `st.session_state`. The `run_eval.py` page simulates evaluations with random scores and appends results to `reports/results.json`.

**`app.py`** — Streamlit entry point. Handles login (via `users.json`), loads project filter from `projects.json`, stores `project_categories` in `st.session_state` for pages to filter on, and routes to UI pages via sidebar radio.

### Key Configuration Files

- `projects.json`: defines named project scopes with `categories` arrays used as filters (Safety Bench, Factual QA, Bias Audit)
- `users.json`: simple flat-file user store for auth
- `.streamlit/config.toml`: dark theme with custom colour palette
- `style.css`: custom CSS injected into Streamlit via `st.markdown(..., unsafe_allow_html=True)`

### Reports Directory

All pipeline outputs land in `reports/` as JSON. `reports/results.json` is the canonical merged dataset read by analytics and UI pages. The file is appended to (not replaced) when evaluations are run from the UI.
