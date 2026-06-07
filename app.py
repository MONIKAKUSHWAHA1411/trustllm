"""
app.py — TrustLLM main entry point.

Auth flow:
    1. Local .env / st.secrets checked for SUPABASE_URL + SUPABASE_KEY.
    2. If Supabase credentials present  → show "Sign in with Google" button.
    3. If Supabase redirects back with ?code= → exchange for user info.
    4. Fall-back username/password login always available.
    5. All authenticated users are upserted into SQLite (db/database.py).
"""

import json
import os
import textwrap
from pathlib import Path
from typing import Optional, List

import streamlit as st
import streamlit.components.v1 as _components

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

from db.database import init_db, upsert_user, touch_user
from auth.google_oauth import (
    is_configured as _google_configured,
    get_auth_url as _google_auth_url,
    exchange_code as _google_exchange_code,
    generate_state as _google_generate_state,
)
from auth.github_oauth import (
    is_configured as _github_configured,
    get_auth_url as _github_auth_url,
    exchange_code as _github_exchange_code,
    generate_state as _github_generate_state,
)

BASE_DIR = Path(__file__).resolve().parent

init_db()

st.set_page_config(
    page_title="TrustLLM",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _h(html: str) -> str:
    """Strip all leading whitespace per-line so Markdown never treats indented HTML as a code block."""
    return '\n'.join(l.lstrip() for l in html.strip().splitlines())


def _load_css() -> None:
    with open(BASE_DIR / "style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

_load_css()


# -----------------------------------------------------------------------
# Local user helpers
# -----------------------------------------------------------------------
USERS_PATH = BASE_DIR / "users.json"


def _load_local_users() -> List[dict]:
    with open(USERS_PATH) as f:
        return json.load(f)["users"]


def _authenticate_local(username: str, password: str) -> Optional[dict]:
    """Authenticate by username OR email (case-insensitive)."""
    identifier = username.strip().lower()
    for u in _load_local_users():
        match = (
            u["username"].lower() == identifier
            or u.get("email", "").lower() == identifier
        )
        if match and u["password"] == password:
            return u
    return None


def _normalise_local_user(u: dict) -> dict:
    return {
        "id":      f"local:{u['username']}",
        "name":    u.get("display_name", u["username"]),
        "email":   u.get("email", ""),
        "picture": "",
        "role":    u.get("role", "viewer"),
    }


def _create_local_user(username: str, password: str, display_name: str = "", email: str = "") -> Optional[dict]:
    with open(USERS_PATH) as f:
        data = json.load(f)
    for u in data["users"]:
        if u["username"].lower() == username.lower():
            return None
    new_user = {
        "username": username,
        "password": password,
        "display_name": display_name or username,
        "role": "viewer",
    }
    if email:
        new_user["email"] = email
    data["users"].append(new_user)
    with open(USERS_PATH, "w") as f:
        json.dump(data, f, indent=2)
    return new_user


# -----------------------------------------------------------------------
# OAuth callback
# -----------------------------------------------------------------------
def _handle_oauth_callback() -> None:
    params = st.query_params
    code = params.get("code")
    if not code:
        return

    # CRITICAL: prevent double-exchange.
    # Streamlit reruns the script when URL params change. Without this guard,
    # the same authorization code gets sent to Google twice — the second
    # attempt fails with "invalid_grant: Malformed auth code" because the
    # code is single-use.
    if st.session_state.get("_oauth_processing") == code:
        return
    if st.session_state.get("_oauth_used_code") == code:
        # Already exchanged this code successfully — clean up the URL and bail
        st.query_params.clear()
        return

    # Mark this code as in-flight BEFORE any work, so reruns see the guard
    st.session_state["_oauth_processing"] = code

    # Decode provider from state ("google:..." or "github:...")
    returned_state = params.get("state", "")
    provider = "google"
    if ":" in returned_state:
        prefix, _ = returned_state.split(":", 1)
        if prefix in ("google", "github"):
            provider = prefix

    with st.spinner("Signing you in…"):
        try:
            if provider == "github":
                user_info = _github_exchange_code(code)
            else:
                user_info = _google_exchange_code(code)
        except Exception as exc:
            # Mark this exact code as already-tried so an auto-rerun
            # doesn't re-fire the same exchange and stack a 2nd error.
            # User can still retry by clicking the button (new code each time).
            st.session_state["_oauth_used_code"] = code
            st.session_state.pop("_oauth_processing", None)
            st.query_params.clear()
            st.error(f"Sign-in failed ({provider}): {exc}")
            return

    # Mark code as fully used; clear in-flight lock
    st.session_state["_oauth_used_code"] = code
    st.session_state.pop("_oauth_processing", None)
    st.query_params.clear()

    db_user = upsert_user(user_info)
    st.session_state["logged_in"] = True
    st.session_state["user"]      = db_user or user_info
    st.rerun()


_handle_oauth_callback()


# -----------------------------------------------------------------------
# Live stats for hero (from results.json, with graceful fallback)
# -----------------------------------------------------------------------
def _hero_stats() -> dict:
    path = BASE_DIR / "reports" / "results.json"
    try:
        import pandas as pd
        with open(path) as f:
            data = json.load(f)
        df = pd.DataFrame(data)
        return {
            "prompts":   len(df),
            "models":    df["model"].nunique(),
            "avg_trust": round(df["trust_score"].mean(), 2),
        }
    except Exception:
        return {"prompts": 163, "models": 6, "avg_trust": 0.76}


# -----------------------------------------------------------------------
# Mini bar-chart preview (used in hero)
# -----------------------------------------------------------------------
def _preview_bars(stats: dict) -> str:
    path = BASE_DIR / "reports" / "results.json"
    bars_html = ""
    try:
        import pandas as pd
        with open(path) as f:
            data = json.load(f)
        df = pd.DataFrame(data)
        top = (
            df.groupby("model")["trust_score"]
            .mean()
            .sort_values(ascending=False)
            .head(4)
        )
        for model, score in top.items():
            pct = int(score * 100)
            if score >= 0.75:
                color = "#22c55e"
            elif score >= 0.5:
                color = "#f59e0b"
            else:
                color = "#ef4444"
            bars_html += f"""
            <div class="pbar-row">
                <span class="pbar-name">{model}</span>
                <div class="pbar-track"><div class="pbar-fill" style="width:{pct}%;background:{color};"></div></div>
                <span class="pbar-val">{score:.2f}</span>
            </div>"""
    except Exception:
        for m, s, c in [("claude-opus", 0.87, "#22c55e"), ("gpt-4o", 0.78, "#22c55e"),
                        ("gemini-1.5", 0.75, "#22c55e"), ("mistral-7b", 0.55, "#ef4444")]:
            pct = int(s * 100)
            bars_html += f"""
            <div class="pbar-row">
                <span class="pbar-name">{m}</span>
                <div class="pbar-track"><div class="pbar-fill" style="width:{pct}%;background:{c};"></div></div>
                <span class="pbar-val">{s:.2f}</span>
            </div>"""
    return bars_html


# -----------------------------------------------------------------------
# Login page — Braintrust hero + Vercel-style form
# -----------------------------------------------------------------------
def _try_demo_login() -> None:
    """Sign in as the demo user — no credentials shown to the user."""
    demo = _authenticate_local("TestUser", "User123")
    if demo:
        normalised = _normalise_local_user(demo)
        upsert_user(normalised)
        st.session_state["logged_in"] = True
        st.session_state["user"] = normalised
        st.session_state["just_logged_in"] = True  # trigger entry animation
        st.rerun()


def _show_login() -> None:
    # ── CSS ──────────────────────────────────────────────────────────
    st.markdown(_h("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
        #MainMenu{visibility:hidden;} footer{visibility:hidden;}
        header[data-testid="stHeader"]{visibility:hidden;}
        section[data-testid="stSidebar"]{display:none!important;}
        .stApp{background:#FFFFFF!important;}
        section.main{background:transparent!important;}
        section.main .block-container{padding:0!important;max-width:100%!important;background:transparent!important;}
        [data-testid="stMain"],[data-testid="stMainBlockContainer"],[data-testid="stAppViewBlockContainer"]{
            width:100%!important;max-width:100%!important;padding:0!important;background:transparent!important;}
        [data-testid="stVerticalBlock"],[data-testid="stVerticalBlockBorderWrapper"],
        [data-testid="stHorizontalBlock"],[data-testid="stColumn"],[data-testid="column"],
        .stColumn,.element-container{background:transparent!important;}
        /* Headings: dark on white */
        [data-testid="stMain"] h1,[data-testid="stMain"] h2,
        [data-testid="stMain"] h3,[data-testid="stMain"] h4{
            font-family:'Inter',system-ui,sans-serif!important;
            color:#0A0A0A!important;-webkit-text-fill-color:#0A0A0A!important;}
        [data-testid="stMain"] p,[data-testid="stMain"] label,
        [data-testid="stMain"] span:not([data-testid="stIconMaterial"]){
            font-family:'Inter',system-ui,sans-serif;}
        /* Form */
        [data-testid="stForm"]{background:transparent!important;border:none!important;padding:0!important;box-shadow:none!important;}
        [data-testid="stTextInputRootElement"],[data-baseweb="input"],[data-baseweb="base-input"]{
            background:#FFFFFF!important;border-color:#E5E7EB!important;}
        [data-testid="stTextInputRootElement"]{border:1px solid #E5E7EB!important;border-radius:8px!important;}
        [data-testid="stTextInputRootElement"]:focus-within{border-color:#E8420A!important;box-shadow:0 0 0 3px rgba(232,66,10,0.1)!important;}
        [data-testid="stTextInputRootElement"] input{color:#0A0A0A!important;background:transparent!important;}
        [data-testid="stTextInput"] label{color:#374151!important;font-size:0.85rem!important;font-weight:500!important;}
        [data-testid="stFormSubmitButton"] button,[data-testid="stForm"] .stButton>button{
            background:#E8420A!important;color:white!important;border:none!important;
            border-radius:8px!important;font-weight:600!important;font-size:0.9rem!important;}
        [data-testid="stFormSubmitButton"] button:hover,[data-testid="stForm"] .stButton>button:hover{background:#C23308!important;}
        [data-testid="stForm"] [data-testid="InputInstructions"]{display:none!important;}
        /* ── Pure-CSS rotating word ── */
        @keyframes wordFade{
            0%,100%{opacity:0;transform:translateY(10px);}
            4%,13%{opacity:1;transform:translateY(0);}
            17%{opacity:0;transform:translateY(-10px);}
            17.1%,99%{opacity:0;transform:translateY(10px);}
        }
        .word-wrap{position:relative;display:inline-block;min-width:13ch;height:1.15em;vertical-align:middle;}
        .word-wrap span{position:absolute;left:0;width:100%;opacity:0;white-space:nowrap;
            color:#E8420A;font-weight:800;animation:wordFade 12s ease-in-out infinite;}
        .word-wrap span:nth-child(1){animation-delay:0s;}
        .word-wrap span:nth-child(2){animation-delay:2s;}
        .word-wrap span:nth-child(3){animation-delay:4s;}
        .word-wrap span:nth-child(4){animation-delay:6s;}
        .word-wrap span:nth-child(5){animation-delay:8s;}
        .word-wrap span:nth-child(6){animation-delay:10s;}
        /* ── Animated gradient bg ── */
        @keyframes gradientShift{0%,100%{background-color:#FFF1EE;}50%{background-color:#FFE8E0;}}
        .how-bg{animation:gradientShift 6s ease-in-out infinite;}
        /* Feature card hover */
        .feat-card{background:#FFFFFF;border:1px solid #E5E7EB;padding:1.5rem 1.25rem;transition:all .25s ease;}
        .feat-card:hover{border-color:#E8420A;box-shadow:0 8px 24px rgba(232,66,10,0.12);transform:translateY(-3px);}
        .stAlert{border-radius:8px!important;}
        </style>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    """), unsafe_allow_html=True)

    # ── ANNOUNCEMENT BANNER ──────────────────────────────────────────
    st.markdown(_h("""
        <div id="tl-banner" style="background:#E8420A;color:white;padding:0.55rem 1rem;
             text-align:center;font-family:'Inter',sans-serif;font-size:0.82rem;font-weight:500;
             display:flex;align-items:center;justify-content:center;gap:0.5rem;position:relative;">
          ✦ TrustLLM now supports RAG evaluation —
          <a href="#sign-in" style="color:white;font-weight:700;text-decoration:underline;margin-left:3px;">Try it →</a>
          <button onclick="this.parentElement.style.display='none';try{localStorage.setItem('tl_banner','1')}catch(e){}"
            style="position:absolute;right:1rem;top:50%;transform:translateY(-50%);
                   background:none;border:none;color:white;cursor:pointer;font-size:1.1rem;line-height:1;">×</button>
        </div>
    """), unsafe_allow_html=True)

    # ── NAVBAR ───────────────────────────────────────────────────────
    st.markdown(_h("""
        <div style="background:#FFFFFF;border-bottom:1px solid #E5E7EB;padding:0 2rem;
             height:60px;display:flex;align-items:center;justify-content:space-between;
             font-family:'Inter',sans-serif;position:sticky;top:0;z-index:50;box-sizing:border-box;">
          <a href="/" style="display:flex;align-items:center;gap:0.5rem;text-decoration:none;flex-shrink:0;">
            <span style="background:#E8420A;width:26px;height:26px;border-radius:5px;flex-shrink:0;
                         display:flex;align-items:center;justify-content:center;
                         color:white;font-weight:800;font-size:0.8rem;">T</span>
            <span style="font-weight:700;color:#0A0A0A;font-size:0.95rem;letter-spacing:-0.01em;">TrustLLM</span>
          </a>
          <div style="display:flex;align-items:center;gap:2rem;margin-left:2rem;">
            <a href="#features" style="color:#6B7280;font-size:0.85rem;font-weight:500;text-decoration:none;white-space:nowrap;">Features</a>
            <a href="#how-it-works" style="color:#6B7280;font-size:0.85rem;font-weight:500;text-decoration:none;white-space:nowrap;">How It Works</a>
            <a href="#sign-in" style="background:#E8420A;color:white;font-size:0.82rem;font-weight:600;
               text-decoration:none;padding:0.45rem 1rem;border-radius:6px;white-space:nowrap;flex-shrink:0;">Join Now →</a>
          </div>
        </div>
    """), unsafe_allow_html=True)

    # ── HERO ─────────────────────────────────────────────────────────
    st.markdown(_h("""
        <section style="background:#FFFFFF;padding:2.5rem 2rem 4rem;font-family:'Inter',sans-serif;text-align:center;">
          <div style="max-width:800px;margin:0 auto;">
            <div style="display:inline-flex;align-items:center;gap:0.5rem;padding:0.3rem 0.85rem;
                 border:1px solid #E5E7EB;border-radius:999px;font-size:0.72rem;color:#6B7280;
                 font-weight:500;margin-bottom:2rem;">
              <span style="width:6px;height:6px;border-radius:50%;background:#E8420A;display:inline-block;"></span>
              AI Trust Evaluation Platform
            </div>
            <h1 style="font-family:'Inter',sans-serif!important;font-size:clamp(37px,5vw,61px);
                 font-weight:800;color:#0A0A0A!important;-webkit-text-fill-color:#0A0A0A!important;
                 line-height:1.05;letter-spacing:-0.03em;margin:0 0 0.75rem;">
              Your LLMs.<br>
              <span style="color:#E8420A;">Honestly</span> Evaluated.
            </h1>
          </div>
          <!-- Animated sentence — full section width so long line fits -->
          <div style="font-size:clamp(37px,4vw,52px);font-weight:800;color:#0A0A0A;
               line-height:1.1;letter-spacing:-0.03em;padding:0 2rem;margin:0 auto 1.5rem;
               text-align:center;max-width:1200px;overflow:hidden;">
            Evaluate
            <span class="word-wrap">
              <span>Truthfulness</span>
              <span>Safety</span>
              <span>Fairness</span>
              <span>Robustness</span>
              <span>Privacy</span>
              <span>Ethics</span>
            </span>
            in every response.
          </div>
          <div style="max-width:800px;margin:0 auto;">
            <p style="font-size:1rem;color:#6B7280;max-width:560px;margin:0 auto 2.5rem;line-height:1.7;">
              Run rigorous trust benchmarks across safety, fairness, robustness, privacy, and truthfulness.
              Get verdicts, not vanity metrics.
            </p>
            <div style="display:flex;gap:1rem;justify-content:center;flex-wrap:wrap;margin-bottom:3rem;">
              <a href="#sign-in" style="background:#E8420A;color:white;font-weight:600;font-size:0.9rem;
                 padding:0.7rem 1.75rem;border-radius:8px;text-decoration:none;display:inline-block;">
                Start Evaluating →
              </a>
              <a href="#how-it-works" style="background:white;color:#0A0A0A;font-weight:500;font-size:0.9rem;
                 padding:0.7rem 1.75rem;border-radius:8px;text-decoration:none;display:inline-block;
                 border:1px solid #E5E7EB;">
                See how it works
              </a>
            </div>
            <div style="display:flex;flex-wrap:wrap;justify-content:center;gap:1.5rem;
                 padding-top:2rem;border-top:1px solid #E5E7EB;">
              <span style="font-size:0.78rem;color:#9CA3AF;">✓ No GPU required</span>
              <span style="font-size:0.78rem;color:#9CA3AF;">✓ RAG-ready</span>
              <span style="font-size:0.78rem;color:#9CA3AF;">✓ Local inference</span>
              <span style="font-size:0.78rem;color:#9CA3AF;">✓ 500+ eval prompts</span>
            </div>
          </div>
        </section>
    """), unsafe_allow_html=True)

    # ── BYOK SECTION ─────────────────────────────────────────────────
    st.markdown(_h("""
        <section style="background:#FFF1EE;padding:3rem 2rem;border-top:3px solid #E8420A;font-family:'Inter',sans-serif;">
          <div style="max-width:800px;margin:0 auto;">
            <p style="font-size:0.7rem;font-weight:700;letter-spacing:0.15em;color:#E8420A;margin-bottom:0.75rem;text-transform:uppercase;">— BRING YOUR OWN KEY</p>
            <h2 style="font-size:clamp(1.5rem,3vw,2.2rem);font-weight:800;color:#0A0A0A!important;
                -webkit-text-fill-color:#0A0A0A!important;letter-spacing:-0.02em;margin:0 0 0.75rem;">
              Your Keys. Any Model.<br><span style="color:#E8420A;">Full Trust Report.</span>
            </h2>
            <p style="color:#6B7280;font-size:0.92rem;line-height:1.7;max-width:600px;margin:0 0 1.75rem;">
              Connect your own OpenAI, Anthropic, Google, or Groq API keys and benchmark
              ChatGPT, Claude, Gemini, and Grok head-to-head — on your data, your prompts, in real time.
            </p>
            <div style="display:flex;flex-wrap:wrap;gap:0.75rem;">
              <span style="background:white;border:1px solid #E8420A;color:#E8420A;padding:0.45rem 1rem;font-size:0.8rem;font-weight:600;border-radius:6px;">ChatGPT · OpenAI</span>
              <span style="background:white;border:1px solid #E8420A;color:#E8420A;padding:0.45rem 1rem;font-size:0.8rem;font-weight:600;border-radius:6px;">Claude · Anthropic</span>
              <span style="background:white;border:1px solid #E8420A;color:#E8420A;padding:0.45rem 1rem;font-size:0.8rem;font-weight:600;border-radius:6px;">Gemini · Google</span>
              <span style="background:white;border:1px solid #E8420A;color:#E8420A;padding:0.45rem 1rem;font-size:0.8rem;font-weight:600;border-radius:6px;">Grok · xAI</span>
            </div>
          </div>
        </section>
    """), unsafe_allow_html=True)

    # ── HOW IT WORKS ─────────────────────────────────────────────────
    st.markdown(_h("""
        <section id="how-it-works" class="how-bg" style="padding:4rem 2rem;font-family:'Inter',sans-serif;">
          <div style="max-width:800px;margin:0 auto;">
            <p style="font-size:0.7rem;font-weight:700;letter-spacing:0.15em;color:#E8420A;margin-bottom:0.75rem;text-transform:uppercase;">— HOW IT WORKS</p>
            <h2 style="font-size:clamp(1.5rem,3vw,2rem);font-weight:800;color:#0A0A0A!important;
                -webkit-text-fill-color:#0A0A0A!important;letter-spacing:-0.02em;margin:0 0 2.5rem;">
              5 Steps to a Trust Score.
            </h2>
            <div style="display:flex;flex-direction:column;">
              <div style="display:flex;gap:1.25rem;padding:1.5rem 0;border-bottom:1px solid rgba(0,0,0,0.08);align-items:flex-start;">
                <div style="background:#E8420A;min-width:36px;height:36px;border-radius:4px;display:flex;align-items:center;justify-content:center;color:white;font-size:0.75rem;font-weight:700;flex-shrink:0;">01</div>
                <div><div style="font-weight:600;color:#0A0A0A;margin-bottom:0.3rem;">Connect Your Models</div><div style="font-size:0.84rem;color:#6B7280;line-height:1.65;">Add your LLM endpoint or paste API keys for OpenAI, Anthropic, Google, Groq, or any OpenAI-compatible API.</div></div>
              </div>
              <div style="display:flex;gap:1.25rem;padding:1.5rem 0;border-bottom:1px solid rgba(0,0,0,0.08);align-items:flex-start;">
                <div style="background:#E8420A;min-width:36px;height:36px;border-radius:4px;display:flex;align-items:center;justify-content:center;color:white;font-size:0.75rem;font-weight:700;flex-shrink:0;">02</div>
                <div><div style="font-weight:600;color:#0A0A0A;margin-bottom:0.3rem;">Select Evaluation Dimensions</div><div style="font-size:0.84rem;color:#6B7280;line-height:1.65;">Choose from Safety, Fairness, Robustness, Privacy, Truthfulness, and Machine Ethics — or run the full suite.</div></div>
              </div>
              <div style="display:flex;gap:1.25rem;padding:1.5rem 0;border-bottom:1px solid rgba(0,0,0,0.08);align-items:flex-start;">
                <div style="background:#E8420A;min-width:36px;height:36px;border-radius:4px;display:flex;align-items:center;justify-content:center;color:white;font-size:0.75rem;font-weight:700;flex-shrink:0;">03</div>
                <div><div style="font-weight:600;color:#0A0A0A;margin-bottom:0.3rem;">Run Adversarial Prompts</div><div style="font-size:0.84rem;color:#6B7280;line-height:1.65;">500+ curated prompts probe jailbreaks, bias probes, hallucination traps, privacy leaks, and more.</div></div>
              </div>
              <div style="display:flex;gap:1.25rem;padding:1.5rem 0;border-bottom:1px solid rgba(0,0,0,0.08);align-items:flex-start;">
                <div style="background:#E8420A;min-width:36px;height:36px;border-radius:4px;display:flex;align-items:center;justify-content:center;color:white;font-size:0.75rem;font-weight:700;flex-shrink:0;">04</div>
                <div><div style="font-weight:600;color:#0A0A0A;margin-bottom:0.3rem;">Get Scored Verdicts</div><div style="font-size:0.84rem;color:#6B7280;line-height:1.65;">Each response is scored by a judge LLM and rule-based classifiers. Results aggregate into per-dimension scores and a Trust Score.</div></div>
              </div>
              <div style="display:flex;gap:1.25rem;padding:1.5rem 0;align-items:flex-start;">
                <div style="background:#E8420A;min-width:36px;height:36px;border-radius:4px;display:flex;align-items:center;justify-content:center;color:white;font-size:0.75rem;font-weight:700;flex-shrink:0;">05</div>
                <div><div style="font-weight:600;color:#0A0A0A;margin-bottom:0.3rem;">Compare and Decide</div><div style="font-size:0.84rem;color:#6B7280;line-height:1.65;">Side-by-side leaderboard shows where each model excels and fails. Export reports and track regressions over time.</div></div>
              </div>
            </div>
          </div>
        </section>
    """), unsafe_allow_html=True)

    # ── FEATURE CARDS ─────────────────────────────────────────────────
    st.markdown(_h("""
        <section id="features" style="background:#FFFFFF;padding:4rem 2rem;border-top:1px solid #E5E7EB;font-family:'Inter',sans-serif;">
          <div style="max-width:900px;margin:0 auto;">
            <p style="font-size:0.7rem;font-weight:700;letter-spacing:0.15em;color:#E8420A;margin-bottom:0.75rem;text-transform:uppercase;">— FEATURES</p>
            <h2 style="font-size:clamp(1.5rem,3vw,2rem);font-weight:800;color:#0A0A0A!important;
                -webkit-text-fill-color:#0A0A0A!important;letter-spacing:-0.02em;margin:0 0 2rem;">
              Everything you need to trust your LLM.
            </h2>
            <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:1px;background:#E5E7EB;">
              <div class="feat-card"><div style="font-weight:600;color:#0A0A0A;margin-bottom:0.4rem;">Single Prompt Eval</div><p style="font-size:0.83rem;color:#6B7280;line-height:1.6;margin:0 0 1rem;">Test any prompt against a model instantly. See trust scores across all six dimensions in real time.</p><a href="#sign-in" style="color:#E8420A;font-size:0.83rem;font-weight:600;text-decoration:none;">Explore →</a></div>
              <div class="feat-card"><div style="font-weight:600;color:#0A0A0A;margin-bottom:0.4rem;">Batch Evaluation</div><p style="font-size:0.83rem;color:#6B7280;line-height:1.6;margin:0 0 1rem;">Run your full prompt dataset through multiple models at once. Compare side-by-side at scale.</p><a href="#sign-in" style="color:#E8420A;font-size:0.83rem;font-weight:600;text-decoration:none;">Explore →</a></div>
              <div class="feat-card"><div style="font-weight:600;color:#0A0A0A;margin-bottom:0.4rem;">RAG Testing</div><p style="font-size:0.83rem;color:#6B7280;line-height:1.6;margin:0 0 1rem;">Upload documents, build a ChromaDB vector store, and evaluate retrieval faithfulness and grounding accuracy.</p><a href="#sign-in" style="color:#E8420A;font-size:0.83rem;font-weight:600;text-decoration:none;">Explore →</a></div>
              <div class="feat-card"><div style="font-weight:600;color:#0A0A0A;margin-bottom:0.4rem;">Agent Performance</div><p style="font-size:0.83rem;color:#6B7280;line-height:1.6;margin:0 0 1rem;">Benchmark autonomous agents on tool-call accuracy, hallucination rate, and semantic correctness.</p><a href="#sign-in" style="color:#E8420A;font-size:0.83rem;font-weight:600;text-decoration:none;">Explore →</a></div>
            </div>
          </div>
        </section>
    """), unsafe_allow_html=True)

    # ── MODELS ────────────────────────────────────────────────────────
    st.markdown(_h("""
        <section style="background:#F9FAFB;padding:4rem 2rem;border-top:1px solid #E5E7EB;font-family:'Inter',sans-serif;">
          <div style="max-width:900px;margin:0 auto;">
            <p style="font-size:0.7rem;font-weight:700;letter-spacing:0.15em;color:#E8420A;margin-bottom:0.75rem;text-transform:uppercase;">— MODELS EVALUATED</p>
            <h2 style="font-size:clamp(1.5rem,3vw,2rem);font-weight:800;color:#0A0A0A!important;
                -webkit-text-fill-color:#0A0A0A!important;letter-spacing:-0.02em;margin:0 0 2rem;">
              12 Models. 6 Providers.
            </h2>
            <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1px;background:#E5E7EB;">
              <div style="background:#F9FAFB;padding:1.25rem 1.5rem;">
                <div style="font-size:0.68rem;color:#E8420A;letter-spacing:0.12em;margin-bottom:0.5rem;font-weight:700;text-transform:uppercase;">OpenAI</div>
                <div style="font-size:0.85rem;color:#374151;line-height:2;">GPT-4o<br>GPT-4 Turbo<br>GPT-3.5 Turbo</div>
              </div>
              <div style="background:#F9FAFB;padding:1.25rem 1.5rem;">
                <div style="font-size:0.68rem;color:#E8420A;letter-spacing:0.12em;margin-bottom:0.5rem;font-weight:700;text-transform:uppercase;">Anthropic</div>
                <div style="font-size:0.85rem;color:#374151;line-height:2;">Claude 3 Opus<br>Claude 3 Sonnet<br>Claude 3 Haiku</div>
              </div>
              <div style="background:#F9FAFB;padding:1.25rem 1.5rem;">
                <div style="font-size:0.68rem;color:#E8420A;letter-spacing:0.12em;margin-bottom:0.5rem;font-weight:700;text-transform:uppercase;">Google</div>
                <div style="font-size:0.85rem;color:#374151;line-height:2;">Gemini Pro<br>Gemini Flash<br>Gemini Ultra</div>
              </div>
              <div style="background:#F9FAFB;padding:1.25rem 1.5rem;">
                <div style="font-size:0.68rem;color:#E8420A;letter-spacing:0.12em;margin-bottom:0.5rem;font-weight:700;text-transform:uppercase;">xAI · Meta · Groq</div>
                <div style="font-size:0.85rem;color:#374151;line-height:2;">Grok-1<br>Llama 3 70B<br>Mixtral 8x7B</div>
              </div>
            </div>
          </div>
        </section>
    """), unsafe_allow_html=True)

    # ── FOOTER ───────────────────────────────────────────────────────
    st.markdown(_h("""
        <div style="background:#F9FAFB;border-top:1px solid #E5E7EB;padding:32px 16px;
                text-align:center;font-family:'Inter',sans-serif;">
          <div style="display:flex;flex-wrap:wrap;justify-content:center;gap:16px;margin-bottom:12px;">
            <a href="#how-it-works" style="font-size:14px;color:#6B7280;text-decoration:none;">How it works</a>
            <a href="#features"     style="font-size:14px;color:#6B7280;text-decoration:none;">Trust dimensions</a>
            <a href="#models"       style="font-size:14px;color:#6B7280;text-decoration:none;">Models</a>
            <a href="#sign-in"      style="font-size:14px;color:#6B7280;text-decoration:none;">Sign in</a>
          </div>
          <p style="font-size:13px;color:#6B7280;line-height:1.6;margin:0;">
            © 2025 TrustLLM · AI Model Evaluation Platform · Powered by ChromaDB · Groq · Streamlit ·
            <span style="white-space:nowrap;">Built by <a href="https://www.linkedin.com/in/monika-kushwaha-52443735" target="_blank"
               rel="noopener noreferrer"
               style="color:#E8420A;text-decoration:none;">Monika Kushwaha</a></span>
          </p>
        </div>
    """), unsafe_allow_html=True)

    # ── SIGN-IN SECTION HEADER ────────────────────────────────────────
    st.markdown(_h("""
        <section id="sign-in" style="background:#F9FAFB;border-top:1px solid #E5E7EB;
             padding:4rem 2rem 1.5rem;font-family:'Inter',sans-serif;text-align:center;">
          <div style="max-width:440px;margin:0 auto;">
            <p style="font-size:0.7rem;font-weight:700;letter-spacing:0.15em;color:#E8420A;margin-bottom:0.75rem;text-transform:uppercase;">— GET STARTED</p>
            <h2 style="font-size:clamp(1.5rem,3vw,2rem);font-weight:800;color:#0A0A0A!important;
                -webkit-text-fill-color:#0A0A0A!important;letter-spacing:-0.02em;margin:0 0 0.5rem;">
              Sign in to TrustLLM.
            </h2>
            <p style="color:#6B7280;font-size:0.88rem;margin:0 0 2rem;line-height:1.6;">
              Access your evaluation dashboard.
            </p>
          </div>
        </section>
    """), unsafe_allow_html=True)

    # ── FORM CARD ─────────────────────────────────────────────────────
    _, form_col, _ = st.columns([1, 2, 1])
    with form_col:
        # ── OAuth buttons ────────────────────────────────────────────
        _google_ok = _google_configured()
        _github_ok = _github_configured()

        # OAuth debug panel — visible only when ?debug=oauth in URL
        if st.query_params.get("debug") == "oauth":
            _redirect_uri = os.getenv("OAUTH_REDIRECT_URI", "")
            try:
                _redirect_uri = st.secrets.get("OAUTH_REDIRECT_URI", _redirect_uri)
            except Exception:
                pass
            with st.expander("🔧 OAuth debug", expanded=True):
                st.write({
                    "google_configured": _google_ok,
                    "github_configured": _github_ok,
                    "OAUTH_REDIRECT_URI": _redirect_uri or "(not set — defaults to http://localhost:8501)",
                })
                if _google_ok:
                    st.code(_google_auth_url("google:DEBUG"), language="text")
                if _github_ok:
                    st.code(_github_auth_url("github:DEBUG"), language="text")

        if _google_ok or _github_ok:
            try:
                # Build each button's HTML first, then render in one grid — guarantees equal size
                _g_btn = ""
                _gh_btn = ""
                _btn_style = (
                    "display:flex;align-items:center;justify-content:center;gap:0.55rem;"
                    "border-radius:10px;padding:0.85rem 0.5rem;font-size:0.875rem;font-weight:500;"
                    "text-decoration:none;box-sizing:border-box;width:100%;min-height:48px;"
                )

                # Google button — state prefixed with "google:" so callback can identify provider
                if _google_ok:
                    _g_state = "google:" + _google_generate_state()
                    google_url = _google_auth_url(_g_state)
                    _g_btn = (
                        f'<a href="{google_url}" target="_top"'
                        f' style="{_btn_style}background:white;color:#374151;border:1px solid #d1d5db;">'
                        '<svg width="16" height="16" viewBox="0 0 48 48" style="flex-shrink:0;">'
                        '<path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>'
                        '<path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>'
                        '<path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>'
                        '<path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>'
                        '</svg>Continue with Google</a>'
                    )

                # GitHub button — state prefixed with "github:" so callback can identify provider
                if _github_ok:
                    _gh_state = "github:" + _github_generate_state()
                    github_url = _github_auth_url(_gh_state)
                    _gh_btn = (
                        f'<a href="{github_url}" target="_top"'
                        f' style="{_btn_style}background:#24292e;color:white;border:1px solid #24292e;">'
                        '<svg width="16" height="16" viewBox="0 0 24 24" fill="white" style="flex-shrink:0;">'
                        '<path d="M12 0C5.37 0 0 5.37 0 12c0 5.3 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577'
                        ' 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61-.546-1.385-1.335-1.755-1.335-1.755'
                        ' -1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305'
                        ' 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38'
                        ' 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399'
                        ' 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24'
                        ' 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81'
                        ' 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 21.795 24'
                        ' 17.295 24 12c0-6.63-5.37-12-12-12z"/>'
                        '</svg>Continue with GitHub</a>'
                    )

                # Single HTML block — CSS grid guarantees identical width for both buttons
                if _g_btn and _gh_btn:
                    st.markdown(
                        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:14px;">'
                        f'{_g_btn}{_gh_btn}</div>',
                        unsafe_allow_html=True,
                    )
                elif _g_btn:
                    st.markdown(f'<div style="margin-bottom:14px;">{_g_btn}</div>', unsafe_allow_html=True)
                elif _gh_btn:
                    st.markdown(f'<div style="margin-bottom:14px;">{_gh_btn}</div>', unsafe_allow_html=True)

            except Exception as _e:
                st.warning(f"OAuth sign-in unavailable: {_e}")
        else:
            st.markdown(_h("""
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;margin-bottom:1rem;">
                <button style="background:white;color:#374151;border:1px solid #d1d5db;border-radius:0;
                               padding:0.7rem 0.5rem;font-size:0.875rem;font-weight:500;
                               font-family:inherit;opacity:0.45;cursor:not-allowed;">
                🌐 Continue with Google
                </button>
                <button style="background:#24292e;color:white;border:1px solid #24292e;border-radius:0;
                               padding:0.7rem 0.5rem;font-size:0.875rem;font-weight:500;
                               font-family:inherit;opacity:0.45;cursor:not-allowed;">
                ⬛ Continue with GitHub
                </button>
                </div>
                <div style="text-align:center;margin-bottom:0.5rem;">
                <span style="font-size:0.75rem;color:#9ca3af;">
                ⚙️ OAuth not configured — add Supabase credentials to enable
                </span>
                </div>
            """), unsafe_allow_html=True)

        st.markdown(_h("""
            <div style="display:flex;align-items:center;gap:0.75rem;margin:0 0 1rem 0;">
            <div style="flex:1;border-top:1px solid #2D2F5E;"></div>
            <span style="color:rgba(255,255,255,0.45);font-size:0.8rem;font-weight:500;white-space:nowrap;-webkit-text-fill-color:rgba(255,255,255,0.45);">or continue with email</span>
            <div style="flex:1;border-top:1px solid #2D2F5E;"></div>
            </div>
        """), unsafe_allow_html=True)

        if "login_mode" not in st.session_state:
            st.session_state.login_mode = "signin"

        if st.session_state.login_mode == "signin":
            with st.form("login_form"):
                username = st.text_input("Username or Email", placeholder="Enter your username or email")
                password = st.text_input("Password", type="password", placeholder="Enter your password")
                submitted = st.form_submit_button("Sign in →", use_container_width=True)

            if submitted:
                if not username or not password:
                    st.error("Please enter both username and password.")
                else:
                    local_user = _authenticate_local(username, password)
                    if local_user:
                        normalised = _normalise_local_user(local_user)
                        upsert_user(normalised)
                        st.session_state["logged_in"] = True
                        st.session_state["user"] = normalised
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")

            if not _google_configured():
                if st.button("⚡ Try demo — no sign-up needed", use_container_width=True, key="try_demo"):
                    _try_demo_login()

            c1, c2 = st.columns([1, 1])
            with c1:
                if st.button("Create account →", key="to_create", use_container_width=True):
                    st.session_state.login_mode = "create"
                    st.rerun()
            with c2:
                with st.expander("Forgot password?"):
                    fp_user = st.text_input("Username", key="fp_username")
                    fp_new  = st.text_input("New password", type="password", key="fp_new")
                    fp_conf = st.text_input("Confirm", type="password", key="fp_conf")
                    if st.button("Reset", key="fp_submit", use_container_width=True):
                        if not fp_user or not fp_new:
                            st.error("Fill in all fields.")
                        elif fp_new != fp_conf:
                            st.error("Passwords don't match.")
                        elif len(fp_new) < 6:
                            st.error("Min 6 characters.")
                        else:
                            with open(USERS_PATH) as _uf:
                                _udata = json.load(_uf)
                            matched = False
                            for _u in _udata["users"]:
                                if _u["username"] == fp_user:
                                    _u["password"] = fp_new
                                    matched = True
                                    break
                            if matched:
                                with open(USERS_PATH, "w") as _uf:
                                    json.dump(_udata, _uf, indent=2)
                                st.success("Password updated.")
                            else:
                                st.error("Username not found.")

        else:  # create account
            with st.form("create_account_form"):
                new_name  = st.text_input("Display Name", placeholder="Your full name")
                new_user  = st.text_input("Username", placeholder="Choose a username")
                new_email = st.text_input("Email (optional)", placeholder="you@example.com")
                new_pass  = st.text_input("Password", type="password", placeholder="Min 6 characters")
                new_pass2 = st.text_input("Confirm Password", type="password", placeholder="Re-enter password")
                create_btn = st.form_submit_button("Create Account →", use_container_width=True)

            if create_btn:
                if not new_user or not new_pass:
                    st.error("Username and password are required.")
                elif len(new_pass) < 6:
                    st.error("Password must be at least 6 characters.")
                elif new_pass != new_pass2:
                    st.error("Passwords do not match.")
                elif len(new_user) < 3:
                    st.error("Username must be at least 3 characters.")
                else:
                    created = _create_local_user(new_user, new_pass, new_name, new_email)
                    if created:
                        if new_email:
                            try:
                                from email_service.email_service import send_welcome_email_async
                                send_welcome_email_async(new_email, new_name or new_user)
                            except Exception as _e:
                                print(f"[signup] welcome email dispatch failed: {_e}")
                        st.success("Account created! Sign in below.")
                        st.session_state.login_mode = "signin"
                        st.rerun()
                    else:
                        st.error("Username already taken.")

            if st.button("← Back to sign in", key="to_signin", use_container_width=True):
                st.session_state.login_mode = "signin"
                st.rerun()

        st.markdown(_h("""
            <div style="text-align:center;padding:1rem 0 3rem;">
            <span style="color:rgba(255,255,255,0.45);font-size:0.8rem;">
            Demo — Username: <strong style="color:#cbd5e1;">TestUser</strong>
            &nbsp;·&nbsp; Password: <strong style="color:#cbd5e1;">User123</strong>
            </span>
            </div>
        """), unsafe_allow_html=True)

    # ── FOOTER ────────────────────────────────────────────────────────
    st.markdown(_h("""
        <footer style="background:#0E0E0E;border-top:1px solid rgba(255,255,255,0.1);padding:36px 24px;
                        text-align:center;color:rgba(255,255,255,0.45);font-size:13px;
                        font-family:'Inter',system-ui,sans-serif;">
          <div style="display:inline-flex;flex-wrap:wrap;gap:24px;justify-content:center;margin-bottom:14px;">
            <a href="#tl-how" style="color:rgba(255,255,255,0.45);font-size:13px;text-decoration:none;">How it works</a>
            <a href="#tl-dimensions" style="color:rgba(255,255,255,0.45);font-size:13px;text-decoration:none;">Trust dimensions</a>
            <a href="#tl-models" style="color:rgba(255,255,255,0.45);font-size:13px;text-decoration:none;">Models</a>
            <a href="#tl-signin" style="color:rgba(255,255,255,0.45);font-size:13px;text-decoration:none;">Sign in</a>
          </div>
          <div>© 2025 TrustLLM · AI Model Evaluation Platform · Powered by ChromaDB · Groq · Streamlit ·
            Built by <a href="https://www.linkedin.com/in/monika-kushwaha-52443735/" target="_blank"
              rel="noopener" style="color:#FF5533;font-weight:500;text-decoration:none;">Monika Kushwaha</a>
          </div>
        </footer>
    """), unsafe_allow_html=True)

    # ── STICKY NAV + FORM CARD JS ──────────────────────────────────────
    _components.html("""
        <script>
        (function() {
          // Sticky nav scroll border
          var nav = window.parent.document.getElementById('tl-nav');
          if (nav) {
            window.parent.addEventListener('scroll', function() {
              nav.style.borderBottomColor = window.parent.scrollY > 8 ? 'rgba(255,255,255,0.1)' : 'transparent';
            }, {passive: true});
          }
          // Dark card wrapper for the middle (form) column
          var cols = window.parent.document.querySelectorAll('[data-testid="stColumn"]');
          if (cols.length >= 3) {
            var mid = cols[Math.floor(cols.length / 2)];
            mid.style.background = '#1C1C1C';
            mid.style.border = '1px solid rgba(255,255,255,0.1)';
            mid.style.borderRadius = '16px';
            mid.style.padding = '32px';
            mid.style.boxShadow = '0 0 60px rgba(99,102,241,0.10)';
          }
        })();
        </script>
    """, height=0)


# -----------------------------------------------------------------------
# Command palette HTML/JS injection
# -----------------------------------------------------------------------
_CMD_PAGES = [
    ("Overview",          "📊", "Monitor"),
    ("Failure Analysis",  "🔍", "Monitor"),
    ("Leaderboard",       "🏆", "Monitor"),
    ("Run Evaluation",    "▶",  "Evaluate"),
    ("RAG Testing",       "📚", "Evaluate"),
    ("Prompt Explorer",   "🔎", "Data"),
    ("Prompt Dataset",    "📂", "Data"),
    ("Query History",     "🕘", "Data"),
    ("Profile",           "👤", "Account"),
    ("API Keys",          "🔑", "Account"),
]


def _inject_command_palette() -> None:
    items_json = json.dumps(
        [{"name": n, "icon": i, "section": s} for n, i, s in _CMD_PAGES]
    )
    # ------------------------------------------------------------------
    # Overlay DOM structure — injected via st.markdown (no scripts needed).
    # ------------------------------------------------------------------
    overlay_html = "".join([
        '<div id="cmd-overlay">',
        '<div id="cmd-box">',
        '<div id="cmd-input-row">',
        '<span id="cmd-search-icon">⌘</span>',
        '<input id="cmd-input" placeholder="Search pages…" autocomplete="off" spellcheck="false"/>',
        '</div>',
        '<div id="cmd-results"></div>',
        '<div id="cmd-footer">',
        '<span><kbd>↑↓</kbd> navigate</span>',
        '<span><kbd>↵</kbd> open</span>',
        '<span><kbd>esc</kbd> close</span>',
        '</div>',
        '</div>',
        '</div>',
    ])
    st.markdown(overlay_html, unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # JS setup — uses st.components.v1.html() (renders in an iframe whose
    # scripts ARE executed).  window.parent gives access to the main page.
    # Guard on element._cmdSetup re-attaches listeners after Streamlit
    # rerenders the overlay DOM node; guard on window._cmdKeyListener
    # prevents duplicate document-level keydown handlers.
    # ------------------------------------------------------------------
    setup_html = f"""<script>
(function(){{
  var w = window.parent;
  var d = w.document;
  var ITEMS = {items_json};

  function setup() {{
    var overlay = d.getElementById('cmd-overlay');
    if (!overlay) return false;
    if (overlay._cmdSetup) return true;   // this exact node already wired
    overlay._cmdSetup = true;

    var input   = d.getElementById('cmd-input');
    var results = d.getElementById('cmd-results');
    var hi = 0;

    function openP() {{
      overlay.classList.add('open');
      input.value = ''; hi = 0; render(ITEMS);
      setTimeout(function() {{ input.focus(); }}, 60);
    }}
    function closeP() {{ overlay.classList.remove('open'); }}

    function render(items) {{
      var groups = {{}};
      items.forEach(function(it) {{
        if (!groups[it.section]) groups[it.section] = [];
        groups[it.section].push(it);
      }});
      var html = ''; var idx = 0;
      Object.keys(groups).forEach(function(sec) {{
        html += '<div class="cmd-group">' + sec + '</div>';
        groups[sec].forEach(function(it) {{
          html += '<div class="cmd-row' + (idx===hi ? ' hi' : '') + '" data-name="' + it.name + '">'
               + '<span class="cmd-row-icon">'   + it.icon    + '</span>'
               + '<span class="cmd-row-label">'  + it.name    + '</span>'
               + '<span class="cmd-row-section">' + it.section + '</span></div>';
          idx++;
        }});
      }});
      results.innerHTML = html;
      results.querySelectorAll('.cmd-row').forEach(function(row) {{
        row.addEventListener('click', function() {{ navigate(row.dataset.name); }});
      }});
    }}

    function navigate(name) {{
      closeP();
      var sidebar = d.querySelector('section[data-testid="stSidebar"]');
      if (!sidebar) return;
      var btns = sidebar.querySelectorAll('button');
      for (var i = 0; i < btns.length; i++) {{
        // Sidebar buttons are rendered as "icon name" — use includes()
        if (btns[i].innerText.trim().includes(name)) {{ btns[i].click(); return; }}
      }}
    }}

    function filterItems(q) {{
      if (!q) return ITEMS;
      var low = q.toLowerCase();
      return ITEMS.filter(function(it) {{
        return it.name.toLowerCase().includes(low) || it.section.toLowerCase().includes(low);
      }});
    }}

    input.addEventListener('input', function() {{ hi = 0; render(filterItems(input.value)); }});
    input.addEventListener('keydown', function(e) {{
      var rows = results.querySelectorAll('.cmd-row');
      if (e.key === 'ArrowDown') {{ hi = Math.min(hi+1, rows.length-1); render(filterItems(input.value)); e.preventDefault(); }}
      if (e.key === 'ArrowUp')   {{ hi = Math.max(hi-1, 0);             render(filterItems(input.value)); e.preventDefault(); }}
      if (e.key === 'Enter')     {{ if (rows[hi]) navigate(rows[hi].dataset.name); }}
      if (e.key === 'Escape')    {{ closeP(); }}
    }});
    overlay.addEventListener('click', function(e) {{ if (e.target === overlay) closeP(); }});

    // Replace any previous document-level keydown to avoid duplicates
    if (w._cmdKeyListener) d.removeEventListener('keydown', w._cmdKeyListener);
    w._cmdKeyListener = function(e) {{
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {{
        e.preventDefault();
        if (overlay.classList.contains('open')) closeP(); else openP();
      }}
    }};
    d.addEventListener('keydown', w._cmdKeyListener);

    // Wire the header ⌘K button (DOMPurify strips onclick attrs, so we add
    // the listener here where we have unrestricted DOM access)
    d.querySelectorAll('button').forEach(function(b) {{
      if (b.innerText.includes('Command palette') && !b._cmdWired) {{
        b._cmdWired = true;
        b.addEventListener('click', openP);
      }}
    }});

    w._cmdOpen  = openP;
    w._cmdClose = closeP;
    return true;
  }}

  // Try immediately; retry until overlay element exists in the parent DOM
  if (!setup()) {{
    var t = setInterval(function() {{ if (setup()) clearInterval(t); }}, 50);
    setTimeout(function() {{ clearInterval(t); }}, 5000);
  }}
}})();
</script>"""
    _components.html(setup_html, height=0, scrolling=False)


# -----------------------------------------------------------------------
# Auth gate
# -----------------------------------------------------------------------
if not st.session_state.get("logged_in"):
    _show_login()
    st.stop()

_current_user = st.session_state["user"]
touch_user(_current_user.get("id", ""))

# -----------------------------------------------------------------------
# Page imports (after auth)
# -----------------------------------------------------------------------
from ui_pages.overview          import render as overview
from ui_pages.prompt_explorer   import render as prompt_explorer
from ui_pages.leaderboard       import render as leaderboard
from ui_pages.run_eval          import render as run_eval
from ui_pages.rag_page          import render as rag_testing
from ui_pages.prompt_dataset    import render as prompt_dataset
from ui_pages.failure_analysis  import render as failure_analysis
from ui_pages.profile           import render as profile_page
from ui_pages.api_keys          import render as api_keys_page
from ui_pages.query_history     import render as query_history_page

# -----------------------------------------------------------------------
# Projects
# -----------------------------------------------------------------------
with open(BASE_DIR / "projects.json") as _pf:
    _projects_data = json.load(_pf)["projects"]
_project_names = ["All Projects"] + [p["name"] for p in _projects_data]

# -----------------------------------------------------------------------
# Top header bar
# -----------------------------------------------------------------------
user       = st.session_state["user"]
user_name  = user.get("name", user.get("display_name", "User"))

header = st.container()
with header:
    h1, h2, h3, h4, h5 = st.columns([1.2, 2, 2, 1.1, 1.1])
    with h1:
        st.markdown(_h("""
            <div style="display:flex;align-items:center;gap:0.5rem;padding-top:0.3rem;">
            <div style="background:#E8290B;width:26px;height:26px;border-radius:5px;
                        display:flex;align-items:center;justify-content:center;
                        font-size:0.85rem;color:white;">🛡</div>
            <span style="font-weight:800;color:#0E0E0E;font-size:0.95rem;
                         font-family:'Syne',sans-serif;letter-spacing:0.02em;">TrustLLM</span>
            </div>
        """), unsafe_allow_html=True)
    with h2:
        selected_project = st.selectbox(
            "Project", _project_names, label_visibility="collapsed"
        )
    with h3:
        selected_env = st.selectbox(
            "Environment",
            ["production", "staging", "development"],
            label_visibility="collapsed",
        )
    with h4:
        pass  # command palette button removed
    with h5:
        with st.popover(f"👤 {user_name}", use_container_width=True):
            st.markdown(
                f"<div style='font-size:0.83rem;color:#71717a;padding-bottom:0.5rem;'>"
                f"{user.get('email', '')}</div>",
                unsafe_allow_html=True,
            )
            if st.button("👤 My Profile", use_container_width=True, key="hdr_profile"):
                st.session_state["nav_page"] = "Profile"
                st.rerun()
            if st.button("🕘 Query History", use_container_width=True, key="hdr_history"):
                st.session_state["nav_page"] = "Query History"
                st.rerun()
            st.divider()
            if st.button("Sign out", use_container_width=True, key="hdr_signout"):
                for k in list(st.session_state.keys()):
                    del st.session_state[k]
                st.rerun()

st.markdown('<hr class="header-divider">', unsafe_allow_html=True)

# Project category filter
_selected_categories = None
if selected_project != "All Projects":
    for p in _projects_data:
        if p["name"] == selected_project:
            _selected_categories = p["categories"]
            break
st.session_state["project_categories"] = _selected_categories

# -----------------------------------------------------------------------
# Sidebar — sectioned navigation
# -----------------------------------------------------------------------
_SECTIONS = {
    "MONITOR": [
        ("📊", "Overview"),
        ("🔍", "Failure Analysis"),
        ("🏆", "Leaderboard"),
    ],
    "EVALUATE": [
        ("▶",  "Run Evaluation"),
        ("📚", "RAG Testing"),
    ],
    "DATA": [
        ("🔎", "Prompt Explorer"),
        ("📂", "Prompt Dataset"),
        ("🕘", "Query History"),
    ],
    "ACCOUNT": [
        ("👤", "Profile"),
        ("🔑", "API Keys"),
    ],
}

_nav_override = st.session_state.pop("nav_page", None)
if _nav_override:
    st.session_state["_current_page"] = _nav_override

if "_current_page" not in st.session_state:
    st.session_state["_current_page"] = "Overview"

st.sidebar.markdown(
    f"""<div style="padding:1rem 0.75rem 0.5rem;">
        <div style="display:flex;align-items:center;gap:0.6rem;">
            <div style="background:#E8290B;width:30px;height:30px;flex-shrink:0;border-radius:6px;
                        display:flex;align-items:center;justify-content:center;font-size:1rem;">🛡</div>
            <div>
                <div style="font-size:0.95rem;font-weight:800;color:white;
                            font-family:'Syne',sans-serif;letter-spacing:0.02em;">TrustLLM</div>
                <div style="font-size:0.68rem;color:rgba(255,255,255,0.3);
                            font-family:'Syne',sans-serif;letter-spacing:0.12em;
                            text-transform:uppercase;">{user_name}</div>
            </div>
        </div>
    </div>""",
    unsafe_allow_html=True,
)

st.sidebar.markdown('<hr style="border:none;border-top:1px solid rgba(255,255,255,0.08);margin:0 0 0.25rem;">', unsafe_allow_html=True)

page = st.session_state["_current_page"]

for section, items in _SECTIONS.items():
    st.sidebar.markdown(f'<div class="sb-section">{section}</div>', unsafe_allow_html=True)
    for icon, label in items:
        is_active = (page == label)
        btn_label = f"{'●' if is_active else '○'}  {icon}  {label}"
        if is_active:
            st.sidebar.markdown(
                f'<div style="background:rgba(232,41,11,0.1);border-left:3px solid #E8290B;'
                f'padding:0.4rem 0.75rem;font-size:0.87rem;color:white;font-weight:600;'
                f'margin-bottom:1px;font-family:\'Inter\',sans-serif;">'
                f'{icon}&nbsp;&nbsp;{label}</div>',
                unsafe_allow_html=True,
            )
        else:
            if st.sidebar.button(f"{icon}  {label}", key=f"nav_{label}", use_container_width=True):
                st.session_state["_current_page"] = label
                page = label
                st.rerun()

st.sidebar.markdown('<hr style="border:none;border-top:1px solid rgba(255,255,255,0.08);margin:0.75rem 0 0.5rem;">', unsafe_allow_html=True)

# -----------------------------------------------------------------------
# Get-your-own-key quick-links (TrustLLM Pro BYOK)
# -----------------------------------------------------------------------
from llm_runner.providers import PROVIDERS as _PRO_PROVIDERS  # noqa: E402

st.sidebar.markdown('<div class="sb-section">GET API KEYS</div>', unsafe_allow_html=True)
_link_html_parts = []
for _pid, _meta in _PRO_PROVIDERS.items():
    _link_html_parts.append(
        f'<a href="{_meta["api_key_url"]}" target="_blank" rel="noopener" '
        f'style="display:block;padding:0.25rem 0.75rem;font-size:0.8rem;color:rgba(255,255,255,0.4);'
        f'text-decoration:none;">'
        f'↗ {_meta["display_name"]}</a>'
    )
st.sidebar.markdown("".join(_link_html_parts), unsafe_allow_html=True)

# Quick inline API key paste — lets users activate Pro without going to the Settings page
with st.sidebar.expander("➕ Paste API key (Pro)", expanded=False):
    _provider_names  = [_meta["display_name"] for _meta in _PRO_PROVIDERS.values()]
    _provider_ids    = list(_PRO_PROVIDERS.keys())
    _sel_display     = st.selectbox("Provider", _provider_names, key="sb_quick_provider", label_visibility="collapsed")
    _sel_pid         = _provider_ids[_provider_names.index(_sel_display)]
    _quick_key       = st.text_input(
        "API key",
        type="password",
        placeholder=_PRO_PROVIDERS[_sel_pid]["key_prefix_hint"],
        key="sb_quick_key_input",
        label_visibility="collapsed",
    )
    # Show persistent inline feedback so the message survives any rerun
    _key_msg = st.session_state.pop("_sb_key_msg", None)
    if _key_msg:
        if _key_msg.startswith("✅"):
            st.success(_key_msg)
        else:
            st.error(_key_msg)

    if st.button("Save key", key="sb_quick_save", type="primary", use_container_width=True, disabled=not _quick_key.strip()):
        try:
            from auth.api_keys import set_key as _set_key_fn, encryption_configured as _enc_ok
            if not _enc_ok():
                st.session_state["_sb_key_msg"] = "❌ Encryption not configured — add API_KEYS_ENCRYPTION_KEY to Streamlit secrets."
            elif _set_key_fn(_sel_pid, _quick_key.strip()):
                st.session_state["_sb_key_msg"] = f"✅ {_sel_display} API key saved successfully!"
            else:
                st.session_state["_sb_key_msg"] = "❌ Save failed — check your Streamlit secrets."
        except Exception as _e:
            st.session_state["_sb_key_msg"] = f"❌ Error: {_e}"
        st.rerun()

st.sidebar.markdown('<hr style="border:none;border-top:1px solid rgba(255,255,255,0.08);margin:0.75rem 0 0.5rem;">', unsafe_allow_html=True)

pass  # command palette hint removed

if st.sidebar.button("Sign out", use_container_width=True, key="sb_signout"):
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()

# -----------------------------------------------------------------------
# Inject command palette
# -----------------------------------------------------------------------
_inject_command_palette()

# -----------------------------------------------------------------------
# Router
# -----------------------------------------------------------------------
_routes = {
    "Overview":          overview,
    "Prompt Explorer":   prompt_explorer,
    "Leaderboard":       leaderboard,
    "Run Evaluation":    run_eval,
    "RAG Testing":       rag_testing,
    "Prompt Dataset":    prompt_dataset,
    "Failure Analysis":  failure_analysis,
    "Query History":     query_history_page,
    "Profile":           profile_page,
    "API Keys":          api_keys_page,
}

_routes.get(page, overview)()
