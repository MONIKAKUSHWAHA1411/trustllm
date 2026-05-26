# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Install dependencies:**
```bash
pip install -r requirements.txt
```

**Run the app:**
```bash
streamlit run app.py
# or
python main.py
```
Default login: `TestUser` / `User123` (defined in `users.json`).

**Run the offline evaluation pipeline** (operates on pre-existing data in `reports/`):
```bash
python -m evaluation_engine.evaluation_pipeline
```

**Run agent evaluation from CLI:**
```bash
python run_agent_eval.py
python run_agent_eval.py --dataset datasets/agent_test_cases.json --save
```

**Run LLM prompts through Ollama** (must be run from `llm_runner/` due to relative paths):
```bash
cd llm_runner && python test_runner.py
```

**Prerequisites — Ollama must be running for live LLM calls:**
```bash
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

RAG has a parallel flow:
```
PDF upload → rag/ingestion.py → vector_db/ (ChromaDB)
                                      ↓
                            rag/retriever.py → rag/rag_pipeline.py (Ollama) → answer
                                                       ↓
                                            rag/evaluator.py (cosine-similarity metrics)
```

### Key Design Decisions

**`reports/results.json` is the canonical dataset.** All analytics pages and most UI pages read exclusively from this file. The `run_eval` UI page appends to it (never replaces). The offline pipeline writes intermediate files (`prompt_injection_results.json`, `hallucination_results.json`, `judged_results.json`) and `merge_results.py` joins them all into `results.json`.

**Trust score formulas differ by context:**
- Standard eval: `(halluc_score + correctness + relevance + clarity + safety) / 5`
- Agent eval: `0.35 * semantic_avg + 0.35 * halluc_score + 0.30 * tool_accuracy`
- Leaderboard: `0.4 * correctness + 0.2 * relevance + 0.2 * clarity + 0.2 * safety`
- Failure threshold: `< 0.7` in `visual_data.py`, `< 0.6` in `failing_prompts.py`

**LLM judge scores are currently simulated** (`random.uniform` in `evaluation_engine/llm_judge.py`). The pipeline structure is real, but scoring is not calling a real judge LLM.

**Hallucination and injection detection are regex/pattern-based**, not LLM-based. `hallucination_detector.py` matches vague claim patterns; `prompt_injection_test.py` pattern-matches injection phrases.

**RAG embeddings use ChromaDB's built-in ONNX runtime** (`all-MiniLM-L6-v2`) via a singleton in `rag/embeddings.py` — no GPU or PyTorch required. The collection `trustllm_rag` is persisted at `./vector_db`.

**HR agent is deterministic** (`agents/hr_agent.py`): routes queries to `workday_api`, `servicenow_api`, or `policy_retriever` using regex keyword matching. `evaluators/agent_eval.py` measures tool-selection accuracy against the labeled dataset at `datasets/agent_test_cases.json`.

### Module Responsibilities

- **`app.py`** — Streamlit entry point: login gate → onboarding flow → page router. Loads `projects.json` and sets `st.session_state["project_categories"]` for downstream filtering. Pages are routed via sidebar radio using `st.session_state["page"]`.
- **`ui_pages/`** — Each file exports a single `render()` function. Pages are stateless except for `st.session_state`.
- **`evaluation_engine/`** — Offline pipeline steps, each reading/writing JSON in `reports/`.
- **`analytics/`** — Pure read-only helpers over `reports/results.json` (KPIs, groupings, heatmaps).
- **`rag/`** — Ingestion, retrieval, pipeline, and evaluation for RAG testing.
- **`agents/` + `evaluators/`** — HR agent simulation and its tool-selection accuracy evaluation.
- **`llm_runner/`** — Direct Ollama calls producing raw `reports/results.json`.

### Configuration Files

- `projects.json` — Named project scopes with `categories` arrays (`Safety Bench`, `Factual QA`, `Bias Audit`) used as filters throughout the UI.
- `users.json` — Flat-file user store (username, password, display_name, role).
- `style.css` — Custom CSS injected globally via `st.markdown(..., unsafe_allow_html=True)` in `app.py`.
- `.streamlit/config.toml` — Dark theme with custom colour palette.
