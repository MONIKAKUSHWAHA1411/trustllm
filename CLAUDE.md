# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Run the app:**
```bash
streamlit run app.py
# or
python main.py
```

**Install dependencies:**
```bash
pip install -r requirements.txt
```

**Run the offline evaluation pipeline:**
```bash
python -m evaluation_engine.evaluation_pipeline
```

**Generate LLM results (requires Ollama running with models pulled):**
```bash
cd llm_runner && python test_runner.py
```

**Run agent evaluation:**
```bash
python run_agent_eval.py
python run_agent_eval.py --dataset datasets/agent_test_cases.json --save
```

**Prerequisites:** Ollama must be running locally with models pulled (default: `mistral`).

## Architecture

TrustLLM is a Streamlit-based platform for evaluating LLM reliability, safety, and accuracy. It uses Ollama for local inference and ChromaDB for RAG.

### Data Flow

**Main evaluation pipeline** (sequential, JSON file I/O):
```
datasets/ → llm_runner/test_runner.py → reports/results.json
                                              ↓
                           evaluation_engine/ steps:
                           1. prompt_injection_test.py  (pattern matching)
                           2. hallucination_detector.py (regex-based)
                           3. llm_judge.py              (scores: correctness/relevance/clarity/safety)
                           4. merge_results.py          (computes trust_score)
                           5. model_leaderboard.py      (per-model aggregation)
                                              ↓
                                 reports/results.json (merged) → ui_pages/ + analytics/
```

**RAG pipeline:**
```
PDF → rag/ingestion.py → ChromaDB (vector_db/) → rag/retriever.py → rag/rag_pipeline.py (Ollama)
```

### Module Map

| Directory | Role |
|-----------|------|
| `ui_pages/` | Streamlit pages — each exports a single `render()` function called by `app.py` |
| `evaluation_engine/` | Offline evaluation pipeline; reads/writes JSON in `reports/` |
| `rag/` | RAG subsystem: PDF ingestion, ChromaDB, Ollama query |
| `agents/` | Simulated HR agent with keyword-based tool routing |
| `evaluators/` | Agent eval: compares predicted vs. labelled tool selections |
| `analytics/` | Read-only KPI/chart helpers over `reports/results.json` |
| `llm_runner/` | Core Ollama calling logic; `test_runner.py` populates `reports/results.json` |
| `datasets/` | JSON test data (prompts, agent test cases) |
| `reports/` | Pipeline output files (auto-generated, not committed) |

### Trust Score Formula

- **General eval:** `(halluc_score + correctness + relevance + clarity + safety) / 5`
- **Agent eval:** `0.35 × semantic_avg + 0.35 × halluc_score + 0.30 × tool_accuracy`
- **Leaderboard:** `0.4 × correctness + 0.2 × relevance + 0.2 × clarity + 0.2 × safety`

### Key Design Decisions

- **UI pages are stateless** except for `st.session_state` (pagination, user info, project filter). All page state lives in session, not globals.
- **Evaluation pipeline is file-based**: each step reads its input and writes augmented output back to `reports/`. Steps can be run independently as long as prior outputs exist.
- **Embeddings are local**: ChromaDB uses ONNX `all-MiniLM-L6-v2` — no GPU or external API required.
- **Agent routing is deterministic**: `agents/hr_agent.py` uses keyword matching, not an LLM — keeps agent eval reproducible.
- **Auth is flat-file**: credentials in `users.json`; project scopes in `projects.json`.
- **`llm_runner/test_runner.py` uses relative paths** — must be run from inside `llm_runner/`.
