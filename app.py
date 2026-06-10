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
        header {visibility: hidden;}
        .stApp { background: #0f172a !important; }
        section.main .block-container {
            padding: 0 !important;
            max-width: 100% !important;
        }
        [data-testid="stForm"] {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            padding: 0 !important;
        }
        [data-testid="stForm"] label {
            color: #cbd5e1 !important;
            font-size: 0.875rem !important;
            font-weight: 500 !important;
        }
        [data-testid="stForm"] input {
            background-color: rgba(255,255,255,0.08) !important;
            border: 1px solid rgba(255,255,255,0.18) !important;
            color: #f1f5f9 !important;
            border-radius: 6px !important;
        }
        [data-testid="stForm"] input::placeholder { color: #475569 !important; }
        [data-testid="stForm"] input:focus {
            border-color: #6366f1 !important;
            box-shadow: 0 0 0 3px rgba(99,102,241,0.2) !important;
        }
        [data-testid="stForm"] .stButton > button {
            background-color: #4f46e5 !important;
            color: white !important;
            font-weight: 600 !important;
            font-size: 0.9rem !important;
            padding: 0.6rem 1rem !important;
            border-radius: 6px !important;
            border: none !important;
            width: 100%;
        }
        [data-testid="stForm"] .stButton > button:hover {
            background-color: #4338ca !important;
        }
        @keyframes tllm-drift{0%,100%{transform:translate(0,0) rotate(0deg) scale(1);}33%{transform:translate(6%,-4%) rotate(8deg) scale(1.1);}66%{transform:translate(-5%,5%) rotate(-6deg) scale(1.05);}}
        @keyframes tllm-pulse{0%,100%{opacity:1;box-shadow:0 0 0 0 rgba(74,222,128,.4);}50%{opacity:.4;box-shadow:0 0 0 6px rgba(74,222,128,0);}}
        @keyframes tllm-flash{0%,12%{opacity:1;background:rgba(255,255,255,.05);}18%,100%{opacity:.32;background:transparent;}}
        @keyframes tllm-fillup{0%{width:0;}14%,100%{width:var(--tw);}}
        @keyframes tllm-si{from{opacity:0;transform:translateY(18px);}to{opacity:1;transform:none;}}
        .tllm-s1{opacity:0;animation:tllm-si .6s .00s cubic-bezier(.2,.7,.2,1) forwards;}
        .tllm-s2{opacity:0;animation:tllm-si .6s .08s cubic-bezier(.2,.7,.2,1) forwards;}
        .tllm-s3{opacity:0;animation:tllm-si .6s .16s cubic-bezier(.2,.7,.2,1) forwards;}
        .tllm-s4{opacity:0;animation:tllm-si .6s .24s cubic-bezier(.2,.7,.2,1) forwards;}
        .tllm-s5{opacity:0;animation:tllm-si .6s .32s cubic-bezier(.2,.7,.2,1) forwards;}
        .tllm-s6{opacity:0;animation:tllm-si .6s .40s cubic-bezier(.2,.7,.2,1) forwards;}
        .tllm-s7{opacity:0;animation:tllm-si .6s .48s cubic-bezier(.2,.7,.2,1) forwards;}
        .tllm-s8{opacity:0;animation:tllm-si .6s .56s cubic-bezier(.2,.7,.2,1) forwards;}
        @media(prefers-reduced-motion:reduce){
          .tllm-mesh,.tllm-erow,.tllm-fill,.tllm-ld{animation:none!important;}
          .tllm-s1,.tllm-s2,.tllm-s3,.tllm-s4,.tllm-s5,.tllm-s6,.tllm-s7,.tllm-s8{opacity:1!important;animation:none!important;}
          .tllm-fill{width:var(--tw)!important;}
        }
        </style>
    """), unsafe_allow_html=True)

    left_col, right_col = st.columns([13, 11])

    # ── LEFT PANEL: animated product showcase ──────────────────────────────
    with left_col:
        st.markdown(_h("""
            <div style="position:relative;background:#0f172a;min-height:100vh;padding:3rem 3.5rem;
                        display:flex;flex-direction:column;justify-content:space-between;overflow:hidden;">
            <div class="tllm-mesh" style="position:absolute;inset:-30%;z-index:0;filter:blur(70px);
                 opacity:.55;pointer-events:none;
                 background:radial-gradient(40% 40% at 25% 30%,#6366f1 0%,transparent 60%),
                            radial-gradient(45% 45% at 75% 35%,#a855f7 0%,transparent 60%),
                            radial-gradient(40% 40% at 55% 75%,#2dd4bf 0%,transparent 60%);
                 animation:tllm-drift 20s ease-in-out infinite;"></div>
            <div style="position:absolute;inset:0;z-index:1;opacity:.05;pointer-events:none;
                 background-image:url(&quot;data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='120'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='3'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E&quot;);"></div>
            <div style="position:relative;z-index:2;">
            <div class="tllm-s1" style="display:flex;align-items:center;gap:.6rem;margin-bottom:2.5rem;">
            <div style="background:#4f46e5;width:36px;height:36px;border-radius:8px;
                        display:flex;align-items:center;justify-content:center;font-size:1.1rem;">🛡</div>
            <span style="color:white;font-size:1.2rem;font-weight:700;letter-spacing:-.02em;">TrustLLM</span>
            </div>
            <div class="tllm-s2" style="display:inline-flex;align-items:center;
                        background:rgba(99,102,241,.15);border:1px solid rgba(99,102,241,.35);
                        color:#a5b4fc;font-size:.72rem;font-weight:600;
                        padding:.25rem .75rem;border-radius:20px;width:fit-content;margin-bottom:1.5rem;">
            ✦ LLM Evaluation Platform
            </div>
            <div class="tllm-s3" style="color:white;font-size:2.5rem;font-weight:800;line-height:1.15;
                        letter-spacing:-.03em;margin:0 0 1rem 0;">
            Evaluate LLMs you can<br><span style="color:#ffd43b;">actually</span> trust.
            </div>
            <p class="tllm-s4" style="color:#94a3b8;font-size:.95rem;line-height:1.7;max-width:420px;margin:0 0 2rem 0;">
            Score every model response for correctness, safety, and hallucination.
            Surface failures fast. Ship with confidence.
            </p>
            <div class="tllm-s5" style="margin-bottom:2rem;">
            <div style="display:flex;align-items:flex-start;gap:.6rem;margin-bottom:.5rem;">
            <div style="width:20px;height:20px;background:rgba(99,102,241,.2);border-radius:50%;
                        display:flex;align-items:center;justify-content:center;color:#a5b4fc;font-size:.65rem;flex-shrink:0;margin-top:1px;">✓</div>
            <span style="color:#cbd5e1;font-size:.875rem;">Trace every prompt, response &amp; tool call in real time</span>
            </div>
            <div style="display:flex;align-items:flex-start;gap:.6rem;margin-bottom:.5rem;">
            <div style="width:20px;height:20px;background:rgba(99,102,241,.2);border-radius:50%;
                        display:flex;align-items:center;justify-content:center;color:#a5b4fc;font-size:.65rem;flex-shrink:0;margin-top:1px;">✓</div>
            <span style="color:#cbd5e1;font-size:.875rem;">Compare models side-by-side on safety, quality &amp; cost</span>
            </div>
            <div style="display:flex;align-items:flex-start;gap:.6rem;">
            <div style="width:20px;height:20px;background:rgba(99,102,241,.2);border-radius:50%;
                        display:flex;align-items:center;justify-content:center;color:#a5b4fc;font-size:.65rem;flex-shrink:0;margin-top:1px;">✓</div>
            <span style="color:#cbd5e1;font-size:.875rem;">Detect hallucinations, bias &amp; safety violations automatically</span>
            </div>
            </div>
            </div>
            <div style="position:relative;z-index:2;">
            <div class="tllm-s6" style="background:linear-gradient(160deg,#16161f,#101017);
                        border:1px solid rgba(255,255,255,.1);border-radius:16px;padding:16px;margin-bottom:.75rem;">
            <div style="display:flex;align-items:center;justify-content:space-between;
                        font-size:12px;color:#9a9aab;margin-bottom:12px;">
            <span style="font-family:monospace;font-size:11px;">evaluation_run · gpt-4o</span>
            <span style="display:flex;align-items:center;gap:6px;color:#4ade80;">
            <span class="tllm-ld" style="width:7px;height:7px;border-radius:50%;background:#4ade80;
                  display:inline-block;animation:tllm-pulse 1.4s ease-in-out infinite;"></span>scoring
            </span>
            </div>
            <div class="tllm-erow" style="display:flex;align-items:center;gap:10px;padding:8px 0;border-top:1px solid rgba(255,255,255,.06);font-size:12.5px;opacity:.35;animation:tllm-flash 6s 0s linear infinite;">
            <span style="flex:1;font-weight:500;color:#f4f4f7;">Truthfulness</span>
            <span style="width:80px;height:5px;border-radius:99px;background:rgba(255,255,255,.1);display:inline-block;overflow:hidden;"><span class="tllm-fill" style="--tw:91%;display:block;height:100%;border-radius:99px;background:linear-gradient(90deg,#6366f1,#2dd4bf);width:0;animation:tllm-fillup 6s 0s ease-out infinite;"></span></span>
            <span style="width:30px;text-align:right;color:#f4f4f7;font-size:11px;font-weight:600;">91</span>
            </div>
            <div class="tllm-erow" style="display:flex;align-items:center;gap:10px;padding:8px 0;border-top:1px solid rgba(255,255,255,.06);font-size:12.5px;opacity:.35;animation:tllm-flash 6s 1.2s linear infinite;">
            <span style="flex:1;font-weight:500;color:#f4f4f7;">Safety</span>
            <span style="width:80px;height:5px;border-radius:99px;background:rgba(255,255,255,.1);display:inline-block;overflow:hidden;"><span class="tllm-fill" style="--tw:88%;display:block;height:100%;border-radius:99px;background:linear-gradient(90deg,#6366f1,#2dd4bf);width:0;animation:tllm-fillup 6s 1.2s ease-out infinite;"></span></span>
            <span style="width:30px;text-align:right;color:#f4f4f7;font-size:11px;font-weight:600;">88</span>
            </div>
            <div class="tllm-erow" style="display:flex;align-items:center;gap:10px;padding:8px 0;border-top:1px solid rgba(255,255,255,.06);font-size:12.5px;opacity:.35;animation:tllm-flash 6s 2.4s linear infinite;">
            <span style="flex:1;font-weight:500;color:#f4f4f7;">Fairness</span>
            <span style="width:80px;height:5px;border-radius:99px;background:rgba(255,255,255,.1);display:inline-block;overflow:hidden;"><span class="tllm-fill" style="--tw:83%;display:block;height:100%;border-radius:99px;background:linear-gradient(90deg,#6366f1,#2dd4bf);width:0;animation:tllm-fillup 6s 2.4s ease-out infinite;"></span></span>
            <span style="width:30px;text-align:right;color:#f4f4f7;font-size:11px;font-weight:600;">83</span>
            </div>
            <div class="tllm-erow" style="display:flex;align-items:center;gap:10px;padding:8px 0;border-top:1px solid rgba(255,255,255,.06);font-size:12.5px;opacity:.35;animation:tllm-flash 6s 3.6s linear infinite;">
            <span style="flex:1;font-weight:500;color:#f4f4f7;">Privacy</span>
            <span style="width:80px;height:5px;border-radius:99px;background:rgba(255,255,255,.1);display:inline-block;overflow:hidden;"><span class="tllm-fill" style="--tw:95%;display:block;height:100%;border-radius:99px;background:linear-gradient(90deg,#6366f1,#2dd4bf);width:0;animation:tllm-fillup 6s 3.6s ease-out infinite;"></span></span>
            <span style="width:30px;text-align:right;color:#f4f4f7;font-size:11px;font-weight:600;">95</span>
            </div>
            <div class="tllm-erow" style="display:flex;align-items:center;gap:10px;padding:8px 0;border-top:1px solid rgba(255,255,255,.06);font-size:12.5px;opacity:.35;animation:tllm-flash 6s 4.8s linear infinite;">
            <span style="flex:1;font-weight:500;color:#f4f4f7;">Robustness</span>
            <span style="width:80px;height:5px;border-radius:99px;background:rgba(255,255,255,.1);display:inline-block;overflow:hidden;"><span class="tllm-fill" style="--tw:79%;display:block;height:100%;border-radius:99px;background:linear-gradient(90deg,#6366f1,#2dd4bf);width:0;animation:tllm-fillup 6s 4.8s ease-out infinite;"></span></span>
            <span style="width:30px;text-align:right;color:#f4f4f7;font-size:11px;font-weight:600;">79</span>
            </div>
            </div>
            <div class="tllm-s7" style="display:grid;grid-template-columns:repeat(3,1fr);gap:.75rem;margin-bottom:1.5rem;">
            <div style="background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.08);border-radius:10px;padding:1rem;">
            <div style="color:white;font-size:1.75rem;font-weight:700;line-height:1;margin-bottom:.2rem;">161</div>
            <div style="color:#64748b;font-size:.72rem;">Prompts evaluated</div>
            </div>
            <div style="background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.08);border-radius:10px;padding:1rem;">
            <div style="color:white;font-size:1.75rem;font-weight:700;line-height:1;margin-bottom:.2rem;">6</div>
            <div style="color:#64748b;font-size:.72rem;">Models tested</div>
            </div>
            <div style="background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.08);border-radius:10px;padding:1rem;">
            <div style="color:white;font-size:1.75rem;font-weight:700;line-height:1;margin-bottom:.2rem;">0.76</div>
            <div style="color:#64748b;font-size:.72rem;">Avg trust score</div>
            </div>
            </div>
            <div class="tllm-s8" style="margin-top:1.5rem;padding-top:1.25rem;border-top:1px solid rgba(255,255,255,.06);">
            <p style="color:#334155;font-size:.72rem;margin:0;">
            Built by <a href="https://www.linkedin.com/in/monika-kushwaha-52443735/" target="_blank"
            style="color:#6366f1;text-decoration:none;">Monika Kushwaha</a>
            </p>
            </div>
            </div>
            </div>
        """), unsafe_allow_html=True)

    # ── RIGHT PANEL: auth form ────────────────────────────────────────
    with right_col:
        st.markdown("<div style='height:6vh'></div>", unsafe_allow_html=True)

        st.markdown(_h("""
            <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:2rem;">
            <div style="background:#4f46e5;width:28px;height:28px;border-radius:6px;
                        display:flex;align-items:center;justify-content:center;font-size:0.9rem;">🛡</div>
            <span style="color:#f1f5f9;font-size:1rem;font-weight:700;letter-spacing:-0.01em;">TrustLLM</span>
            </div>
            <div style="color:#f1f5f9;font-size:1.75rem;font-weight:700;letter-spacing:-0.025em;margin:0 0 0.3rem 0;">
            Welcome back
            </div>
            <p style="color:#94a3b8;font-size:0.875rem;margin:0 0 1.5rem 0;">Sign in to your account.</p>
        """), unsafe_allow_html=True)

        # ── Social login buttons (pure HTML to allow full style control) ──
        st.markdown(_h("""
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;margin-bottom:1rem;">
            <button style="background:white;color:#374151;border:1px solid #d1d5db;border-radius:6px;
                           padding:0.65rem 1rem;font-size:0.875rem;font-weight:500;cursor:pointer;
                           width:100%;font-family:inherit;"
                    onclick="var b=this;b.textContent='Not available in demo mode';
                             setTimeout(function(){b.textContent='🔵  Continue with Google'},2500)">
            🔵  Continue with Google
            </button>
            <button style="background:#24292e;color:white;border:1px solid #1b1f23;border-radius:6px;
                           padding:0.65rem 1rem;font-size:0.875rem;font-weight:500;cursor:pointer;
                           width:100%;font-family:inherit;"
                    onclick="var b=this;b.textContent='Not available in demo mode';
                             setTimeout(function(){b.textContent='⬛  Continue with GitHub'},2500)">
            ⬛  Continue with GitHub
            </button>
            </div>
            <div style="display:flex;align-items:center;gap:0.75rem;margin:0 0 1rem 0;">
            <div style="flex:1;border-top:1px solid rgba(255,255,255,0.1);"></div>
            <span style="color:#94a3b8;font-size:0.78rem;white-space:nowrap;">or sign in with credentials</span>
            <div style="flex:1;border-top:1px solid rgba(255,255,255,0.1);"></div>
            </div>
        """), unsafe_allow_html=True)

        # ── Credentials form ─────────────────────────────────────────
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
            <p style="color:#94a3b8;font-size:0.78rem;text-align:center;margin-top:1rem;">
            Demo — Username: <strong style="color:#cbd5e1;">TestUser</strong>
            &nbsp;·&nbsp; Password: <strong style="color:#cbd5e1;">User123</strong>
            </p>
            <div style="margin-top:2rem;padding-top:1.25rem;border-top:1px solid rgba(255,255,255,0.06);">
            <p style="color:#475569;font-size:0.75rem;text-align:center;margin:0;">
            © 2025 TrustLLM · AI Model Evaluation Platform
            </p>
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
