<div align="center">

<img src="https://img.shields.io/badge/T-TrustLLM-E8420A?style=for-the-badge&labelColor=0A0A0A&color=E8420A" height="48" alt="TrustLLM" />

# TrustLLM

**Evaluate LLM Truthfulness · Safety · Fairness · Robustness · Privacy · Ethics**

A local-first, multi-provider LLM evaluation platform with RAG testing, agent benchmarking, and a full analytics dashboard. No GPU required.

---

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-≥1.39-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)](https://streamlit.io)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-≥1.5-1C1C1C?style=flat-square)](https://trychroma.com)
[![LangChain](https://img.shields.io/badge/LangChain-≥0.3-1C8A6E?style=flat-square)](https://langchain.com)
[![Groq](https://img.shields.io/badge/Groq-supported-F55036?style=flat-square)](https://groq.com)
[![License](https://img.shields.io/badge/License-MIT-6B7280?style=flat-square)](LICENSE)
[![Last Commit](https://img.shields.io/github/last-commit/monikakushwaha1411/trustllm?style=flat-square&color=E8420A)](https://github.com/monikakushwaha1411/trustllm/commits)

</div>

---

## What it does

TrustLLM runs LLM responses through a multi-step evaluation pipeline and produces a weighted **trust score** across six dimensions:

| Dimension | Measured as |
|---|---|
| **Truthfulness** | Hallucination score (regex + pattern matching) |
| **Correctness** | LLM-judge grade (0–1) |
| **Relevance** | LLM-judge grade (0–1) |
| **Clarity** | LLM-judge grade (0–1) |
| **Safety** | Prompt injection detection + LLM-judge safety score |
| **Fairness / Robustness / Privacy / Ethics** | Trust dimension tags (evaluation modules) |

**Trust score formulas (actual code):**

```
General eval:   trust_score = (halluc_score + correctness + relevance + clarity + safety) / 5
Agent eval:     trust_score = 0.35 × semantic_avg + 0.35 × halluc_score + 0.30 × tool_accuracy
Leaderboard:    trust_score = 0.4 × correctness + 0.2 × relevance + 0.2 × clarity + 0.2 × safety
```

---

## Dashboard pages

| Page | What it does |
|---|---|
| **Overview** | Trust report — KPI grid, per-model trust scores, verdict banner |
| **Leaderboard** | Ranked model table by weighted trust score |
| **Run Evaluation** | Single-prompt eval against any configured provider |
| **Prompt Dataset** | Upload a JSON dataset, batch-eval across all models |
| **Prompt Explorer** | Browse, filter, and re-run individual prompts |
| **RAG Testing** | Upload PDFs → ingest → query → faithfulness score |
| **Failure Analysis** | Browse failures by type (hallucination / injection / safety) |
| **Agent Performance** | Benchmark HR agent on tool-call accuracy + semantic score |
| **Experiments** | Grouped experiment tracking |
| **Logs** | Raw evaluation run log viewer |
| **Query History** | Per-user query history |
| **Export Report** | Download results as PDF (ReportLab) or JSON |
| **API Keys** | BYOK — store provider keys encrypted at rest |
| **Profile** | User account and project scope |

---

## Supported model providers

All providers are **BYOK (bring your own key)**. No keys are bundled.

| Provider | SDK |
|---|---|
| **Groq** | `groq>=0.9.0` |
| **Anthropic / Claude** | `anthropic>=0.39.0` |
| **OpenAI / GPT** | `openai>=1.50.0` |
| **Google Gemini** | `google-generativeai>=0.8.0` |
| **Mistral** | `mistralai>=1.2.0` |
| **HuggingFace** | `huggingface_hub>=0.26.0` |
| **Ollama (local)** | HTTP calls via `llm_runner/` |

---

## Architecture

```
datasets/ → llm_runner/test_runner.py → reports/results.json
                                               ↓
                          evaluation_engine/ (5 sequential steps):
                          1. prompt_injection_test.py   pattern matching
                          2. hallucination_detector.py  regex-based
                          3. llm_judge.py               correctness / relevance / clarity / safety
                          4. merge_results.py           computes trust_score
                          5. model_leaderboard.py       per-model aggregation
                                               ↓
                              reports/results.json  →  ui_pages/ + analytics/

RAG pipeline:
PDF → rag/ingestion.py → ChromaDB (vector_db/) → rag/retriever.py → rag/rag_pipeline.py
```

Embeddings: **ONNX `all-MiniLM-L6-v2`** — runs locally, no GPU, no external API call.

Agent routing: **keyword matching** (`agents/hr_agent.py`) — deterministic, not LLM-driven.

---

## Tech stack

```
Frontend     Streamlit ≥1.39  +  React/Vite landing page (Tailwind CSS)
Evaluation   LangChain ≥0.3, custom Python pipeline (evaluation_engine/)
Vector DB    ChromaDB ≥1.5  (local persistent, ONNX embeddings)
PDF parsing  PyPDF ≥4.3
Charts       Plotly
PDF export   ReportLab
Auth         Flat-file users.json  +  Google OAuth  +  GitHub OAuth  (Authlib)
             Supabase auth (feature branch)
API keys     Encrypted at rest with cryptography ≥43
Email        Resend ≥2.0
Env          python-dotenv
Runtime      Python 3.11
```

---

## Setup

```bash
# 1. Clone
git clone https://github.com/monikakushwaha1411/trustllm
cd trustllm

# 2. Install
pip install -r requirements.txt

# 3. Configure
cp .env.example .env          # add GROQ_API_KEY and/or other provider keys
                              # add GOOGLE_CLIENT_ID / GITHUB_CLIENT_ID for OAuth

# 4. Run
streamlit run app.py
```

**Run the evaluation pipeline (requires results.json):**

```bash
# Generate LLM results first (needs Ollama running with mistral pulled)
cd llm_runner && python test_runner.py

# Then run the full pipeline
cd .. && python -m evaluation_engine.evaluation_pipeline
```

**Run agent evaluation:**

```bash
python run_agent_eval.py
python run_agent_eval.py --dataset datasets/agent_test_cases.json --save
```

---

## What this is NOT

> Honest limitations. Read before using.

- **Not a real-time evaluator.** The pipeline is file-based and sequential — it reads/writes `reports/results.json`. There is no streaming eval loop.
- **Not a hosted API.** No REST endpoints, no webhooks, no SDK. It is a Streamlit app.
- **Not a GPU workload.** Embeddings use ONNX CPU-only (`all-MiniLM-L6-v2`). No CUDA required.
- **Not an academic benchmark.** Trust scores are computed by a local LLM judge (`llm_judge.py`) using Groq/Ollama — not by a certified human-annotated rubric.
- **Not multi-tenant production-ready.** Auth is flat-file (`users.json`). There is no row-level security, no rate limiting, no audit log by default.
- **Not a drop-in replacement for RAGAS, HELM, or EleutherAI LM-Eval.** It shares some goals but is a standalone implementation with different scoring methodology.
- **Agent routing is keyword-based** (`hr_agent.py`), not LLM-driven — agent eval results reflect keyword matching accuracy, not reasoning capability.
- **No GPU, no Ollama = no local inference.** Cloud provider keys (Groq etc.) are needed if Ollama is not running locally.

---

## Project structure

```
trustllm/
├── app.py                  # Streamlit entry point — login + routing
├── ui_pages/               # One render() function per page
├── evaluation_engine/      # Offline eval pipeline (5 steps)
├── rag/                    # PDF ingestion, ChromaDB, retrieval, RAG eval
├── agents/                 # HR agent (keyword routing)
├── evaluators/             # Agent eval: predicted vs labelled tools
├── analytics/              # Read-only KPI helpers over results.json
├── llm_runner/             # Ollama calling logic, test_runner.py
├── auth/                   # Google OAuth, GitHub OAuth, Supabase auth
├── email_service/          # Resend welcome emails
├── datasets/               # JSON test data
├── reports/                # Pipeline output (git-ignored)
├── landing/                # React/Vite marketing landing page
├── style.css               # Global Streamlit CSS overrides
└── requirements.txt
```

---

## Built by

[Monika Kushwaha](https://www.linkedin.com/in/monika-kushwaha-52443735) · AI/ML Engineer
