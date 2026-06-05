import streamlit as st
import json
import textwrap
from pathlib import Path

from ui_pages.overview import render as overview
from ui_pages.prompt_explorer import render as prompt_explorer
from ui_pages.leaderboard import render as leaderboard
from ui_pages.run_eval import render as run_eval
from ui_pages.agent_performance import render as agent_performance
from ui_pages.rag_page import render as rag_testing
from ui_pages.prompt_dataset import render as prompt_dataset
from ui_pages.failure_analysis import render as failure_analysis

BASE_DIR = Path(__file__).resolve().parent


def _h(html: str) -> str:
    """Strip common indentation so Markdown never misreads HTML as a code block."""
    return textwrap.dedent(html).strip()


# -----------------------------------------------
# PAGE CONFIG
# -----------------------------------------------
st.set_page_config(
    page_title="TrustLLM",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)


# -----------------------------------------------
# LOAD CSS
# -----------------------------------------------
def load_css():
    with open(BASE_DIR / "style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()


# -----------------------------------------------
# AUTH HELPERS
# -----------------------------------------------
def _load_users():
    with open(BASE_DIR / "users.json") as f:
        return json.load(f)["users"]


def _authenticate(username, password):
    for u in _load_users():
        if u["username"] == username and u["password"] == password:
            return u
    return None


# -----------------------------------------------
# LOGIN PAGE  —  VERDICT style (single-column)
# -----------------------------------------------
def _show_login():
    def _md(html_str):
        import textwrap
        h = textwrap.dedent(html_str).strip()
        h = "\n".join(ln for ln in h.splitlines() if ln.strip())
        st.markdown(h, unsafe_allow_html=True)

    # ── CSS + Fonts ──────────────────────────────────────────────────────
    st.markdown("""<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
[data-testid="stAppViewContainer"] { background: #0E0E0E !important; }
[data-testid="stApp"] { background: #0E0E0E !important; }
.block-container { padding-top: 0 !important; max-width: 100% !important; }
[data-testid="stForm"] {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
}
[data-testid="stForm"] input {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    border-radius: 0 !important;
    color: white !important;
    font-family: 'Inter', sans-serif !important;
}
[data-testid="stForm"] input:focus {
    border-color: #E8290B !important;
    box-shadow: none !important;
}
[data-testid="stForm"] label {
    color: rgba(255,255,255,0.6) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.8rem !important;
}
[data-testid="stForm"] .stButton > button {
    background: #E8290B !important;
    color: white !important;
    border: none !important;
    border-radius: 0 !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    letter-spacing: 0.08em !important;
    font-size: 0.85rem !important;
    padding: 0.65rem 1.5rem !important;
    width: 100% !important;
}
[data-testid="stForm"] .stButton > button:hover {
    background: #C42208 !important;
}
[data-testid="stForm"] [data-testid="InputInstructions"] {
    display: none !important;
}
.stAlert { border-radius: 0 !important; }
</style>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">""", unsafe_allow_html=True)

    # ── HERO ──────────────────────────────────────────────────────────────
    _md("""
<div style="background:#0E0E0E;padding:4rem 2rem 3rem;font-family:'Syne',sans-serif;">
  <div style="max-width:860px;margin:0 auto;">
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:3rem;">
      <div style="background:#E8290B;width:40px;height:40px;display:flex;align-items:center;justify-content:center;font-size:20px;font-weight:800;color:white;flex-shrink:0;">T</div>
      <div>
        <div style="color:white;font-size:1.1rem;font-weight:800;letter-spacing:0.03em;">TrustLLM</div>
        <div style="color:rgba(255,255,255,0.25);font-size:8px;letter-spacing:0.18em;margin-top:2px;">EVAL PLATFORM</div>
      </div>
    </div>
    <div style="font-size:10px;color:#E8290B;letter-spacing:0.2em;margin-bottom:1rem;font-weight:600;">— AI TRUST EVALUATION PLATFORM</div>
    <h1 style="font-size:clamp(2rem,5vw,3.5rem);font-weight:800;color:white;line-height:1.05;letter-spacing:-0.03em;margin:0 0 1.5rem;">Your LLMs.<br><em style="color:#E8290B;font-style:normal;">Honestly</em><br>Evaluated.</h1>
    <p style="color:rgba(255,255,255,0.55);font-size:1rem;line-height:1.7;max-width:560px;font-family:'Inter',sans-serif;margin-bottom:2.5rem;">Run rigorous trust benchmarks across safety, fairness, robustness, privacy, and truthfulness. Get verdicts, not vanity metrics.</p>
    <div style="display:flex;gap:2rem;padding-top:2rem;border-top:1px solid rgba(255,255,255,0.08);">
      <div style="text-align:center;">
        <div style="font-size:2rem;font-weight:800;color:#E8290B;">12+</div>
        <div style="font-size:0.72rem;color:rgba(255,255,255,0.35);letter-spacing:0.12em;margin-top:4px;">MODELS TESTED</div>
      </div>
      <div style="width:1px;background:rgba(255,255,255,0.08);"></div>
      <div style="text-align:center;">
        <div style="font-size:2rem;font-weight:800;color:#E8290B;">6</div>
        <div style="font-size:0.72rem;color:rgba(255,255,255,0.35);letter-spacing:0.12em;margin-top:4px;">TRUST DIMENSIONS</div>
      </div>
      <div style="width:1px;background:rgba(255,255,255,0.08);"></div>
      <div style="text-align:center;">
        <div style="font-size:2rem;font-weight:800;color:#E8290B;">500+</div>
        <div style="font-size:0.72rem;color:rgba(255,255,255,0.35);letter-spacing:0.12em;margin-top:4px;">EVAL PROMPTS</div>
      </div>
      <div style="width:1px;background:rgba(255,255,255,0.08);"></div>
      <div style="text-align:center;">
        <div style="font-size:2rem;font-weight:800;color:#E8290B;">RAG</div>
        <div style="font-size:0.72rem;color:rgba(255,255,255,0.35);letter-spacing:0.12em;margin-top:4px;">PIPELINE BUILT-IN</div>
      </div>
    </div>
  </div>
</div>
""")

    # ── BYOK WOW FEATURE ─────────────────────────────────────────────────
    _md("""
<div style="background:#1C1C1C;padding:3rem 2rem;font-family:'Syne',sans-serif;border-top:3px solid #E8290B;">
  <div style="max-width:860px;margin:0 auto;">
    <div style="font-size:10px;color:#E8290B;letter-spacing:0.2em;margin-bottom:0.75rem;font-weight:600;">— BRING YOUR OWN KEY</div>
    <h2 style="font-size:clamp(1.5rem,3vw,2.2rem);font-weight:800;color:white;letter-spacing:-0.02em;margin:0 0 1rem;line-height:1.1;">Your Keys. Any Model.<br><em style="color:#E8290B;font-style:normal;">Full Trust Report.</em></h2>
    <p style="color:rgba(255,255,255,0.55);font-size:0.95rem;line-height:1.7;max-width:620px;font-family:'Inter',sans-serif;margin-bottom:2rem;">Why guess when you can verify? Connect your own OpenAI, Anthropic, Google, or Groq API keys and benchmark ChatGPT, Claude, Gemini, and Grok head-to-head — on your data, with your prompts, in real time.</p>
    <div style="display:flex;flex-wrap:wrap;gap:0.75rem;">
      <div style="background:rgba(232,41,11,0.1);border:1px solid rgba(232,41,11,0.3);padding:0.5rem 1rem;font-size:0.8rem;font-weight:600;color:#E8290B;letter-spacing:0.05em;">ChatGPT · OpenAI</div>
      <div style="background:rgba(232,41,11,0.1);border:1px solid rgba(232,41,11,0.3);padding:0.5rem 1rem;font-size:0.8rem;font-weight:600;color:#E8290B;letter-spacing:0.05em;">Claude · Anthropic</div>
      <div style="background:rgba(232,41,11,0.1);border:1px solid rgba(232,41,11,0.3);padding:0.5rem 1rem;font-size:0.8rem;font-weight:600;color:#E8290B;letter-spacing:0.05em;">Gemini · Google</div>
      <div style="background:rgba(232,41,11,0.1);border:1px solid rgba(232,41,11,0.3);padding:0.5rem 1rem;font-size:0.8rem;font-weight:600;color:#E8290B;letter-spacing:0.05em;">Grok · xAI</div>
    </div>
  </div>
</div>
""")

    # ── HOW IT WORKS ─────────────────────────────────────────────────────
    _md("""
<div style="background:#0E0E0E;padding:4rem 2rem;font-family:'Syne',sans-serif;">
  <div style="max-width:860px;margin:0 auto;">
    <div style="font-size:10px;color:#E8290B;letter-spacing:0.2em;margin-bottom:0.75rem;font-weight:600;">— HOW IT WORKS</div>
    <h2 style="font-size:1.8rem;font-weight:800;color:white;letter-spacing:-0.02em;margin:0 0 2.5rem;">5 Steps to a Trust Score.</h2>
    <div style="display:flex;flex-direction:column;gap:0;">
      <div style="display:flex;gap:1.5rem;align-items:flex-start;padding:1.5rem 0;border-bottom:1px solid rgba(255,255,255,0.06);">
        <div style="background:#E8290B;min-width:36px;height:36px;display:flex;align-items:center;justify-content:center;font-size:0.85rem;font-weight:800;color:white;flex-shrink:0;">01</div>
        <div>
          <div style="font-size:1rem;font-weight:700;color:white;margin-bottom:0.35rem;">Connect Your Models</div>
          <div style="font-size:0.85rem;color:rgba(255,255,255,0.45);line-height:1.65;font-family:'Inter',sans-serif;">Add your LLM endpoints or paste API keys for OpenAI, Anthropic, Google, Groq, or any OpenAI-compatible API.</div>
        </div>
      </div>
      <div style="display:flex;gap:1.5rem;align-items:flex-start;padding:1.5rem 0;border-bottom:1px solid rgba(255,255,255,0.06);">
        <div style="background:#E8290B;min-width:36px;height:36px;display:flex;align-items:center;justify-content:center;font-size:0.85rem;font-weight:800;color:white;flex-shrink:0;">02</div>
        <div>
          <div style="font-size:1rem;font-weight:700;color:white;margin-bottom:0.35rem;">Select Evaluation Dimensions</div>
          <div style="font-size:0.85rem;color:rgba(255,255,255,0.45);line-height:1.65;font-family:'Inter',sans-serif;">Choose from 6 trust dimensions — Safety, Fairness, Robustness, Privacy, Machine Ethics, and Truthfulness — or run the full suite.</div>
        </div>
      </div>
      <div style="display:flex;gap:1.5rem;align-items:flex-start;padding:1.5rem 0;border-bottom:1px solid rgba(255,255,255,0.06);">
        <div style="background:#E8290B;min-width:36px;height:36px;display:flex;align-items:center;justify-content:center;font-size:0.85rem;font-weight:800;color:white;flex-shrink:0;">03</div>
        <div>
          <div style="font-size:1rem;font-weight:700;color:white;margin-bottom:0.35rem;">Run Adversarial Prompts</div>
          <div style="font-size:0.85rem;color:rgba(255,255,255,0.45);line-height:1.65;font-family:'Inter',sans-serif;">500+ curated prompts probe your model's boundaries — jailbreaks, bias probes, hallucination traps, privacy leaks, and more.</div>
        </div>
      </div>
      <div style="display:flex;gap:1.5rem;align-items:flex-start;padding:1.5rem 0;border-bottom:1px solid rgba(255,255,255,0.06);">
        <div style="background:#E8290B;min-width:36px;height:36px;display:flex;align-items:center;justify-content:center;font-size:0.85rem;font-weight:800;color:white;flex-shrink:0;">04</div>
        <div>
          <div style="font-size:1rem;font-weight:700;color:white;margin-bottom:0.35rem;">Get Scored Verdicts</div>
          <div style="font-size:0.85rem;color:rgba(255,255,255,0.45);line-height:1.65;font-family:'Inter',sans-serif;">Each response is scored by a judge LLM and rule-based classifiers. Results aggregate into per-dimension scores and an overall Trust Score.</div>
        </div>
      </div>
      <div style="display:flex;gap:1.5rem;align-items:flex-start;padding:1.5rem 0;">
        <div style="background:#E8290B;min-width:36px;height:36px;display:flex;align-items:center;justify-content:center;font-size:0.85rem;font-weight:800;color:white;flex-shrink:0;">05</div>
        <div>
          <div style="font-size:1rem;font-weight:700;color:white;margin-bottom:0.35rem;">Compare and Decide</div>
          <div style="font-size:0.85rem;color:rgba(255,255,255,0.45);line-height:1.65;font-family:'Inter',sans-serif;">Side-by-side leaderboard shows where each model excels and fails. Export reports, track regressions, and make evidence-based deployment decisions.</div>
        </div>
      </div>
    </div>
  </div>
</div>
""")

    # ── TRUST DIMENSIONS ─────────────────────────────────────────────────
    _md("""
<div style="background:#1C1C1C;padding:4rem 2rem;font-family:'Syne',sans-serif;">
  <div style="max-width:860px;margin:0 auto;">
    <div style="font-size:10px;color:#E8290B;letter-spacing:0.2em;margin-bottom:0.75rem;font-weight:600;">— TRUST DIMENSIONS</div>
    <h2 style="font-size:1.8rem;font-weight:800;color:white;letter-spacing:-0.02em;margin:0 0 2rem;">6 Dimensions. One Score.</h2>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:1px;background:rgba(255,255,255,0.06);">
      <div style="background:#1C1C1C;padding:1.75rem 1.5rem;">
        <div style="font-size:1.5rem;margin-bottom:0.75rem;">🛡️</div>
        <div style="font-size:0.95rem;font-weight:700;color:white;margin-bottom:0.5rem;">Safety</div>
        <div style="font-size:0.82rem;color:rgba(255,255,255,0.4);line-height:1.6;font-family:'Inter',sans-serif;">Jailbreak resistance, harmful output prevention, content policy adherence under adversarial conditions.</div>
      </div>
      <div style="background:#1C1C1C;padding:1.75rem 1.5rem;">
        <div style="font-size:1.5rem;margin-bottom:0.75rem;">⚖️</div>
        <div style="font-size:0.95rem;font-weight:700;color:white;margin-bottom:0.5rem;">Fairness</div>
        <div style="font-size:0.82rem;color:rgba(255,255,255,0.4);line-height:1.6;font-family:'Inter',sans-serif;">Demographic bias detection across gender, race, religion, and protected attributes in model outputs.</div>
      </div>
      <div style="background:#1C1C1C;padding:1.75rem 1.5rem;">
        <div style="font-size:1.5rem;margin-bottom:0.75rem;">💪</div>
        <div style="font-size:0.95rem;font-weight:700;color:white;margin-bottom:0.5rem;">Robustness</div>
        <div style="font-size:0.82rem;color:rgba(255,255,255,0.4);line-height:1.6;font-family:'Inter',sans-serif;">Consistency under paraphrasing, typos, and adversarial rephrasing. Does your model hold its ground?</div>
      </div>
      <div style="background:#1C1C1C;padding:1.75rem 1.5rem;">
        <div style="font-size:1.5rem;margin-bottom:0.75rem;">🔒</div>
        <div style="font-size:0.95rem;font-weight:700;color:white;margin-bottom:0.5rem;">Privacy</div>
        <div style="font-size:0.82rem;color:rgba(255,255,255,0.4);line-height:1.6;font-family:'Inter',sans-serif;">PII leakage, training data extraction, and sensitive information disclosure detection.</div>
      </div>
      <div style="background:#1C1C1C;padding:1.75rem 1.5rem;">
        <div style="font-size:1.5rem;margin-bottom:0.75rem;">🎯</div>
        <div style="font-size:0.95rem;font-weight:700;color:white;margin-bottom:0.5rem;">Truthfulness</div>
        <div style="font-size:0.82rem;color:rgba(255,255,255,0.4);line-height:1.6;font-family:'Inter',sans-serif;">Hallucination rate, factual accuracy, and calibration. Does the model know what it doesn't know?</div>
      </div>
      <div style="background:#1C1C1C;padding:1.75rem 1.5rem;">
        <div style="font-size:1.5rem;margin-bottom:0.75rem;">🤖</div>
        <div style="font-size:0.95rem;font-weight:700;color:white;margin-bottom:0.5rem;">Machine Ethics</div>
        <div style="font-size:0.82rem;color:rgba(255,255,255,0.4);line-height:1.6;font-family:'Inter',sans-serif;">Moral reasoning, sycophancy resistance, and alignment to human values in edge-case dilemmas.</div>
      </div>
    </div>
  </div>
</div>
""")

    # ── MODELS ────────────────────────────────────────────────────────────
    _md("""
<div style="background:#0E0E0E;padding:4rem 2rem;font-family:'Syne',sans-serif;">
  <div style="max-width:860px;margin:0 auto;">
    <div style="font-size:10px;color:#E8290B;letter-spacing:0.2em;margin-bottom:0.75rem;font-weight:600;">— MODELS EVALUATED</div>
    <h2 style="font-size:1.8rem;font-weight:800;color:white;letter-spacing:-0.02em;margin:0 0 2rem;">12 Models. 6 Providers.</h2>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1px;background:rgba(255,255,255,0.06);">
      <div style="background:#0E0E0E;padding:1.25rem 1.5rem;">
        <div style="font-size:0.72rem;color:#E8290B;letter-spacing:0.12em;margin-bottom:0.5rem;font-weight:600;">OPENAI</div>
        <div style="font-size:0.88rem;color:rgba(255,255,255,0.7);font-family:'Inter',sans-serif;line-height:1.9;">GPT-4o<br>GPT-4 Turbo<br>GPT-3.5 Turbo</div>
      </div>
      <div style="background:#0E0E0E;padding:1.25rem 1.5rem;">
        <div style="font-size:0.72rem;color:#E8290B;letter-spacing:0.12em;margin-bottom:0.5rem;font-weight:600;">ANTHROPIC</div>
        <div style="font-size:0.88rem;color:rgba(255,255,255,0.7);font-family:'Inter',sans-serif;line-height:1.9;">Claude 3 Opus<br>Claude 3 Sonnet<br>Claude 3 Haiku</div>
      </div>
      <div style="background:#0E0E0E;padding:1.25rem 1.5rem;">
        <div style="font-size:0.72rem;color:#E8290B;letter-spacing:0.12em;margin-bottom:0.5rem;font-weight:600;">GOOGLE</div>
        <div style="font-size:0.88rem;color:rgba(255,255,255,0.7);font-family:'Inter',sans-serif;line-height:1.9;">Gemini Pro<br>Gemini Flash<br>Gemini Ultra</div>
      </div>
      <div style="background:#0E0E0E;padding:1.25rem 1.5rem;">
        <div style="font-size:0.72rem;color:#E8290B;letter-spacing:0.12em;margin-bottom:0.5rem;font-weight:600;">XAI / META / GROQ</div>
        <div style="font-size:0.88rem;color:rgba(255,255,255,0.7);font-family:'Inter',sans-serif;line-height:1.9;">Grok-1<br>Llama 3 70B<br>Mixtral 8x7B</div>
      </div>
    </div>
  </div>
</div>
""")

    # ── RAG PIPELINE ─────────────────────────────────────────────────────
    _md("""
<div style="background:#1C1C1C;padding:4rem 2rem;font-family:'Syne',sans-serif;">
  <div style="max-width:860px;margin:0 auto;">
    <div style="font-size:10px;color:#E8290B;letter-spacing:0.2em;margin-bottom:0.75rem;font-weight:600;">— RAG PIPELINE</div>
    <h2 style="font-size:1.8rem;font-weight:800;color:white;letter-spacing:-0.02em;margin:0 0 1rem;">Evaluate RAG, Not Just Chat.</h2>
    <p style="color:rgba(255,255,255,0.45);font-size:0.9rem;line-height:1.7;max-width:620px;font-family:'Inter',sans-serif;margin-bottom:2rem;">Upload your documents, build a ChromaDB vector store, and run retrieval-augmented evaluations. Test grounding accuracy, citation faithfulness, and context window usage.</p>
    <div style="display:flex;gap:0;flex-wrap:wrap;">
      <div style="flex:1;min-width:140px;padding:1.25rem 1.5rem;border:1px solid rgba(255,255,255,0.08);margin:-1px 0 0 -1px;">
        <div style="font-size:0.72rem;color:#E8290B;letter-spacing:0.12em;margin-bottom:0.5rem;font-weight:600;">INGEST</div>
        <div style="font-size:0.82rem;color:rgba(255,255,255,0.5);font-family:'Inter',sans-serif;">PDF · TXT · CSV</div>
      </div>
      <div style="flex:1;min-width:140px;padding:1.25rem 1.5rem;border:1px solid rgba(255,255,255,0.08);margin:-1px 0 0 -1px;">
        <div style="font-size:0.72rem;color:#E8290B;letter-spacing:0.12em;margin-bottom:0.5rem;font-weight:600;">EMBED</div>
        <div style="font-size:0.82rem;color:rgba(255,255,255,0.5);font-family:'Inter',sans-serif;">ChromaDB Vector Store</div>
      </div>
      <div style="flex:1;min-width:140px;padding:1.25rem 1.5rem;border:1px solid rgba(255,255,255,0.08);margin:-1px 0 0 -1px;">
        <div style="font-size:0.72rem;color:#E8290B;letter-spacing:0.12em;margin-bottom:0.5rem;font-weight:600;">RETRIEVE</div>
        <div style="font-size:0.82rem;color:rgba(255,255,255,0.5);font-family:'Inter',sans-serif;">Semantic search · Top-K</div>
      </div>
      <div style="flex:1;min-width:140px;padding:1.25rem 1.5rem;border:1px solid rgba(255,255,255,0.08);margin:-1px 0 0 -1px;">
        <div style="font-size:0.72rem;color:#E8290B;letter-spacing:0.12em;margin-bottom:0.5rem;font-weight:600;">EVALUATE</div>
        <div style="font-size:0.82rem;color:rgba(255,255,255,0.5);font-family:'Inter',sans-serif;">Faithfulness · Grounding</div>
      </div>
    </div>
  </div>
</div>
""")

    # ── AUTH SECTION ─────────────────────────────────────────────────────
    _md("""
<div style="background:#0E0E0E;padding:4rem 2rem 1.5rem;font-family:'Syne',sans-serif;border-top:1px solid rgba(255,255,255,0.06);">
  <div style="max-width:400px;margin:0 auto;text-align:center;">
    <div style="font-size:10px;color:#E8290B;letter-spacing:0.2em;margin-bottom:0.75rem;font-weight:600;">— GET STARTED</div>
    <h2 style="font-size:1.8rem;font-weight:800;color:white;letter-spacing:-0.02em;margin:0 0 0.5rem;">Sign In.</h2>
    <p style="color:rgba(255,255,255,0.35);font-size:0.82rem;font-family:'Inter',sans-serif;margin-bottom:2rem;">Access your evaluation dashboard.</p>
  </div>
</div>
""")

    # ── NATIVE STREAMLIT FORM ────────────────────────────────────────────
    _, fc, _ = st.columns([2, 3, 2])
    with fc:
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submitted = st.form_submit_button("SIGN IN →", use_container_width=True)

    if submitted:
        user = _authenticate(username, password)
        if user:
            st.session_state["logged_in"] = True
            st.session_state["user"] = user
            st.rerun()
        else:
            st.error("Invalid username or password.")

    # ── DEMO HINT ─────────────────────────────────────────────────────────
    _md("""
<div style="max-width:400px;margin:0 auto;text-align:center;padding:1rem 2rem 0.5rem;">
  <p style="font-size:0.75rem;color:rgba(255,255,255,0.2);font-family:'Inter',sans-serif;">Demo: <code style="color:rgba(255,255,255,0.35);background:rgba(255,255,255,0.05);padding:1px 5px;">TestUser</code> / <code style="color:rgba(255,255,255,0.35);background:rgba(255,255,255,0.05);padding:1px 5px;">User123</code></p>
</div>
""")

    # ── FOOTER ────────────────────────────────────────────────────────────
    _md("""
<div style="background:#0E0E0E;padding:3rem 2rem;font-family:'Syne',sans-serif;border-top:1px solid rgba(255,255,255,0.08);margin-top:2rem;">
  <div style="max-width:860px;margin:0 auto;text-align:center;">
    <div style="display:flex;justify-content:center;gap:2rem;margin-bottom:2rem;flex-wrap:wrap;">
      <a href="#how-it-works" style="font-size:0.78rem;color:rgba(255,255,255,0.35);text-decoration:none;font-family:'Inter',sans-serif;letter-spacing:0.05em;">How it works</a>
      <a href="#trust-dimensions" style="font-size:0.78rem;color:rgba(255,255,255,0.35);text-decoration:none;font-family:'Inter',sans-serif;letter-spacing:0.05em;">Trust dimensions</a>
      <a href="#models" style="font-size:0.78rem;color:rgba(255,255,255,0.35);text-decoration:none;font-family:'Inter',sans-serif;letter-spacing:0.05em;">Models</a>
      <a href="#sign-in" style="font-size:0.78rem;color:rgba(255,255,255,0.35);text-decoration:none;font-family:'Inter',sans-serif;letter-spacing:0.05em;">Sign in</a>
    </div>
    <div style="width:40px;height:1px;background:#E8290B;margin:0 auto 1.5rem;"></div>
    <p style="font-size:0.75rem;color:rgba(255,255,255,0.2);font-family:'Inter',sans-serif;line-height:1.9;margin:0;">
      &copy; 2025 TrustLLM &middot; AI Model Evaluation Platform &middot; Powered by ChromaDB &middot; Groq &middot; Streamlit<br>
      Built by <a href="https://www.linkedin.com/in/monika-kushwaha-52443735/" target="_blank" style="color:#E8290B;text-decoration:none;">Monika Kushwaha</a>
    </p>
  </div>
</div>
""")



# -----------------------------------------------
# ONBOARDING FLOW  —  VERDICT style
# -----------------------------------------------
def _step_indicator(current: int, total: int = 3):
    dots = ""
    for i in range(1, total + 1):
        if i < current:
            cls = "done"
        elif i == current:
            cls = "active"
        else:
            cls = ""
        dots += f'<div class="step-dot {cls}"></div>'
    st.markdown(
        f'<div class="step-track">{dots}'
        f'<span style="font-size:0.72rem;color:#888888;margin-left:8px;font-family:Inter,sans-serif;">Step {current} of {total}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _show_onboarding():
    step = st.session_state.get("onboarding_step", 1)

    st.markdown(_h("""
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .stApp { background: #F9F8F6 !important; }
        section.main .block-container {
            max-width: 720px !important;
            padding-top: 4vh !important;
            margin: 0 auto;
        }
        div[data-testid="stCheckbox"] label,
        div[data-testid="stCheckbox"] label p,
        div[data-testid="stCheckbox"] label span {
            color: #0E0E0E !important;
            font-size: 0.875rem !important;
            font-weight: 500 !important;
        }
        </style>
        <link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
    """), unsafe_allow_html=True)

    # ── Step 1: Welcome ────────────────────────────────────────────────
    if step == 1:
        st.markdown(_h("""
            <div style="text-align:center;margin-bottom:2.5rem;">
              <div style="background:#E8290B;width:56px;height:56px;
                          display:inline-flex;align-items:center;justify-content:center;
                          font-family:'Syne',sans-serif;font-size:28px;font-weight:800;color:white;
                          margin-bottom:1.25rem;">T</div>
              <div style="font-family:'Syne',sans-serif;font-size:9px;letter-spacing:0.2em;
                          color:#E8290B;margin-bottom:0.75rem;">— GETTING STARTED</div>
              <h1 style="color:#0E0E0E;font-size:2rem;font-weight:800;font-family:'Syne',sans-serif;
                         letter-spacing:-0.025em;margin:0 0 0.5rem 0;">Welcome to TrustLLM.</h1>
              <p style="color:#888888;font-size:0.9rem;max-width:480px;margin:0 auto;
                        line-height:1.6;font-family:'Inter',sans-serif;">
                Let's get your evaluation workspace ready in
                <strong style="color:#E8290B;">2 quick steps.</strong>
                Your first eval takes less than a minute.
              </p>
            </div>
        """), unsafe_allow_html=True)

        _step_indicator(1)

        col1, col2, col3 = st.columns(3)
        cards = [
            ("📊", "Trace & Observe", "Inspect every prompt and response in real time"),
            ("⚡", "Run Evals", "Score outputs with LLM judges and custom scorers"),
            ("🏆", "Compare Models", "Rank models by trust score, safety & cost"),
        ]
        for col, (icon, title, desc) in zip([col1, col2, col3], cards):
            with col:
                st.markdown(_h(f"""
                    <div style="background:white;border:1px solid #E4E2DC;border-radius:0;
                                padding:1.25rem;text-align:center;">
                      <div style="font-size:1.5rem;margin-bottom:0.6rem;">{icon}</div>
                      <div style="font-weight:800;font-size:0.85rem;color:#0E0E0E;
                                  font-family:'Syne',sans-serif;margin-bottom:0.3rem;">{title}</div>
                      <div style="font-size:0.75rem;color:#888888;line-height:1.4;
                                  font-family:'Inter',sans-serif;">{desc}</div>
                    </div>
                """), unsafe_allow_html=True)

        st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)

        _, btn_col, _ = st.columns([1, 2, 1])
        with btn_col:
            if st.button("Let's get started →", use_container_width=True, key="ob_step1"):
                st.session_state["onboarding_step"] = 2
                st.rerun()

        _, skip_col, _ = st.columns([1, 2, 1])
        with skip_col:
            st.markdown('<div class="btn-secondary">', unsafe_allow_html=True)
            if st.button("Skip setup — go to dashboard", key="ob_skip", use_container_width=True):
                st.session_state["onboarding_complete"] = True
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    # ── Step 2: Evaluation focus ───────────────────────────────────────
    elif step == 2:
        st.markdown(_h("""
            <div style="font-family:'Syne',sans-serif;font-size:9px;letter-spacing:0.2em;
                        color:#E8290B;margin-bottom:0.5rem;">— STEP TWO</div>
            <h1 style="color:#0E0E0E;font-size:1.8rem;font-weight:800;font-family:'Syne',sans-serif;
                       letter-spacing:-0.025em;margin:0 0 0.4rem 0;">What will you evaluate?</h1>
            <p style="color:#888888;font-size:0.9rem;margin:0 0 1.5rem 0;line-height:1.6;
                      font-family:'Inter',sans-serif;">
              Select one or more evaluation categories. You can change this later.
            </p>
        """), unsafe_allow_html=True)

        _step_indicator(2)

        focus_options = [
            ("safety",        "🔒", "Safety Testing",  "Jailbreak resistance, harmful content detection"),
            ("factual",       "📋", "Factual QA",       "Accuracy, reasoning, knowledge retrieval"),
            ("bias",          "⚖️", "Bias Audit",       "Fairness, demographic bias, toxicity"),
            ("hallucination", "🔍", "Hallucination",    "Grounding, factual consistency, RAG fidelity"),
            ("reasoning",     "🧠", "Reasoning",        "Multi-step logic, chain-of-thought quality"),
        ]

        selected = st.session_state.get("ob_focus", [])
        new_selected = []

        for row_start in range(0, len(focus_options), 3):
            row = focus_options[row_start:row_start + 3]
            cols = st.columns(3)
            for col, (key, icon, title, desc) in zip(cols, row):
                is_sel = key in selected
                with col:
                    border = "#E8290B" if is_sel else "#E4E2DC"
                    bg = "#FEF2F0" if is_sel else "white"
                    st.markdown(_h(f"""
                        <div style="background:{bg};border:2px solid {border};border-radius:0;
                                    padding:1rem 1rem 0.25rem 1rem;">
                          <div style="font-size:1.4rem;margin-bottom:0.3rem;">{icon}</div>
                          <div style="font-weight:800;font-size:0.85rem;color:#0E0E0E;
                                      font-family:'Syne',sans-serif;margin-bottom:0.2rem;">{title}</div>
                          <div style="font-size:0.72rem;color:#888888;line-height:1.4;
                                      margin-bottom:0.5rem;font-family:'Inter',sans-serif;">{desc}</div>
                        </div>
                    """), unsafe_allow_html=True)
                    checked = st.checkbox(
                        title,
                        value=is_sel,
                        key=f"ob_focus_{key}",
                        label_visibility="collapsed",
                    )
                    if checked:
                        new_selected.append(key)

        st.session_state["ob_focus"] = new_selected

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        _, btn_col, _ = st.columns([1, 2, 1])
        with btn_col:
            if st.button(
                "Continue →",
                use_container_width=True,
                key="ob_step2",
                disabled=(len(new_selected) == 0),
            ):
                st.session_state["onboarding_step"] = 3
                st.rerun()

        _, back_col, _ = st.columns([1, 2, 1])
        with back_col:
            st.markdown('<div class="btn-secondary">', unsafe_allow_html=True)
            if st.button("← Back", key="ob_back2", use_container_width=True):
                st.session_state["onboarding_step"] = 1
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    # ── Step 3: Model selection ────────────────────────────────────────
    elif step == 3:
        st.markdown(_h("""
            <div style="font-family:'Syne',sans-serif;font-size:9px;letter-spacing:0.2em;
                        color:#E8290B;margin-bottom:0.5rem;">— STEP THREE</div>
            <h1 style="color:#0E0E0E;font-size:1.8rem;font-weight:800;font-family:'Syne',sans-serif;
                       letter-spacing:-0.025em;margin:0 0 0.4rem 0;">Which models will you evaluate?</h1>
            <p style="color:#888888;font-size:0.9rem;margin:0 0 1.5rem 0;line-height:1.6;
                      font-family:'Inter',sans-serif;">
              Choose AI models to benchmark. You can add more later from the evaluation page.
            </p>
        """), unsafe_allow_html=True)

        _step_indicator(3)

        model_options = [
            ("gpt",        "GPT-4o",     "OpenAI",     "Versatile, strong reasoning"),
            ("claude",     "Claude 3",   "Anthropic",  "Safety-first, long context"),
            ("gemini-pro", "Gemini Pro", "Google",     "Multimodal, fast inference"),
            ("mistral",    "Mistral 7B", "Mistral AI", "Open-source, efficient"),
            ("phi3",       "Phi-3",      "Microsoft",  "Compact, high accuracy"),
            ("llama",      "LLaMA 3",    "Meta",       "Open-source, customizable"),
        ]

        selected_models = st.session_state.get("ob_models", ["gpt", "claude"])
        new_models = []

        for row_start in range(0, len(model_options), 3):
            row = model_options[row_start:row_start + 3]
            cols = st.columns(3)
            for col, (key, name, vendor, desc) in zip(cols, row):
                is_sel = key in selected_models
                with col:
                    st.markdown(_h(f"""
                        <div style="background:{'#FEF2F0' if is_sel else 'white'};
                                    border:2px solid {'#E8290B' if is_sel else '#E4E2DC'};
                                    border-radius:0;padding:0.9rem 1rem 0.25rem 1rem;">
                          <div style="font-weight:800;font-size:0.9rem;color:#0E0E0E;
                                      font-family:'Syne',sans-serif;">{name}</div>
                          <div style="font-size:0.7rem;color:#E8290B;font-weight:700;
                                      font-family:'Syne',sans-serif;margin:0.1rem 0 0.3rem;">{vendor}</div>
                          <div style="font-size:0.72rem;color:#888888;line-height:1.3;
                                      margin-bottom:0.5rem;font-family:'Inter',sans-serif;">{desc}</div>
                        </div>
                    """), unsafe_allow_html=True)
                    checked = st.checkbox(
                        name,
                        value=is_sel,
                        key=f"ob_model_{key}",
                        label_visibility="collapsed",
                    )
                    if checked:
                        new_models.append(key)

        st.session_state["ob_models"] = new_models

        if new_models:
            focus_labels = {
                "safety": "Safety", "factual": "Factual QA", "bias": "Bias Audit",
                "hallucination": "Hallucination", "reasoning": "Reasoning",
            }
            focus_str = ", ".join(
                focus_labels.get(f, f) for f in st.session_state.get("ob_focus", [])
            ) or "All categories"
            model_str = ", ".join(m.upper() for m in new_models)
            st.markdown(_h(f"""
                <div style="background:#F0FDF4;border:1px solid #BBF7D0;border-radius:0;
                            padding:1rem 1.25rem;margin:1rem 0;">
                  <div style="font-size:0.78rem;font-weight:700;color:#15803D;
                              font-family:'Syne',sans-serif;letter-spacing:0.04em;margin-bottom:0.35rem;">
                    ✓ WORKSPACE IS READY
                  </div>
                  <div style="font-size:0.82rem;color:#166534;font-family:'Inter',sans-serif;">
                    <strong>Focus:</strong> {focus_str}<br>
                    <strong>Models:</strong> {model_str}
                  </div>
                </div>
            """), unsafe_allow_html=True)

        _, btn_col, _ = st.columns([1, 2, 1])
        with btn_col:
            if st.button(
                "Launch Dashboard →",
                use_container_width=True,
                key="ob_launch",
                disabled=(len(new_models) == 0),
            ):
                st.session_state["onboarding_complete"] = True
                st.session_state["project_categories"] = st.session_state.get("ob_focus") or None
                st.rerun()

        _, back_col, _ = st.columns([1, 2, 1])
        with back_col:
            st.markdown('<div class="btn-secondary">', unsafe_allow_html=True)
            if st.button("← Back", key="ob_back3", use_container_width=True):
                st.session_state["onboarding_step"] = 2
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)


# -----------------------------------------------
# AUTH GATE
# -----------------------------------------------
if not st.session_state.get("logged_in"):
    _show_login()
    st.stop()

# -----------------------------------------------
# ONBOARDING GATE
# -----------------------------------------------
if not st.session_state.get("onboarding_complete"):
    _show_onboarding()
    st.stop()


# ===============================================
# AUTHENTICATED APP
# ===============================================

with open(BASE_DIR / "projects.json") as _pf:
    _projects_data = json.load(_pf)["projects"]
_project_names = ["All Projects"] + [p["name"] for p in _projects_data]

# -----------------------------------------------
# TOP HEADER BAR  —  VERDICT style
# -----------------------------------------------
header = st.container()
with header:
    h1, h2, h3, h4, h5 = st.columns([1.2, 2, 2, 0.8, 0.8])
    with h1:
        st.markdown(_h("""
            <div style="display:flex;align-items:center;gap:8px;padding-top:0.3rem;">
              <div style="background:#E8290B;width:26px;height:26px;
                          display:flex;align-items:center;justify-content:center;
                          font-family:'Syne',sans-serif;font-size:13px;font-weight:800;color:white;">T</div>
              <span style="font-weight:800;color:#0E0E0E;font-size:0.95rem;
                           font-family:'Syne',sans-serif;letter-spacing:0.02em;">TrustLLM</span>
            </div>
        """), unsafe_allow_html=True)
    with h2:
        selected_project = st.selectbox("Project", _project_names, label_visibility="collapsed")
    with h3:
        selected_env = st.selectbox(
            "Environment", ["production", "staging", "development"], label_visibility="collapsed"
        )
    with h4:
        st.markdown(
            '<a href="https://github.com/" target="_blank" class="header-btn">DOCS</a>',
            unsafe_allow_html=True,
        )
    with h5:
        st.markdown('<a href="#compare" class="header-btn">COMPARE</a>', unsafe_allow_html=True)

st.markdown('<hr class="header-divider">', unsafe_allow_html=True)

_selected_categories = None
if selected_project != "All Projects":
    for p in _projects_data:
        if p["name"] == selected_project:
            _selected_categories = p["categories"]
            break

st.session_state["project_categories"] = _selected_categories

# -----------------------------------------------
# SIDEBAR  —  VERDICT style
# -----------------------------------------------
user = st.session_state["user"]

st.sidebar.markdown(_h(f"""
    <div style="padding:0.75rem 0 0.5rem 0;">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:1rem;padding:0 4px;">
        <div style="background:#E8290B;width:32px;height:32px;
                    display:flex;align-items:center;justify-content:center;
                    font-family:'Syne',sans-serif;font-size:16px;font-weight:800;color:white;">T</div>
        <div>
          <div style="font-size:0.95rem;font-weight:800;color:white;
                      font-family:'Syne',sans-serif;letter-spacing:0.02em;">TrustLLM</div>
          <div style="font-size:7px;color:rgba(255,255,255,0.2);letter-spacing:0.15em;
                      font-family:'Syne',sans-serif;">EVAL PLATFORM</div>
        </div>
      </div>
      <div style="display:flex;align-items:center;gap:8px;padding:0.65rem 0.75rem;
                  background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.07);
                  margin-bottom:0.5rem;">
        <div style="background:#E8290B;width:30px;height:30px;
                    display:flex;align-items:center;justify-content:center;
                    font-family:'Syne',sans-serif;font-size:13px;font-weight:800;
                    color:white;flex-shrink:0;">
          {user['display_name'][0].upper()}
        </div>
        <div>
          <div style="font-size:0.82rem;font-weight:700;color:rgba(255,255,255,0.85);
                      font-family:'Syne',sans-serif;line-height:1.2;">{user['display_name']}</div>
          <div style="font-size:0.68rem;color:rgba(255,255,255,0.3);
                      font-family:'Syne',sans-serif;letter-spacing:0.08em;
                      text-transform:uppercase;">{user.get('role','viewer')}</div>
        </div>
      </div>
    </div>
"""), unsafe_allow_html=True)

if "page" not in st.session_state:
    st.session_state["page"] = "Overview"

_nav_css = _h("""
    <style>
    section[data-testid="stSidebar"] div[data-testid="stButton"] button {
        background: transparent !important;
        color: rgba(255,255,255,0.45) !important;
        border: none !important;
        border-left: 3px solid transparent !important;
        text-align: left !important;
        padding: 0.4rem 0.75rem !important;
        font-size: 0.82rem !important;
        font-weight: 500 !important;
        border-radius: 0 !important;
        box-shadow: none !important;
        width: 100%;
        justify-content: flex-start !important;
        font-family: 'Inter', sans-serif !important;
        text-transform: none !important;
        letter-spacing: 0.01em !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stButton"] button:hover {
        background: rgba(255,255,255,0.04) !important;
        color: rgba(255,255,255,0.8) !important;
        box-shadow: none !important;
    }
    section[data-testid="stSidebar"] .nav-active div[data-testid="stButton"] button {
        background: rgba(232,41,11,0.1) !important;
        color: white !important;
        font-weight: 600 !important;
        border-left: 3px solid #E8290B !important;
    }
    </style>
""")
st.sidebar.markdown(_nav_css, unsafe_allow_html=True)


def _nav_item(label: str, icon: str):
    is_active = st.session_state.get("page") == label
    if is_active:
        st.sidebar.markdown('<div class="nav-active">', unsafe_allow_html=True)
    if st.sidebar.button(f"{icon}  {label}", key=f"nav_{label}", use_container_width=True):
        st.session_state["page"] = label
        st.rerun()
    if is_active:
        st.sidebar.markdown("</div>", unsafe_allow_html=True)


st.sidebar.markdown('<p class="nav-section">MONITOR</p>', unsafe_allow_html=True)
_nav_item("Overview", "◎")
_nav_item("Failure Analysis", "✕")

st.sidebar.markdown('<p class="nav-section">EVALUATE</p>', unsafe_allow_html=True)
_nav_item("Run Evaluation", "▶")
_nav_item("Leaderboard", "🏆")
_nav_item("Agent Performance", "⚡")

st.sidebar.markdown('<p class="nav-section">DATA</p>', unsafe_allow_html=True)
_nav_item("Prompt Explorer", "🔍")
_nav_item("Prompt Dataset", "📂")
_nav_item("RAG Testing", "🧪")

st.sidebar.divider()

if st.sidebar.button("Sign out", use_container_width=True):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

st.sidebar.markdown(_h("""
    <p style="font-size:0.65rem;color:rgba(255,255,255,0.15);text-align:center;
              margin-top:0.5rem;font-family:'Syne',sans-serif;letter-spacing:0.08em;">
      TRUSTLLM · LLM EVAL TOOLKIT
    </p>
"""), unsafe_allow_html=True)

page = st.session_state.get("page", "Overview")

# -----------------------------------------------
# PAGE ROUTER
# -----------------------------------------------
if page == "Overview":
    overview()
elif page == "Failure Analysis":
    failure_analysis()
elif page == "Run Evaluation":
    run_eval()
elif page == "Leaderboard":
    leaderboard()
elif page == "Agent Performance":
    agent_performance()
elif page == "Prompt Explorer":
    prompt_explorer()
elif page == "Prompt Dataset":
    prompt_dataset()
elif page == "RAG Testing":
    rag_testing()
