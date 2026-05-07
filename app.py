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
# LOGIN PAGE
# -----------------------------------------------
def _show_login():
    st.markdown(_h("""
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header[data-testid="stHeader"] {visibility: hidden;}
        .stApp { background: #ffffff !important; }
        section.main .block-container {
            padding: 0 !important;
            max-width: 100% !important;
        }
        /* form card inputs */
        [data-testid="stForm"] {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            padding: 0 !important;
        }
        [data-testid="stForm"] label {
            color: #374151 !important;
            font-size: 0.875rem !important;
            font-weight: 500 !important;
        }
        [data-testid="stForm"] input {
            background-color: #f9fafb !important;
            border: 1px solid #e5e7eb !important;
            color: #111827 !important;
            border-radius: 8px !important;
            font-size: 0.95rem !important;
        }
        [data-testid="stForm"] input:focus {
            border-color: #4f46e5 !important;
            box-shadow: 0 0 0 3px rgba(79,70,229,0.12) !important;
        }
        [data-testid="stForm"] .stButton > button {
            background-color: #4f46e5 !important;
            color: white !important;
            font-weight: 600 !important;
            font-size: 1rem !important;
            padding: 0.7rem 1rem !important;
            border-radius: 8px !important;
            border: none !important;
            width: 100%;
        }
        [data-testid="stForm"] .stButton > button:hover {
            background-color: #4338ca !important;
        }
        </style>
    """), unsafe_allow_html=True)

    # ── STICKY TOP NAV ────────────────────────────────────────────────
    st.markdown(_h("""
        <div style="position:sticky;top:0;z-index:200;background:rgba(255,255,255,0.95);
                    backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);
                    border-bottom:1px solid #e5e7eb;
                    padding:0 3rem;height:64px;display:flex;align-items:center;
                    justify-content:space-between;">
        <div style="display:flex;align-items:center;gap:0.6rem;">
        <div style="background:#4f46e5;width:32px;height:32px;border-radius:8px;
                    display:flex;align-items:center;justify-content:center;font-size:1rem;color:white;">🛡</div>
        <span style="font-weight:800;font-size:1.1rem;color:#111827;letter-spacing:-0.02em;">TrustLLM</span>
        </div>
        <div style="display:flex;align-items:center;gap:0.75rem;">
        <a href="#signin-section"
           style="color:#6b7280;text-decoration:none;font-size:0.9rem;font-weight:500;
                  padding:0.4rem 0.9rem;border-radius:7px;border:1px solid #e5e7eb;
                  background:white;">Sign in</a>
        <a href="#signin-section"
           style="background:#4f46e5;color:white;text-decoration:none;font-size:0.9rem;
                  font-weight:600;padding:0.4rem 1rem;border-radius:7px;">Get started →</a>
        </div>
        </div>
    """), unsafe_allow_html=True)

    # ── HERO SECTION ─────────────────────────────────────────────────
    st.markdown(_h("""
        <div style="text-align:center;padding:5rem 2rem 3rem;
                    background:linear-gradient(180deg,#fafbff 0%,#ffffff 100%);">
        <div style="display:inline-flex;align-items:center;gap:0.45rem;
                    background:#eef2ff;border:1px solid #c7d2fe;
                    color:#4f46e5;font-size:0.75rem;font-weight:700;letter-spacing:0.06em;
                    padding:0.3rem 0.9rem;border-radius:20px;margin-bottom:1.75rem;">
        ✦ LLM EVALUATION PLATFORM
        </div>
        <div style="font-size:5rem;font-weight:900;color:#111827;line-height:1.05;
                    letter-spacing:-0.04em;margin:0 0 0.15em 0;">
        Evaluate LLMs
        </div>
        <div style="font-size:5rem;font-weight:900;line-height:1.05;
                    letter-spacing:-0.04em;margin:0 0 1.5rem 0;
                    background:linear-gradient(135deg,#4f46e5 0%,#7c3aed 100%);
                    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                    background-clip:text;">
        you can actually trust.
        </div>
        <div style="font-size:1.25rem;color:#6b7280;line-height:1.7;
                    max-width:600px;margin:0 auto 2.5rem;">
        Score every model response for correctness, safety, and hallucination.
        Surface failures fast. Ship with confidence.
        </div>
        <div style="display:flex;justify-content:center;gap:1rem;flex-wrap:wrap;">
        <a href="#signin-section"
           style="background:#4f46e5;color:white;text-decoration:none;
                  font-size:1rem;font-weight:600;padding:0.8rem 2rem;
                  border-radius:8px;display:inline-block;">
        Start evaluating →
        </a>
        <a href="#features-section"
           style="background:white;color:#374151;text-decoration:none;border:1px solid #d1d5db;
                  font-size:1rem;font-weight:500;padding:0.8rem 2rem;
                  border-radius:8px;display:inline-block;">
        See how it works
        </a>
        </div>
        </div>
    """), unsafe_allow_html=True)

    # ── FEATURES SECTION ──────────────────────────────────────────────
    st.markdown(_h("""
        <div id="features-section"
             style="padding:4rem 3rem;background:#f8fafc;
                    border-top:1px solid #e5e7eb;border-bottom:1px solid #e5e7eb;">
        <div style="max-width:960px;margin:0 auto;">
        <div style="text-align:center;margin-bottom:3rem;">
        <div style="font-size:0.75rem;font-weight:700;color:#4f46e5;letter-spacing:0.08em;
                    text-transform:uppercase;margin-bottom:0.75rem;">WHAT YOU GET</div>
        <div style="font-size:2rem;font-weight:800;color:#111827;letter-spacing:-0.025em;">
        Everything you need to trust your LLMs
        </div>
        </div>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:2rem;">
        <div style="background:white;border:1px solid #e5e7eb;border-radius:14px;padding:1.75rem;
                    box-shadow:0 1px 4px rgba(0,0,0,0.04);">
        <div style="background:#eef2ff;width:44px;height:44px;border-radius:10px;
                    display:flex;align-items:center;justify-content:center;
                    font-size:1.25rem;margin-bottom:1rem;">📊</div>
        <div style="font-weight:700;font-size:1rem;color:#111827;margin-bottom:0.5rem;">Trace everything</div>
        <div style="font-size:0.9rem;color:#6b7280;line-height:1.6;">
        Inspect every prompt, response &amp; tool call in real time. Full observability across all models.
        </div>
        </div>
        <div style="background:white;border:1px solid #e5e7eb;border-radius:14px;padding:1.75rem;
                    box-shadow:0 1px 4px rgba(0,0,0,0.04);">
        <div style="background:#eef2ff;width:44px;height:44px;border-radius:10px;
                    display:flex;align-items:center;justify-content:center;
                    font-size:1.25rem;margin-bottom:1rem;">⚡</div>
        <div style="font-weight:700;font-size:1rem;color:#111827;margin-bottom:0.5rem;">Measure with evals</div>
        <div style="font-size:0.9rem;color:#6b7280;line-height:1.6;">
        Score outputs for safety, factual accuracy, bias, and hallucination. Compare models side-by-side.
        </div>
        </div>
        <div style="background:white;border:1px solid #e5e7eb;border-radius:14px;padding:1.75rem;
                    box-shadow:0 1px 4px rgba(0,0,0,0.04);">
        <div style="background:#eef2ff;width:44px;height:44px;border-radius:10px;
                    display:flex;align-items:center;justify-content:center;
                    font-size:1.25rem;margin-bottom:1rem;">🏆</div>
        <div style="font-weight:700;font-size:1rem;color:#111827;margin-bottom:0.5rem;">Compare &amp; improve</div>
        <div style="font-size:0.9rem;color:#6b7280;line-height:1.6;">
        Rank models by trust score, safety &amp; cost. Surface failures fast and iterate with confidence.
        </div>
        </div>
        </div>
        </div>
        </div>
    """), unsafe_allow_html=True)

    # ── STATS STRIP ───────────────────────────────────────────────────
    st.markdown(_h("""
        <div style="background:#111827;padding:3.5rem 3rem;">
        <div style="max-width:700px;margin:0 auto;
                    display:grid;grid-template-columns:repeat(3,1fr);gap:2rem;text-align:center;">
        <div>
        <div style="font-size:3.5rem;font-weight:900;color:white;letter-spacing:-0.04em;line-height:1;">161</div>
        <div style="color:#6b7280;font-size:0.9rem;margin-top:0.4rem;">Prompts evaluated</div>
        </div>
        <div>
        <div style="font-size:3.5rem;font-weight:900;color:white;letter-spacing:-0.04em;line-height:1;">6</div>
        <div style="color:#6b7280;font-size:0.9rem;margin-top:0.4rem;">Models tested</div>
        </div>
        <div>
        <div style="font-size:3.5rem;font-weight:900;color:white;letter-spacing:-0.04em;line-height:1;">0.76</div>
        <div style="color:#6b7280;font-size:0.9rem;margin-top:0.4rem;">Avg trust score</div>
        </div>
        </div>
        </div>
    """), unsafe_allow_html=True)

    # ── SIGN-IN SECTION ───────────────────────────────────────────────
    st.markdown(_h("""
        <div id="signin-section"
             style="padding:5rem 2rem 2rem;background:#f8fafc;
                    border-top:1px solid #e5e7eb;">
        <div style="max-width:440px;margin:0 auto;">
        <div style="text-align:center;margin-bottom:2rem;">
        <div style="background:#4f46e5;width:48px;height:48px;border-radius:12px;
                    display:inline-flex;align-items:center;justify-content:center;
                    font-size:1.4rem;color:white;margin-bottom:1rem;">🛡</div>
        <div style="font-size:1.75rem;font-weight:800;color:#111827;letter-spacing:-0.025em;margin-bottom:0.3rem;">
        Welcome back
        </div>
        <div style="font-size:0.95rem;color:#6b7280;">Sign in to your TrustLLM account</div>
        </div>
        </div>
        </div>
    """), unsafe_allow_html=True)

    # ── FORM CARD (centered column) ───────────────────────────────────
    _, form_col, _ = st.columns([1, 2, 1])
    with form_col:
        # Social buttons
        st.markdown(_h("""
            <div style="background:white;border:1px solid #e5e7eb;border-radius:16px;
                        padding:2rem;box-shadow:0 4px 24px rgba(0,0,0,0.06);margin-bottom:1.5rem;">
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;margin-bottom:1.25rem;">
            <button style="background:white;color:#374151;border:1px solid #d1d5db;border-radius:8px;
                           padding:0.7rem 0.5rem;font-size:0.875rem;font-weight:500;cursor:pointer;
                           width:100%;font-family:inherit;"
                    onclick="var b=this;b.textContent='Not available in demo';
                             setTimeout(function(){b.textContent='🔵 Continue with Google'},2500)">
            🔵 Continue with Google
            </button>
            <button style="background:#24292e;color:white;border:1px solid #1b1f23;border-radius:8px;
                           padding:0.7rem 0.5rem;font-size:0.875rem;font-weight:500;cursor:pointer;
                           width:100%;font-family:inherit;"
                    onclick="var b=this;b.textContent='Not available in demo';
                             setTimeout(function(){b.textContent='⬛ Continue with GitHub'},2500)">
            ⬛ Continue with GitHub
            </button>
            </div>
            <div style="display:flex;align-items:center;gap:0.75rem;">
            <div style="flex:1;border-top:1px solid #e5e7eb;"></div>
            <span style="color:#9ca3af;font-size:0.8rem;white-space:nowrap;">or continue with email</span>
            <div style="flex:1;border-top:1px solid #e5e7eb;"></div>
            </div>
            </div>
        """), unsafe_allow_html=True)

        # Credentials form
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submitted = st.form_submit_button("Sign in  →", use_container_width=True)

        if submitted:
            user = _authenticate(username, password)
            if user:
                st.session_state["logged_in"] = True
                st.session_state["user"] = user
                st.rerun()
            else:
                st.error("Invalid username or password.")

        st.markdown(_h("""
            <div style="text-align:center;padding:1rem 0 3rem;">
            <span style="color:#9ca3af;font-size:0.8rem;">
            Demo — Username: <strong style="color:#374151;">TestUser</strong>
            &nbsp;·&nbsp; Password: <strong style="color:#374151;">User123</strong>
            </span>
            </div>
        """), unsafe_allow_html=True)

    # ── FOOTER ────────────────────────────────────────────────────────
    st.markdown(_h("""
        <div style="background:#111827;padding:2rem 3rem;text-align:center;">
        <span style="color:#374151;font-size:0.8rem;">
        © 2025 TrustLLM · AI Model Evaluation Platform ·
        Built by <a href="https://www.linkedin.com/in/monika-kushwaha-52443735/"
        target="_blank" style="color:#6366f1;text-decoration:none;">Monika Kushwaha</a>
        </span>
        </div>
    """), unsafe_allow_html=True)


# -----------------------------------------------
# ONBOARDING FLOW
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
        f'<span style="font-size:0.75rem;color:#9ca3af;margin-left:8px;">Step {current} of {total}</span>'
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
        .stApp { background: #F8FAFC !important; }
        section.main .block-container {
            max-width: 720px !important;
            padding-top: 4vh !important;
            margin: 0 auto;
        }
        div[data-testid="stCheckbox"] label,
        div[data-testid="stCheckbox"] label p,
        div[data-testid="stCheckbox"] label span {
            color: #111827 !important;
            font-size: 0.9rem !important;
            font-weight: 500 !important;
        }
        </style>
    """), unsafe_allow_html=True)

    # ── Step 1: Welcome ────────────────────────────────────────────────
    if step == 1:
        st.markdown(_h("""
            <div style="text-align:center;margin-bottom:2.5rem;">
            <div style="background:#4f46e5;width:56px;height:56px;border-radius:14px;
                        display:inline-flex;align-items:center;justify-content:center;
                        font-size:1.75rem;margin-bottom:1.25rem;
                        box-shadow:0 8px 24px rgba(79,70,229,0.3);">🛡</div>
            <h1 style="color:#111827;font-size:2rem;font-weight:800;letter-spacing:-0.025em;
                       margin:0 0 0.5rem 0;">Welcome to TrustLLM!</h1>
            <p style="color:#6b7280;font-size:1rem;max-width:480px;margin:0 auto;line-height:1.6;">
            Let's get your evaluation workspace ready in
            <strong style="color:#4f46e5;">2 quick steps</strong>.
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
                    <div style="background:white;border:1px solid #e5e7eb;border-radius:12px;
                                padding:1.25rem;text-align:center;
                                box-shadow:0 1px 4px rgba(0,0,0,0.05);">
                    <div style="font-size:1.75rem;margin-bottom:0.6rem;">{icon}</div>
                    <div style="font-weight:600;font-size:0.875rem;color:#111827;margin-bottom:0.3rem;">{title}</div>
                    <div style="font-size:0.78rem;color:#6b7280;line-height:1.4;">{desc}</div>
                    </div>
                """), unsafe_allow_html=True)

        st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)

        _, btn_col, _ = st.columns([1, 2, 1])
        with btn_col:
            if st.button("Let's get started  →", use_container_width=True, key="ob_step1"):
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
            <h1 style="color:#111827;font-size:1.8rem;font-weight:800;letter-spacing:-0.025em;
                       margin:0 0 0.4rem 0;">What will you evaluate?</h1>
            <p style="color:#6b7280;font-size:0.95rem;margin:0 0 1.5rem 0;line-height:1.6;">
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
                    # Card frame
                    border = "#4f46e5" if is_sel else "#e5e7eb"
                    bg = "#eef2ff" if is_sel else "white"
                    st.markdown(_h(f"""
                        <div style="background:{bg};border:2px solid {border};border-radius:12px;
                                    padding:1rem 1rem 0.25rem 1rem;
                                    box-shadow:0 1px 4px rgba(0,0,0,0.04);">
                        <div style="font-size:1.5rem;margin-bottom:0.3rem;">{icon}</div>
                        <div style="font-weight:700;font-size:0.9rem;color:#111827;margin-bottom:0.2rem;">{title}</div>
                        <div style="font-size:0.75rem;color:#6b7280;line-height:1.4;margin-bottom:0.5rem;">{desc}</div>
                        </div>
                    """), unsafe_allow_html=True)
                    # Checkbox sits just below the card (no label so card is the visual)
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
                "Continue  →",
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
            <h1 style="color:#111827;font-size:1.8rem;font-weight:800;letter-spacing:-0.025em;
                       margin:0 0 0.4rem 0;">Which models will you evaluate?</h1>
            <p style="color:#6b7280;font-size:0.95rem;margin:0 0 1.5rem 0;line-height:1.6;">
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
                        <div style="background:{'#eef2ff' if is_sel else 'white'};
                                    border:2px solid {'#4f46e5' if is_sel else '#e5e7eb'};
                                    border-radius:10px;padding:0.9rem 1rem 0.25rem 1rem;
                                    box-shadow:0 1px 4px rgba(0,0,0,0.04);">
                        <div style="font-weight:700;font-size:0.9rem;color:#111827;">{name}</div>
                        <div style="font-size:0.7rem;color:#4f46e5;font-weight:600;margin:0.1rem 0 0.3rem;">{vendor}</div>
                        <div style="font-size:0.75rem;color:#6b7280;line-height:1.3;margin-bottom:0.5rem;">{desc}</div>
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
                <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;
                            padding:1rem 1.25rem;margin:1rem 0;">
                <div style="font-size:0.78rem;font-weight:600;color:#15803d;margin-bottom:0.35rem;">
                ✓ Your workspace is ready
                </div>
                <div style="font-size:0.82rem;color:#166534;">
                <strong>Focus:</strong> {focus_str}<br>
                <strong>Models:</strong> {model_str}
                </div>
                </div>
            """), unsafe_allow_html=True)

        _, btn_col, _ = st.columns([1, 2, 1])
        with btn_col:
            if st.button(
                "🚀  Launch Dashboard",
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
# TOP HEADER BAR
# -----------------------------------------------
header = st.container()
with header:
    h1, h2, h3, h4, h5 = st.columns([1.2, 2, 2, 0.8, 0.8])
    with h1:
        st.markdown(_h("""
            <div style="display:flex;align-items:center;gap:0.5rem;padding-top:0.3rem;">
            <div style="background:#4f46e5;width:24px;height:24px;border-radius:5px;
                        display:flex;align-items:center;justify-content:center;font-size:0.75rem;">🛡</div>
            <span style="font-weight:700;color:#111827;font-size:0.95rem;letter-spacing:-0.01em;">TrustLLM</span>
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
            '<a href="https://github.com/" target="_blank" class="header-btn">📖 Docs</a>',
            unsafe_allow_html=True,
        )
    with h5:
        st.markdown('<a href="#compare" class="header-btn">⚖️ Compare</a>', unsafe_allow_html=True)

st.markdown('<hr class="header-divider">', unsafe_allow_html=True)

_selected_categories = None
if selected_project != "All Projects":
    for p in _projects_data:
        if p["name"] == selected_project:
            _selected_categories = p["categories"]
            break

st.session_state["project_categories"] = _selected_categories

# -----------------------------------------------
# SIDEBAR
# -----------------------------------------------
user = st.session_state["user"]

st.sidebar.markdown(_h(f"""
    <div style="padding:0.75rem 0 0.5rem 0;">
    <div style="display:flex;align-items:center;gap:0.6rem;margin-bottom:1rem;">
    <div style="background:#4f46e5;width:28px;height:28px;border-radius:7px;
                display:flex;align-items:center;justify-content:center;font-size:0.85rem;">🛡</div>
    <span style="font-size:1rem;font-weight:700;color:#f1f5f9;letter-spacing:-0.01em;">TrustLLM</span>
    </div>
    <div style="display:flex;align-items:center;gap:0.5rem;padding:0.6rem 0.75rem;
                background:rgba(255,255,255,0.05);border-radius:8px;margin-bottom:0.5rem;">
    <div style="background:#334155;width:30px;height:30px;border-radius:50%;
                display:flex;align-items:center;justify-content:center;
                font-size:0.8rem;font-weight:700;color:#e2e8f0;flex-shrink:0;">
    {user['display_name'][0].upper()}
    </div>
    <div>
    <div style="font-size:0.82rem;font-weight:600;color:#e2e8f0;line-height:1.2;">{user['display_name']}</div>
    <div style="font-size:0.7rem;color:#64748b;">{user.get('role','viewer').title()}</div>
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
        color: #94a3b8 !important;
        border: none !important;
        text-align: left !important;
        padding: 0.35rem 0.6rem !important;
        font-size: 0.875rem !important;
        font-weight: 400 !important;
        border-radius: 6px !important;
        box-shadow: none !important;
        width: 100%;
        justify-content: flex-start !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stButton"] button:hover {
        background: rgba(255,255,255,0.08) !important;
        color: #e2e8f0 !important;
        box-shadow: none !important;
    }
    section[data-testid="stSidebar"] .nav-active div[data-testid="stButton"] button {
        background: rgba(79,70,229,0.25) !important;
        color: #a5b4fc !important;
        font-weight: 600 !important;
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
    <p style="font-size:0.68rem;color:#334155;text-align:center;margin-top:0.5rem;">
    TrustLLM · LLM Evaluation Toolkit
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
