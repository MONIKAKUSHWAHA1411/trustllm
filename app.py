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
    st.markdown(_h("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
        /* ── Hide Streamlit chrome ── */
        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }
        /* …but keep our own custom footer visible */
        [data-testid="stMain"] footer { visibility: visible !important; }
        header[data-testid="stHeader"] { visibility: hidden; }
        section[data-testid="stSidebar"] { display: none !important; }
        /* ── Dark background ── */
        .stApp { background: #0A0B1A !important; }
        section.main { background: transparent !important; }
        section.main .block-container { padding: 0 !important; max-width: 100% !important; background: transparent !important; }
        /* ── High-level wrappers — full width, no padding, transparent ── */
        [data-testid="stMain"],
        [data-testid="stMainBlockContainer"],
        [data-testid="stAppViewBlockContainer"] {
            width: 100% !important;
            max-width: 100% !important;
            padding: 0 !important;
            background: transparent !important;
        }
        /* ── Inner containers — transparent only (don't touch padding/size) ── */
        [data-testid="stVerticalBlock"],
        [data-testid="stVerticalBlockBorderWrapper"],
        [data-testid="stHorizontalBlock"],
        [data-testid="stColumn"],
        [data-testid="column"],
        .stColumn, .element-container { background: transparent !important; }
        /* ── CSS variables ── */
        :root {
            --bg-dark: #0A0B1A; --bg-section: #0F1030; --bg-card: #13153A;
            --accent: #6366F1; --accent-light: #818CF8; --accent-dim: #4338CA;
            --accent-glow: rgba(99,102,241,0.15);
            --gradient: linear-gradient(135deg,#6366F1,#8B5CF6);
            --tl-white: #ffffff; --muted: #94A3B8; --border: #1E1F4E;
        }
        /* ── Headings: force Inter + white (override global style.css) ── */
        [data-testid="stMain"] h1,
        [data-testid="stMain"] h2,
        [data-testid="stMain"] h3,
        [data-testid="stMain"] h4 {
            font-family: 'Inter', system-ui, sans-serif !important;
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
        }
        /* ── Gradient text: match standalone `color: transparent;` only ──
           (trailing `;` avoids matching `border-color: transparent <rgb>` shorthands) ── */
        [data-testid="stMain"] [style*="color: transparent;"],
        [data-testid="stMain"] [style*="color:transparent;"],
        [data-testid="stMain"] .grad-text {
            -webkit-text-fill-color: transparent !important;
            color: transparent !important;
        }
        /* ── Body text uses Inter — but NEVER icon spans (would break Material ligatures) ── */
        [data-testid="stMain"] p,
        [data-testid="stMain"] label,
        [data-testid="stMain"] button,
        [data-testid="stMain"] input,
        [data-testid="stMain"] li,
        [data-testid="stMain"] span:not([data-testid="stIconMaterial"]):not([class*="material"]):not([class*="icon"]) {
            font-family: 'Inter', system-ui, sans-serif;
        }
        /* ── Form — transparent shell (dark card comes from wrapper div) ── */
        [data-testid="stForm"] {
            background: transparent !important;
            border: none !important; border-radius: 0 !important;
            padding: 0 !important; box-shadow: none !important;
        }
        /* ── Dark inputs — bg lives on the BaseWeb wrapper, not <input> ── */
        [data-testid="stTextInputRootElement"],
        [data-baseweb="input"], [data-baseweb="base-input"] {
            background: var(--bg-section) !important;
            border-color: var(--border) !important;
        }
        [data-testid="stTextInputRootElement"] {
            border: 1px solid var(--border) !important;
            border-radius: 10px !important;
        }
        /* .stApp prefix beats project style.css `.stTextInput > div > div > input` (0,1,3) */
        .stApp .stTextInput input, .stApp [data-testid="stTextInput"] input,
        .stApp [data-testid="stForm"] input {
            background: transparent !important;
            border: none !important;
            color: var(--tl-white) !important; -webkit-text-fill-color: var(--tl-white) !important;
            font-size: 14px !important; min-height: 44px !important;
            padding: 11px 14px !important;
        }
        .stApp .stTextInput input::placeholder { color: #475569 !important; opacity: 1 !important; -webkit-text-fill-color: #475569 !important; }
        [data-testid="stTextInputRootElement"]:focus-within {
            border-color: var(--accent) !important;
            box-shadow: 0 0 0 3px rgba(99,102,241,0.2) !important;
        }
        /* ── Labels ── */
        .stTextInput label, .stTextInput label p,
        [data-testid="stWidgetLabel"] p,
        [data-testid="stColumn"] label { color: #cbd5e1 !important; font-size: 13px !important; font-weight: 500 !important; }
        /* ── Form submit button — gradient indigo (it's stFormSubmitButton, not stButton) ── */
        [data-testid="stFormSubmitButton"] button {
            background: var(--gradient) !important; color: white !important;
            -webkit-text-fill-color: white !important;
            font-weight: 600 !important; font-size: 14px !important;
            padding: 14px !important; border-radius: 10px !important;
            border: none !important; min-height: 44px !important;
            box-shadow: 0 4px 16px rgba(99,102,241,0.30) !important;
        }
        [data-testid="stFormSubmitButton"] button:hover {
            box-shadow: 0 8px 22px rgba(99,102,241,0.45) !important;
            transform: translateY(-1px) !important;
        }
        [data-testid="stFormSubmitButton"] button p,
        [data-testid="stFormSubmitButton"] button span,
        [data-testid="stFormSubmitButton"] button div {
            color: white !important; -webkit-text-fill-color: white !important;
        }
        /* ── Auxiliary buttons (Try demo, Create account, Back) ── */
        [data-testid="stColumn"] .stButton > button {
            background: transparent !important;
            border: 1px solid var(--border) !important;
            color: var(--accent-light) !important;
            border-radius: 10px !important; font-weight: 600 !important;
        }
        [data-testid="stColumn"] .stButton > button:hover {
            background: var(--accent-glow) !important;
        }
        /* ── Expander (forgot password) ── */
        [data-testid="stExpander"] {
            background: var(--bg-card) !important;
            border: 1px solid var(--border) !important; border-radius: 10px !important;
        }
        [data-testid="stExpander"] summary p,
        [data-testid="stExpander"] summary span { color: #cbd5e1 !important; font-size: 0.875rem !important; }
        [data-testid="stExpander"] label { color: #cbd5e1 !important; }
        [data-testid="stExpander"] input {
            background: var(--bg-section) !important;
            border-color: var(--border) !important; color: white !important;
        }
        [data-testid="stExpander"] input::placeholder { color: #475569 !important; opacity: 1 !important; }
        [data-testid="stExpander"] input:focus {
            border-color: var(--accent) !important;
            box-shadow: 0 0 0 3px rgba(99,102,241,0.2) !important;
        }
        [data-testid="stExpander"] .stButton > button {
            background: var(--accent) !important; color: white !important;
            border: none !important; font-weight: 600 !important;
        }
        /* ── Alert colours ── */
        [data-testid="stAlert"] { background: rgba(239,68,68,0.08) !important; border-color: rgba(239,68,68,0.3) !important; }
        [data-testid="stAlert"] p { color: #fca5a5 !important; }
        [data-testid="stAlert"][data-type="success"] { background: rgba(34,197,94,0.08) !important; border-color: rgba(34,197,94,0.3) !important; }
        [data-testid="stAlert"][data-type="success"] p { color: #86efac !important; }
        /* ── Markdown text in dark context ──
           Project style.css forces .stMarkdown p/span/li to #111827 !important, which
           clobbers our inline colors. Re-assert intended colors with higher specificity.
           Selectors match the browser-serialized inline form: `color: rgb(R, G, B)`. ── */
        [data-testid="stMarkdownContainer"] p { color: #cbd5e1 !important; }
        /* model-id <li> inherit the card's muted tone */
        [data-testid="stMain"] [data-testid="stMarkdownContainer"] li {
            color: #94A3B8 !important; -webkit-text-fill-color: #94A3B8 !important;
        }
        /* eyebrows (#6366F1), chips/checkmarks (#818CF8), values (#94A3B8), labels (#cbd5e1) */
        [data-testid="stMain"] [style*="color: rgb(99, 102, 241)"] {
            color: #6366F1 !important; -webkit-text-fill-color: #6366F1 !important;
        }
        [data-testid="stMain"] [style*="color: rgb(129, 140, 248)"] {
            color: #818CF8 !important; -webkit-text-fill-color: #818CF8 !important;
        }
        [data-testid="stMain"] [style*="color: rgb(148, 163, 184)"] {
            color: #94A3B8 !important; -webkit-text-fill-color: #94A3B8 !important;
        }
        [data-testid="stMain"] [style*="color: rgb(203, 213, 225)"] {
            color: #cbd5e1 !important; -webkit-text-fill-color: #cbd5e1 !important;
        }
        /* ── Responsive ── */
        @media (max-width: 520px) {
            .tl-step { grid-template-columns: 48px 1fr !important; }
            .tl-step-spacer { display: none !important; }
            .tl-steps-spine { left: 22px !important; }
            .tl-dims-grid { grid-template-columns: 1fr !important; }
            .tl-models-row { display: flex !important; overflow-x: auto !important; }
            .tl-model-card { flex: 0 0 70% !important; min-width: 200px !important; }
            .tl-hero-ctas { flex-direction: column !important; width: 100% !important; max-width: 320px !important; }
            .tl-stats-grid { grid-template-columns: 1fr !important; }
        }
        </style>
    """), unsafe_allow_html=True)

    # ── NAV ──────────────────────────────────────────────────────────
    st.markdown(_h("""
        <nav id="tl-nav" style="position:sticky;top:0;z-index:200;
            background:rgba(10,11,26,0.85);backdrop-filter:blur(12px);
            -webkit-backdrop-filter:blur(12px);border-bottom:1px solid transparent;
            transition:border-color 0.2s ease;font-family:'Inter',system-ui,sans-serif;">
          <div style="max-width:1240px;margin:0 auto;padding:16px 24px;
                      display:flex;align-items:center;justify-content:space-between;gap:16px;">
            <a href="#" style="display:flex;align-items:center;gap:10px;color:white;text-decoration:none;
                               font-size:17px;font-weight:700;letter-spacing:-0.01em;">
              <span style="width:32px;height:32px;border-radius:8px;background:#6366F1;
                           display:flex;align-items:center;justify-content:center;font-size:17px;flex-shrink:0;">🛡</span>
              TrustLLM
            </a>
            <div style="display:flex;align-items:center;gap:10px;">
              <a href="#tl-signin" style="display:inline-flex;align-items:center;padding:10px 18px;
                  border-radius:10px;font-size:14px;font-weight:600;background:transparent;
                  color:#818CF8;border:1px solid #6366F1;text-decoration:none;">Sign In</a>
              <a href="#tl-signin" style="display:inline-flex;align-items:center;padding:10px 18px;
                  border-radius:10px;font-size:14px;font-weight:600;
                  background:linear-gradient(135deg,#6366F1,#8B5CF6);color:white;text-decoration:none;
                  box-shadow:0 4px 16px rgba(99,102,241,0.30);">Get Started</a>
            </div>
          </div>
        </nav>
    """), unsafe_allow_html=True)

    # ── HERO ──────────────────────────────────────────────────────────
    st.markdown(_h("""
        <section style="min-height:100vh;padding:140px 24px 96px;display:flex;align-items:center;
            justify-content:center;text-align:center;position:relative;overflow:hidden;
            background:#0A0B1A;font-family:'Inter',system-ui,sans-serif;">
          <div style="position:absolute;width:480px;height:480px;border-radius:50%;background:#6366F1;
                      top:-120px;left:-100px;filter:blur(120px);opacity:0.1;pointer-events:none;z-index:0;"></div>
          <div style="position:absolute;width:380px;height:380px;border-radius:50%;background:#8B5CF6;
                      bottom:-100px;right:-80px;filter:blur(120px);opacity:0.12;pointer-events:none;z-index:0;"></div>
          <div style="position:absolute;inset:0;background:
              radial-gradient(ellipse 800px 600px at 50% 40%,rgba(99,102,241,0.12),transparent 60%),
              radial-gradient(ellipse 500px 400px at 15% 80%,rgba(139,92,246,0.08),transparent 60%);
              pointer-events:none;z-index:0;"></div>
          <div style="position:relative;z-index:1;max-width:880px;
                      display:flex;flex-direction:column;align-items:center;gap:26px;">
            <span style="display:inline-flex;align-items:center;gap:8px;padding:6px 14px;
                border-radius:999px;background:rgba(99,102,241,0.15);border:1px solid #6366F1;
                color:#818CF8;font-size:12px;font-weight:600;letter-spacing:0.06em;">
              <span style="width:6px;height:6px;border-radius:50%;background:#6366F1;
                           box-shadow:0 0 0 4px rgba(99,102,241,0.18);display:inline-block;"></span>
              LLM Evaluation Platform
            </span>
            <h1 style="font-size:clamp(40px,6.4vw,72px);font-weight:800;letter-spacing:-0.035em;
                        line-height:1.05;margin:0;color:white;">
              Evaluate LLMs you can<br>
              <span style="background:linear-gradient(135deg,#6366F1,#8B5CF6);
                           -webkit-background-clip:text;background-clip:text;color:transparent;">
                actually trust.
              </span>
            </h1>
            <p style="font-size:18px;color:#94A3B8;max-width:560px;line-height:1.65;margin:0;">
              Score every model response for correctness, safety, and hallucination.
              Surface failures fast. Ship with confidence.
            </p>
            <div class="tl-hero-ctas" style="display:flex;flex-wrap:wrap;gap:12px;justify-content:center;margin-top:4px;">
              <a href="#tl-signin" style="display:inline-flex;align-items:center;padding:14px 26px;
                  border-radius:12px;font-size:15px;font-weight:600;
                  background:linear-gradient(135deg,#6366F1,#8B5CF6);color:white;text-decoration:none;
                  box-shadow:0 4px 16px rgba(99,102,241,0.30);">Start Evaluating &nbsp;→</a>
              <a href="#tl-how" style="display:inline-flex;align-items:center;padding:14px 26px;
                  border-radius:12px;font-size:15px;font-weight:600;background:transparent;
                  color:#818CF8;border:1px solid #6366F1;text-decoration:none;">Watch Demo &nbsp;▶</a>
            </div>
            <div style="display:flex;flex-direction:column;align-items:center;gap:12px;margin-top:16px;">
              <div style="display:inline-flex;align-items:center;gap:12px;font-size:14.5px;color:white;font-weight:500;">
                <span style="width:22px;height:22px;border-radius:50%;background:rgba(99,102,241,0.15);
                             border:1px solid #6366F1;display:inline-flex;align-items:center;justify-content:center;
                             color:#818CF8;font-size:11px;font-weight:700;flex-shrink:0;">✓</span>
                Trace every prompt &amp; response in real time
              </div>
              <div style="display:inline-flex;align-items:center;gap:12px;font-size:14.5px;color:white;font-weight:500;">
                <span style="width:22px;height:22px;border-radius:50%;background:rgba(99,102,241,0.15);
                             border:1px solid #6366F1;display:inline-flex;align-items:center;justify-content:center;
                             color:#818CF8;font-size:11px;font-weight:700;flex-shrink:0;">✓</span>
                Compare models side-by-side on safety &amp; quality
              </div>
              <div style="display:inline-flex;align-items:center;gap:12px;font-size:14.5px;color:white;font-weight:500;">
                <span style="width:22px;height:22px;border-radius:50%;background:rgba(99,102,241,0.15);
                             border:1px solid #6366F1;display:inline-flex;align-items:center;justify-content:center;
                             color:#818CF8;font-size:11px;font-weight:700;flex-shrink:0;">✓</span>
                Detect hallucinations, bias &amp; safety violations automatically
              </div>
            </div>
          </div>
        </section>
    """), unsafe_allow_html=True)

    # ── STATS BAR ─────────────────────────────────────────────────────
    st.markdown(_h("""
        <section style="background:#13153A;border-top:1px solid #1E1F4E;border-bottom:1px solid #1E1F4E;
                        padding:56px 24px;font-family:'Inter',system-ui,sans-serif;">
          <div class="tl-stats-grid" style="max-width:1100px;margin:0 auto;
                display:grid;grid-template-columns:repeat(3,1fr);gap:0;align-items:center;">
            <div style="text-align:center;padding:16px 24px;">
              <div style="font-size:48px;font-weight:700;color:#818CF8;line-height:1;
                          letter-spacing:-0.02em;font-variant-numeric:tabular-nums;">12</div>
              <div style="font-size:14px;color:#94A3B8;margin-top:10px;font-weight:500;">Models Supported</div>
            </div>
            <div style="text-align:center;padding:16px 24px;position:relative;">
              <div style="position:absolute;left:0;top:18%;bottom:18%;width:1px;background:#1E1F4E;"></div>
              <div style="font-size:48px;font-weight:700;color:#818CF8;line-height:1;
                          letter-spacing:-0.02em;font-variant-numeric:tabular-nums;">6</div>
              <div style="font-size:14px;color:#94A3B8;margin-top:10px;font-weight:500;">Trust Dimensions</div>
            </div>
            <div style="text-align:center;padding:16px 24px;position:relative;">
              <div style="position:absolute;left:0;top:18%;bottom:18%;width:1px;background:#1E1F4E;"></div>
              <div style="font-size:48px;font-weight:700;color:#475569;line-height:1;letter-spacing:0.04em;">--</div>
              <div style="font-size:14px;color:#94A3B8;margin-top:10px;font-weight:500;">Avg Trust Score</div>
            </div>
          </div>
          <p style="max-width:1100px;margin:24px auto 0;text-align:center;font-size:11px;
                    color:#94A3B8;font-style:italic;line-height:1.5;">
            Run your first evaluation to see live stats. * Scores reflect current deployment session;
            data resets on redeploy (Streamlit Cloud ephemeral FS).
          </p>
        </section>
    """), unsafe_allow_html=True)

    # ── HOW IT WORKS ──────────────────────────────────────────────────
    st.markdown(_h("""
        <section id="tl-how" style="background:#0F1030;padding:80px 24px;font-family:'Inter',system-ui,sans-serif;">
        <div style="max-width:780px;margin:0 auto;">
        <div style="text-align:center;margin-bottom:56px;">
        <span style="font-size:11px;font-weight:700;letter-spacing:0.18em;text-transform:uppercase;color:#6366F1;">HOW IT WORKS</span>
        <h2 style="font-size:36px;font-weight:800;line-height:1.15;letter-spacing:-0.02em;margin:12px 0 0;color:white;">
        From prompt to <span style="background:linear-gradient(135deg,#6366F1,#8B5CF6);-webkit-background-clip:text;background-clip:text;color:transparent;">trust score</span> in seconds
        </h2>
        <p style="font-size:16px;color:#94A3B8;line-height:1.65;margin:12px 0 0;">
        Five-stage pipeline — repeatable, deterministic evals.
        </p>
        </div>
        <div style="position:relative;">
        <div style="position:absolute;left:27px;top:28px;bottom:28px;width:0;border-left:2px dashed #4338CA;opacity:0.5;z-index:0;"></div>
        <div style="display:flex;flex-direction:column;gap:20px;position:relative;z-index:1;">
        <div style="display:flex;gap:18px;align-items:flex-start;">
        <div style="width:56px;height:56px;border-radius:50%;background:#13153A;border:2px solid #6366F1;display:flex;align-items:center;justify-content:center;font-family:monospace;font-size:15px;font-weight:700;color:#818CF8;flex-shrink:0;box-shadow:0 0 0 5px #0F1030;">01</div>
        <div style="flex:1;background:#13153A;border:1px solid #1E1F4E;border-left:3px solid #6366F1;border-radius:14px;padding:20px 22px;">
        <div style="font-family:monospace;font-size:10px;color:#6366F1;letter-spacing:0.18em;text-transform:uppercase;margin-bottom:6px;">01 · Input</div>
        <h3 style="font-size:18px;font-weight:700;margin:0 0 8px;color:white;">Submit a prompt</h3>
        <p style="color:#94A3B8;font-size:14px;line-height:1.6;margin:0;">Single prompt or upload a CSV / JSON dataset. Drop it in — that's the whole interface.</p>
        </div>
        </div>
        <div style="display:flex;gap:18px;align-items:flex-start;">
        <div style="width:56px;height:56px;border-radius:50%;background:#13153A;border:2px solid #6366F1;display:flex;align-items:center;justify-content:center;font-family:monospace;font-size:15px;font-weight:700;color:#818CF8;flex-shrink:0;box-shadow:0 0 0 5px #0F1030;">02</div>
        <div style="flex:1;background:#13153A;border:1px solid #1E1F4E;border-left:3px solid #6366F1;border-radius:14px;padding:20px 22px;">
        <div style="font-family:monospace;font-size:10px;color:#6366F1;letter-spacing:0.18em;text-transform:uppercase;margin-bottom:6px;">02 · Model Selection</div>
        <h3 style="font-size:18px;font-weight:700;margin:0 0 8px;color:white;">Pick from 12 models</h3>
        <p style="color:#94A3B8;font-size:14px;line-height:1.6;margin:0 0 12px;">Six providers, two models each — swap in your own endpoint via Ollama or hosted API.</p>
        <div style="display:flex;flex-wrap:wrap;gap:6px;">
        <span style="padding:5px 10px;background:rgba(99,102,241,0.10);border:1px solid #6366F1;border-radius:999px;font-size:12px;color:#818CF8;font-weight:500;">Groq</span>
        <span style="padding:5px 10px;background:rgba(99,102,241,0.10);border:1px solid #6366F1;border-radius:999px;font-size:12px;color:#818CF8;font-weight:500;">Claude</span>
        <span style="padding:5px 10px;background:rgba(99,102,241,0.10);border:1px solid #6366F1;border-radius:999px;font-size:12px;color:#818CF8;font-weight:500;">GPT</span>
        <span style="padding:5px 10px;background:rgba(99,102,241,0.10);border:1px solid #6366F1;border-radius:999px;font-size:12px;color:#818CF8;font-weight:500;">Gemini</span>
        <span style="padding:5px 10px;background:rgba(99,102,241,0.10);border:1px solid #6366F1;border-radius:999px;font-size:12px;color:#818CF8;font-weight:500;">Mistral</span>
        <span style="padding:5px 10px;background:rgba(99,102,241,0.10);border:1px solid #6366F1;border-radius:999px;font-size:12px;color:#818CF8;font-weight:500;">Phi</span>
        </div>
        </div>
        </div>
        <div style="display:flex;gap:18px;align-items:flex-start;">
        <div style="width:56px;height:56px;border-radius:50%;background:#13153A;border:2px solid #6366F1;display:flex;align-items:center;justify-content:center;font-family:monospace;font-size:15px;font-weight:700;color:#818CF8;flex-shrink:0;box-shadow:0 0 0 5px #0F1030;">03</div>
        <div style="flex:1;background:#13153A;border:1px solid #1E1F4E;border-left:3px solid #6366F1;border-radius:14px;padding:20px 22px;">
        <div style="font-family:monospace;font-size:10px;color:#6366F1;letter-spacing:0.18em;text-transform:uppercase;margin-bottom:6px;">03 · Eval Mode</div>
        <h3 style="font-size:18px;font-weight:700;margin:0 0 8px;color:white;">Choose your test path</h3>
        <p style="color:#94A3B8;font-size:14px;line-height:1.6;margin:0 0 12px;">Pick the mode that matches your test — every mode shares the same downstream judge.</p>
        <div style="display:flex;flex-wrap:wrap;gap:8px;">
        <span style="padding:7px 13px;background:#6366F1;border-radius:8px;font-size:13px;color:white;font-weight:500;">Run Evaluation</span>
        <span style="padding:7px 13px;background:transparent;border:1px solid #4338CA;border-radius:8px;font-size:13px;color:#94A3B8;font-weight:500;">RAG Testing</span>
        <span style="padding:7px 13px;background:transparent;border:1px solid #4338CA;border-radius:8px;font-size:13px;color:#94A3B8;font-weight:500;">Batch Dataset</span>
        </div>
        </div>
        </div>
        <div style="display:flex;gap:18px;align-items:flex-start;">
        <div style="width:56px;height:56px;border-radius:50%;background:#13153A;border:2px solid #6366F1;display:flex;align-items:center;justify-content:center;font-family:monospace;font-size:15px;font-weight:700;color:#818CF8;flex-shrink:0;box-shadow:0 0 0 5px #0F1030;">04</div>
        <div style="flex:1;background:#13153A;border:1px solid #1E1F4E;border-left:3px solid #6366F1;border-radius:14px;padding:20px 22px;">
        <div style="font-family:monospace;font-size:10px;color:#6366F1;letter-spacing:0.18em;text-transform:uppercase;margin-bottom:6px;">04 · LLM-as-Judge Scoring</div>
        <h3 style="font-size:18px;font-weight:700;margin:0 0 8px;color:white;">Six dimensions, one trust score</h3>
        <p style="color:#94A3B8;font-size:14px;line-height:1.6;margin:0 0 12px;">Each dimension scored independently, then averaged into a 0–1 trust score.</p>
        <div style="display:flex;flex-direction:column;gap:7px;">
        <div style="display:flex;align-items:center;gap:10px;font-size:13px;"><span style="color:#cbd5e1;width:90px;flex-shrink:0;">Truthfulness</span><div style="flex:1;background:#1E1F4E;height:5px;border-radius:999px;overflow:hidden;"><div style="height:100%;width:92%;background:linear-gradient(90deg,#6366F1,#8B5CF6);border-radius:999px;"></div></div><span style="font-family:monospace;font-size:11px;color:#94A3B8;width:30px;text-align:right;">0.92</span></div>
        <div style="display:flex;align-items:center;gap:10px;font-size:13px;"><span style="color:#cbd5e1;width:90px;flex-shrink:0;">Safety</span><div style="flex:1;background:#1E1F4E;height:5px;border-radius:999px;overflow:hidden;"><div style="height:100%;width:88%;background:linear-gradient(90deg,#6366F1,#8B5CF6);border-radius:999px;"></div></div><span style="font-family:monospace;font-size:11px;color:#94A3B8;width:30px;text-align:right;">0.88</span></div>
        <div style="display:flex;align-items:center;gap:10px;font-size:13px;"><span style="color:#cbd5e1;width:90px;flex-shrink:0;">Fairness</span><div style="flex:1;background:#1E1F4E;height:5px;border-radius:999px;overflow:hidden;"><div style="height:100%;width:74%;background:linear-gradient(90deg,#6366F1,#8B5CF6);border-radius:999px;"></div></div><span style="font-family:monospace;font-size:11px;color:#94A3B8;width:30px;text-align:right;">0.74</span></div>
        <div style="display:flex;align-items:center;gap:10px;font-size:13px;"><span style="color:#cbd5e1;width:90px;flex-shrink:0;">Privacy</span><div style="flex:1;background:#1E1F4E;height:5px;border-radius:999px;overflow:hidden;"><div style="height:100%;width:81%;background:linear-gradient(90deg,#6366F1,#8B5CF6);border-radius:999px;"></div></div><span style="font-family:monospace;font-size:11px;color:#94A3B8;width:30px;text-align:right;">0.81</span></div>
        <div style="display:flex;align-items:center;gap:10px;font-size:13px;"><span style="color:#cbd5e1;width:90px;flex-shrink:0;">Robustness</span><div style="flex:1;background:#1E1F4E;height:5px;border-radius:999px;overflow:hidden;"><div style="height:100%;width:69%;background:linear-gradient(90deg,#6366F1,#8B5CF6);border-radius:999px;"></div></div><span style="font-family:monospace;font-size:11px;color:#94A3B8;width:30px;text-align:right;">0.69</span></div>
        <div style="display:flex;align-items:center;gap:10px;font-size:13px;"><span style="color:#cbd5e1;width:90px;flex-shrink:0;">Ethics</span><div style="flex:1;background:#1E1F4E;height:5px;border-radius:999px;overflow:hidden;"><div style="height:100%;width:85%;background:linear-gradient(90deg,#6366F1,#8B5CF6);border-radius:999px;"></div></div><span style="font-family:monospace;font-size:11px;color:#94A3B8;width:30px;text-align:right;">0.85</span></div>
        </div>
        <div style="display:inline-flex;margin-top:12px;padding:8px 12px;background:rgba(99,102,241,0.10);border:1px solid #6366F1;border-radius:8px;font-family:monospace;font-size:12px;color:#818CF8;">Trust Score = Σ(6 dims) / 6</div>
        </div>
        </div>
        <div style="display:flex;gap:18px;align-items:flex-start;">
        <div style="width:56px;height:56px;border-radius:50%;background:#13153A;border:2px solid #6366F1;display:flex;align-items:center;justify-content:center;font-family:monospace;font-size:15px;font-weight:700;color:#818CF8;flex-shrink:0;box-shadow:0 0 0 5px #0F1030;">05</div>
        <div style="flex:1;background:#13153A;border:1px solid #1E1F4E;border-left:3px solid #6366F1;border-radius:14px;padding:20px 22px;">
        <div style="font-family:monospace;font-size:10px;color:#6366F1;letter-spacing:0.18em;text-transform:uppercase;margin-bottom:6px;">05 · Results</div>
        <h3 style="font-size:18px;font-weight:700;margin:0 0 8px;color:white;">Slice it however you ship</h3>
        <p style="color:#94A3B8;font-size:14px;line-height:1.6;margin:0 0 12px;">Three views, all rendered from the same merged results file.</p>
        <div style="display:flex;gap:8px;flex-wrap:wrap;">
        <div style="background:#0F1030;border:1px solid #1E1F4E;border-radius:10px;padding:12px 16px;display:flex;align-items:center;gap:8px;"><span style="font-size:14px;">📋</span><span style="font-size:13px;font-weight:600;color:#e2e8f0;">Per-Eval Breakdown</span></div>
        <div style="background:#0F1030;border:1px solid #1E1F4E;border-radius:10px;padding:12px 16px;display:flex;align-items:center;gap:8px;"><span style="font-size:14px;">⏱</span><span style="font-size:13px;font-weight:600;color:#e2e8f0;">Session History</span></div>
        <div style="background:#0F1030;border:1px solid #1E1F4E;border-radius:10px;padding:12px 16px;display:flex;align-items:center;gap:8px;"><span style="font-size:14px;">🏆</span><span style="font-size:13px;font-weight:600;color:#e2e8f0;">Leaderboard</span></div>
        </div>
        </div>
        </div>
        </div>
        </div>
        </div>
        </section>
    """), unsafe_allow_html=True)

    # ── TRUST DIMENSIONS ──────────────────────────────────────────────
    st.markdown(_h("""
        <section id="tl-dimensions" style="background:#0A0B1A;padding:96px 24px;
                                            font-family:'Inter',system-ui,sans-serif;">
          <div style="max-width:1180px;margin:0 auto;">
            <div style="text-align:center;margin-bottom:48px;display:flex;
                        flex-direction:column;align-items:center;gap:12px;">
              <span style="font-size:11px;font-weight:700;letter-spacing:0.18em;
                           text-transform:uppercase;color:#6366F1;">TRUST DIMENSIONS</span>
              <h2 style="font-size:44px;font-weight:800;line-height:1.1;letter-spacing:-0.025em;
                          margin:0;max-width:720px;color:white;">
                <span style="background:linear-gradient(135deg,#6366F1,#8B5CF6);
                  -webkit-background-clip:text;background-clip:text;color:transparent;">6 Dimensions</span> of Trust
              </h2>
              <p style="font-size:17px;color:#94A3B8;max-width:620px;line-height:1.65;margin:0;">
                Each independent, each scored 0–1, each surfaced in your final report.
              </p>
            </div>
            <div class="tl-dims-grid" style="display:grid;grid-template-columns:repeat(3,1fr);gap:18px;">
              <div style="background:#13153A;border:1px solid #1E1F4E;border-top:2px solid transparent;
                          border-radius:14px;padding:26px 24px;transition:border-color 0.2s,transform 0.2s;">
                <div style="width:48px;height:48px;border-radius:50%;background:rgba(99,102,241,0.12);
                            color:#818CF8;display:flex;align-items:center;justify-content:center;
                            font-size:22px;margin-bottom:16px;">🔍</div>
                <h3 style="font-size:17px;font-weight:700;letter-spacing:-0.01em;margin-bottom:8px;color:white;">Truthfulness</h3>
                <p style="color:#94A3B8;font-size:14px;line-height:1.55;margin:0;">Factual grounding measured against expected answers and retrieved context.</p>
              </div>
              <div style="background:#13153A;border:1px solid #1E1F4E;border-top:2px solid transparent;
                          border-radius:14px;padding:26px 24px;">
                <div style="width:48px;height:48px;border-radius:50%;background:rgba(99,102,241,0.12);
                            color:#818CF8;display:flex;align-items:center;justify-content:center;
                            font-size:22px;margin-bottom:16px;">🛡</div>
                <h3 style="font-size:17px;font-weight:700;letter-spacing:-0.01em;margin-bottom:8px;color:white;">Safety</h3>
                <p style="color:#94A3B8;font-size:14px;line-height:1.55;margin:0;">Jailbreak resistance, harmful content detection, and prompt-injection scoring.</p>
              </div>
              <div style="background:#13153A;border:1px solid #1E1F4E;border-top:2px solid transparent;
                          border-radius:14px;padding:26px 24px;">
                <div style="width:48px;height:48px;border-radius:50%;background:rgba(99,102,241,0.12);
                            color:#818CF8;display:flex;align-items:center;justify-content:center;
                            font-size:22px;margin-bottom:16px;">⚖</div>
                <h3 style="font-size:17px;font-weight:700;letter-spacing:-0.01em;margin-bottom:8px;color:white;">Fairness</h3>
                <p style="color:#94A3B8;font-size:14px;line-height:1.55;margin:0;">Demographic bias, group fairness, and toxicity across diverse prompts.</p>
              </div>
              <div style="background:#13153A;border:1px solid #1E1F4E;border-top:2px solid transparent;
                          border-radius:14px;padding:26px 24px;">
                <div style="width:48px;height:48px;border-radius:50%;background:rgba(99,102,241,0.12);
                            color:#818CF8;display:flex;align-items:center;justify-content:center;
                            font-size:22px;margin-bottom:16px;">🔒</div>
                <h3 style="font-size:17px;font-weight:700;letter-spacing:-0.01em;margin-bottom:8px;color:white;">Privacy</h3>
                <p style="color:#94A3B8;font-size:14px;line-height:1.55;margin:0;">PII leakage detection, data exfiltration risk, and consent boundary checks.</p>
              </div>
              <div style="background:#13153A;border:1px solid #1E1F4E;border-top:2px solid transparent;
                          border-radius:14px;padding:26px 24px;">
                <div style="width:48px;height:48px;border-radius:50%;background:rgba(99,102,241,0.12);
                            color:#818CF8;display:flex;align-items:center;justify-content:center;
                            font-size:22px;margin-bottom:16px;">💪</div>
                <h3 style="font-size:17px;font-weight:700;letter-spacing:-0.01em;margin-bottom:8px;color:white;">Robustness</h3>
                <p style="color:#94A3B8;font-size:14px;line-height:1.55;margin:0;">Behavior under adversarial inputs, paraphrasing, and edge-case stress tests.</p>
              </div>
              <div style="background:#13153A;border:1px solid #1E1F4E;border-top:2px solid transparent;
                          border-radius:14px;padding:26px 24px;">
                <div style="width:48px;height:48px;border-radius:50%;background:rgba(99,102,241,0.12);
                            color:#818CF8;display:flex;align-items:center;justify-content:center;
                            font-size:22px;margin-bottom:16px;">🧭</div>
                <h3 style="font-size:17px;font-weight:700;letter-spacing:-0.01em;margin-bottom:8px;color:white;">Ethics</h3>
                <p style="color:#94A3B8;font-size:14px;line-height:1.55;margin:0;">Alignment with use-case norms, refusal quality, and decision-rationale clarity.</p>
              </div>
            </div>
          </div>
        </section>
    """), unsafe_allow_html=True)

    # ── MODELS ────────────────────────────────────────────────────────
    st.markdown(_h("""
        <section id="tl-models" style="background:#0F1030;padding:96px 24px;
                                        font-family:'Inter',system-ui,sans-serif;">
          <div style="max-width:1180px;margin:0 auto;">
            <div style="text-align:center;margin-bottom:48px;display:flex;
                        flex-direction:column;align-items:center;gap:12px;">
              <span style="font-size:11px;font-weight:700;letter-spacing:0.18em;
                           text-transform:uppercase;color:#6366F1;">MODELS</span>
              <h2 style="font-size:44px;font-weight:800;line-height:1.1;letter-spacing:-0.025em;
                          margin:0;max-width:720px;color:white;">
                12 Models. <span style="background:linear-gradient(135deg,#6366F1,#8B5CF6);
                  -webkit-background-clip:text;background-clip:text;color:transparent;">One Platform.</span>
              </h2>
              <p style="font-size:17px;color:#94A3B8;max-width:620px;line-height:1.65;margin:0;">
                Match exactly the model IDs in
                <code style="font-family:monospace;font-size:0.85em;color:#818CF8;">providers.py</code>.
                No vendored adapters, no surprises.
              </p>
            </div>
            <div class="tl-models-row" style="display:grid;grid-template-columns:repeat(6,1fr);gap:12px;">
              <div class="tl-model-card" style="background:#13153A;border:1px solid #1E1F4E;border-radius:12px;padding:18px;color:#94A3B8;">
                <div style="font-size:15px;font-weight:700;color:white;margin-bottom:8px;">Groq</div>
                <ul style="list-style:none;padding:0;margin:0;">
                  <li style="font-family:monospace;font-size:12px;padding:3px 0;line-height:1.4;">llama3-8b-8192</li>
                  <li style="font-family:monospace;font-size:12px;padding:3px 0;line-height:1.4;">mixtral-8x7b-32768</li>
                </ul>
              </div>
              <div class="tl-model-card" style="background:#13153A;border:1px solid #1E1F4E;border-radius:12px;padding:18px;color:#94A3B8;">
                <div style="font-size:15px;font-weight:700;color:white;margin-bottom:8px;">Claude</div>
                <ul style="list-style:none;padding:0;margin:0;">
                  <li style="font-family:monospace;font-size:12px;padding:3px 0;line-height:1.4;">claude-haiku-3</li>
                  <li style="font-family:monospace;font-size:12px;padding:3px 0;line-height:1.4;">claude-sonnet-3-5</li>
                </ul>
              </div>
              <div class="tl-model-card" style="background:#13153A;border:1px solid #1E1F4E;border-radius:12px;padding:18px;color:#94A3B8;">
                <div style="font-size:15px;font-weight:700;color:white;margin-bottom:8px;">OpenAI</div>
                <ul style="list-style:none;padding:0;margin:0;">
                  <li style="font-family:monospace;font-size:12px;padding:3px 0;line-height:1.4;">gpt-4o</li>
                  <li style="font-family:monospace;font-size:12px;padding:3px 0;line-height:1.4;">gpt-4o-mini</li>
                </ul>
              </div>
              <div class="tl-model-card" style="background:#13153A;border:1px solid #1E1F4E;border-radius:12px;padding:18px;color:#94A3B8;">
                <div style="font-size:15px;font-weight:700;color:white;margin-bottom:8px;">Gemini</div>
                <ul style="list-style:none;padding:0;margin:0;">
                  <li style="font-family:monospace;font-size:12px;padding:3px 0;line-height:1.4;">gemini-1.5-pro</li>
                  <li style="font-family:monospace;font-size:12px;padding:3px 0;line-height:1.4;">gemini-1.5-flash</li>
                </ul>
              </div>
              <div class="tl-model-card" style="background:#13153A;border:1px solid #1E1F4E;border-radius:12px;padding:18px;color:#94A3B8;">
                <div style="font-size:15px;font-weight:700;color:white;margin-bottom:8px;">Mistral</div>
                <ul style="list-style:none;padding:0;margin:0;">
                  <li style="font-family:monospace;font-size:12px;padding:3px 0;line-height:1.4;">mistral-7b-instruct</li>
                  <li style="font-family:monospace;font-size:12px;padding:3px 0;line-height:1.4;">mistral-large-latest</li>
                </ul>
              </div>
              <div class="tl-model-card" style="background:#13153A;border:1px solid #1E1F4E;border-radius:12px;padding:18px;color:#94A3B8;">
                <div style="font-size:15px;font-weight:700;color:white;margin-bottom:8px;">Phi</div>
                <ul style="list-style:none;padding:0;margin:0;">
                  <li style="font-family:monospace;font-size:12px;padding:3px 0;line-height:1.4;">phi3-mini</li>
                  <li style="font-family:monospace;font-size:12px;padding:3px 0;line-height:1.4;">phi3-medium</li>
                </ul>
              </div>
            </div>
          </div>
        </section>
    """), unsafe_allow_html=True)

    # ── RAG CALLOUT ───────────────────────────────────────────────────
    st.markdown(_h("""
        <section id="tl-rag" style="background:linear-gradient(135deg,#13153A 0%,#1a1060 100%);
                                     border-top:1px solid #1E1F4E;border-bottom:1px solid #1E1F4E;
                                     padding:96px 24px;text-align:center;
                                     font-family:'Inter',system-ui,sans-serif;">
          <div style="max-width:1180px;margin:0 auto;">
            <span style="font-size:11px;font-weight:700;letter-spacing:0.18em;
                         text-transform:uppercase;color:#6366F1;">RAG PIPELINE</span>
            <h2 style="font-size:44px;font-weight:800;line-height:1.1;letter-spacing:-0.025em;
                        margin:14px auto 18px;max-width:720px;color:white;">
              <span style="background:linear-gradient(135deg,#6366F1,#8B5CF6);
                -webkit-background-clip:text;background-clip:text;color:transparent;">RAG Pipeline?</span>
              We measure that too.
            </h2>
            <p style="font-size:17px;color:#94A3B8;max-width:620px;line-height:1.65;
                      margin:0 auto;">
              If your run went through RAG, four classical IR metrics surface alongside the trust score.
            </p>
            <div style="display:flex;flex-wrap:wrap;gap:10px;justify-content:center;margin:24px 0 16px;">
              <div style="background:#6366F1;color:white;padding:8px 18px;border-radius:999px;
                          font-family:monospace;font-size:13px;font-weight:500;">Precision@K</div>
              <div style="background:#6366F1;color:white;padding:8px 18px;border-radius:999px;
                          font-family:monospace;font-size:13px;font-weight:500;">Recall@K</div>
              <div style="background:#6366F1;color:white;padding:8px 18px;border-radius:999px;
                          font-family:monospace;font-size:13px;font-weight:500;">MRR</div>
              <div style="background:#6366F1;color:white;padding:8px 18px;border-radius:999px;
                          font-family:monospace;font-size:13px;font-weight:500;">NDCG</div>
            </div>
            <div style="display:flex;flex-wrap:wrap;justify-content:center;align-items:center;
                        gap:10px;margin:16px 0 28px;">
              <div style="background:rgba(99,102,241,0.10);border:1px solid #6366F1;border-radius:10px;
                          padding:10px 16px;font-size:13px;color:#818CF8;">40% Relevance</div>
              <span style="color:#94A3B8;font-weight:600;">+</span>
              <div style="background:rgba(99,102,241,0.10);border:1px solid #6366F1;border-radius:10px;
                          padding:10px 16px;font-size:13px;color:#818CF8;">40% Completeness</div>
              <span style="color:#94A3B8;font-weight:600;">+</span>
              <div style="background:rgba(99,102,241,0.10);border:1px solid #6366F1;border-radius:10px;
                          padding:10px 16px;font-size:13px;color:#818CF8;">20% Source Count</div>
            </div>
            <a href="#tl-signin" style="display:inline-flex;align-items:center;padding:14px 26px;
                border-radius:12px;font-size:15px;font-weight:600;
                background:linear-gradient(135deg,#6366F1,#8B5CF6);color:white;text-decoration:none;
                box-shadow:0 4px 16px rgba(99,102,241,0.30);">Try RAG Testing &nbsp;→</a>
          </div>
        </section>
    """), unsafe_allow_html=True)

    # ── SIGN-IN SECTION HEADER ────────────────────────────────────────
    st.markdown(_h("""
        <div id="tl-signin" style="background:#0A0B1A;padding:96px 24px 40px;text-align:center;
                                    font-family:'Inter',system-ui,sans-serif;">
          <div style="max-width:1180px;margin:0 auto;">
            <span style="font-size:11px;font-weight:700;letter-spacing:0.18em;
                         text-transform:uppercase;color:#6366F1;">GET STARTED</span>
            <h2 style="font-size:44px;font-weight:800;line-height:1.1;letter-spacing:-0.025em;
                        margin:14px auto 18px;max-width:720px;color:white;">
              Start evaluating your models
              <span style="background:linear-gradient(135deg,#6366F1,#8B5CF6);
                -webkit-background-clip:text;background-clip:text;color:transparent;">today.</span>
            </h2>
            <p style="font-size:17px;color:#94A3B8;max-width:620px;line-height:1.65;
                      margin:0 auto 0;">
              Free to try. No credit card required.
            </p>
          </div>
        </div>
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
                btn_cols = st.columns(2) if (_google_ok and _github_ok) else [None, None]

                # Google button — state prefixed with "google:" so callback can identify provider
                if _google_ok:
                    _g_state = "google:" + _google_generate_state()
                    google_url = _google_auth_url(_g_state)
                    google_html = f"""
                        <a href="{google_url}" target="_top"
                           style="display:flex;align-items:center;justify-content:center;gap:0.55rem;
                                  background:white;color:#374151;border:1px solid #d1d5db;
                                  border-radius:8px;padding:0.7rem 0.5rem;font-size:0.875rem;font-weight:500;
                                  text-decoration:none;box-sizing:border-box;width:100%;">
                        <svg width="16" height="16" viewBox="0 0 48 48" style="flex-shrink:0;">
                        <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
                        <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
                        <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
                        <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
                        </svg>
                        Continue with Google
                        </a>"""
                    if _github_ok and btn_cols[0]:
                        with btn_cols[0]:
                            st.markdown(google_html, unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div style="margin-bottom:0.75rem;">{google_html}</div>', unsafe_allow_html=True)

                # GitHub button — state prefixed with "github:" so callback can identify provider
                if _github_ok:
                    _gh_state = "github:" + _github_generate_state()
                    github_url = _github_auth_url(_gh_state)
                    github_html = f"""
                        <a href="{github_url}" target="_top"
                           style="display:flex;align-items:center;justify-content:center;gap:0.55rem;
                                  background:#24292e;color:white;border:1px solid #24292e;
                                  border-radius:8px;padding:0.7rem 0.5rem;font-size:0.875rem;font-weight:500;
                                  text-decoration:none;box-sizing:border-box;width:100%;">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="white" style="flex-shrink:0;">
                        <path d="M12 0C5.37 0 0 5.37 0 12c0 5.3 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577
                        0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61-.546-1.385-1.335-1.755-1.335-1.755
                        -1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305
                        3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38
                        1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399
                        3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24
                        2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81
                        1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 21.795 24
                        17.295 24 12c0-6.63-5.37-12-12-12z"/>
                        </svg>
                        Continue with GitHub
                        </a>"""
                    if _google_ok and btn_cols[1]:
                        with btn_cols[1]:
                            st.markdown(github_html, unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div style="margin-bottom:0.75rem;">{github_html}</div>', unsafe_allow_html=True)

                st.markdown("<div style='margin-bottom:0.25rem;'></div>", unsafe_allow_html=True)

            except Exception as _e:
                st.warning(f"OAuth sign-in unavailable: {_e}")
        else:
            st.markdown(_h("""
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;margin-bottom:1rem;">
                <button style="background:white;color:#374151;border:1px solid #d1d5db;border-radius:8px;
                               padding:0.7rem 0.5rem;font-size:0.875rem;font-weight:500;
                               font-family:inherit;opacity:0.45;cursor:not-allowed;">
                🌐 Continue with Google
                </button>
                <button style="background:#24292e;color:white;border:1px solid #24292e;border-radius:8px;
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
            <div style="flex:1;border-top:1px solid #e5e7eb;"></div>
            <span style="color:#9ca3af;font-size:0.8rem;font-weight:500;white-space:nowrap;">or continue with email</span>
            <div style="flex:1;border-top:1px solid #e5e7eb;"></div>
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
            <span style="color:#94A3B8;font-size:0.8rem;">
            Demo — Username: <strong style="color:#cbd5e1;">TestUser</strong>
            &nbsp;·&nbsp; Password: <strong style="color:#cbd5e1;">User123</strong>
            </span>
            </div>
        """), unsafe_allow_html=True)

    # ── FOOTER ────────────────────────────────────────────────────────
    st.markdown(_h("""
        <footer style="background:#0A0B1A;border-top:1px solid #1E1F4E;padding:36px 24px;
                        text-align:center;color:#94A3B8;font-size:13px;
                        font-family:'Inter',system-ui,sans-serif;">
          <div style="display:inline-flex;flex-wrap:wrap;gap:24px;justify-content:center;margin-bottom:14px;">
            <a href="#tl-how" style="color:#94A3B8;font-size:13px;text-decoration:none;">How it works</a>
            <a href="#tl-dimensions" style="color:#94A3B8;font-size:13px;text-decoration:none;">Trust dimensions</a>
            <a href="#tl-models" style="color:#94A3B8;font-size:13px;text-decoration:none;">Models</a>
            <a href="#tl-signin" style="color:#94A3B8;font-size:13px;text-decoration:none;">Sign in</a>
          </div>
          <div>© 2025 TrustLLM · AI Model Evaluation Platform · Powered by ChromaDB · Groq · Streamlit ·
            Built by <a href="https://www.linkedin.com/in/monika-kushwaha-52443735/" target="_blank"
              rel="noopener" style="color:#818CF8;font-weight:500;text-decoration:none;">Monika Kushwaha</a>
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
              nav.style.borderBottomColor = window.parent.scrollY > 8 ? '#1E1F4E' : 'transparent';
            }, {passive: true});
          }
          // Dark card wrapper for the middle (form) column
          var cols = window.parent.document.querySelectorAll('[data-testid="stColumn"]');
          if (cols.length >= 3) {
            var mid = cols[Math.floor(cols.length / 2)];
            mid.style.background = '#13153A';
            mid.style.border = '1px solid #1E1F4E';
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
            <div style="background:#4f46e5;width:24px;height:24px;border-radius:5px;
                        display:flex;align-items:center;justify-content:center;
                        font-size:0.75rem;color:white;">🛡</div>
            <span style="font-weight:700;color:#111827;font-size:0.95rem;
                         letter-spacing:-0.01em;">TrustLLM</span>
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
        st.markdown(
            '<button onclick="if(window._cmdOpen){window._cmdOpen();}else{'
            'var o=document.getElementById(\'cmd-overlay\');'
            'var inp=document.getElementById(\'cmd-input\');'
            'o.classList.add(\'open\');inp.value=\'\';'
            'inp.dispatchEvent(new Event(\'input\',{bubbles:true}));'
            'setTimeout(function(){inp.focus();},60);}" '
            'style="width:100%;padding:0.42rem 0.75rem;background:#18181b;color:#a1a1aa;'
            'border:1px solid #27272a;border-radius:7px;font-size:0.82rem;font-weight:500;'
            'cursor:pointer;font-family:inherit;transition:background 0.15s;">'
            '⌘K&nbsp;&nbsp;Command palette</button>',
            unsafe_allow_html=True,
        )
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
        <div style="display:flex;align-items:center;gap:0.5rem;">
            <span style="font-size:1rem;">🛡</span>
            <span style="font-size:0.95rem;font-weight:700;color:#fafafa;">TrustLLM</span>
        </div>
        <div style="font-size:0.72rem;color:#52525b;margin-top:0.2rem;">
            {user_name}
        </div>
    </div>""",
    unsafe_allow_html=True,
)

st.sidebar.markdown('<hr style="border:none;border-top:1px solid #18181b;margin:0 0 0.25rem;">', unsafe_allow_html=True)

page = st.session_state["_current_page"]

for section, items in _SECTIONS.items():
    st.sidebar.markdown(f'<div class="sb-section">{section}</div>', unsafe_allow_html=True)
    for icon, label in items:
        is_active = (page == label)
        btn_label = f"{'●' if is_active else '○'}  {icon}  {label}"
        btn_style = (
            "background:#18181b !important;color:#818cf8 !important;font-weight:600 !important;"
            if is_active else ""
        )
        if is_active:
            st.sidebar.markdown(
                f'<div style="{btn_style}padding:0.4rem 0.75rem;border-radius:6px;'
                f'font-size:0.87rem;color:#818cf8;font-weight:600;margin-bottom:1px;">'
                f'{icon}&nbsp;&nbsp;{label}</div>',
                unsafe_allow_html=True,
            )
        else:
            if st.sidebar.button(f"{icon}  {label}", key=f"nav_{label}", use_container_width=True):
                st.session_state["_current_page"] = label
                page = label
                st.rerun()

st.sidebar.markdown('<hr style="border:none;border-top:1px solid #18181b;margin:0.75rem 0 0.5rem;">', unsafe_allow_html=True)

# -----------------------------------------------------------------------
# Get-your-own-key quick-links (TrustLLM Pro BYOK)
# -----------------------------------------------------------------------
from llm_runner.providers import PROVIDERS as _PRO_PROVIDERS  # noqa: E402

st.sidebar.markdown('<div class="sb-section">GET API KEYS</div>', unsafe_allow_html=True)
_link_html_parts = []
for _pid, _meta in _PRO_PROVIDERS.items():
    _link_html_parts.append(
        f'<a href="{_meta["api_key_url"]}" target="_blank" rel="noopener" '
        f'style="display:block;padding:0.25rem 0.75rem;font-size:0.8rem;color:#a1a1aa;'
        f'text-decoration:none;border-radius:4px;">'
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

st.sidebar.markdown('<hr style="border:none;border-top:1px solid #18181b;margin:0.75rem 0 0.5rem;">', unsafe_allow_html=True)

st.sidebar.markdown(
    '<div style="font-size:0.7rem;color:#3f3f46;padding:0 0.75rem 0.25rem;text-align:center;">'
    'Press <kbd style="background:#18181b;border-radius:3px;padding:0.05rem 0.3rem;'
    'font-size:0.65rem;color:#52525b;font-family:monospace;">⌘K</kbd> for command palette'
    '</div>',
    unsafe_allow_html=True,
)

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
