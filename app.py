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
from auth.supabase_auth import is_configured, get_auth_url, exchange_code

BASE_DIR = Path(__file__).resolve().parent

init_db()

st.set_page_config(
    page_title="TrustLLM",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _h(html: str) -> str:
    """Strip common indentation so Markdown never reads indented HTML as a code block."""
    return textwrap.dedent(html).strip()


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
    for u in _load_local_users():
        if u["username"] == username and u["password"] == password:
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
    st.query_params.clear()
    with st.spinner("Signing you in…"):
        try:
            user_info = exchange_code(code)
        except Exception as exc:
            st.error(f"Sign-in failed: {exc}")
            return
    db_user = upsert_user(user_info)
    st.session_state["logged_in"] = True
    st.session_state["user"] = db_user or user_info
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
    stats = _hero_stats()
    bars  = _preview_bars(stats)

    st.markdown(_h("""
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header[data-testid="stHeader"] {visibility: hidden;}
        section[data-testid="stSidebar"] { display: none !important; }
        /* ── Page background — lavender for login/form area ── */
        .stApp { background: #ede9fe !important; }
        section.main { background: transparent !important; }
        /* ── Full-width: strip ALL Streamlit wrapper padding/margins ── */
        section.main .block-container,
        [data-testid="stMainBlockContainer"],
        [data-testid="stAppViewBlockContainer"] {
            padding: 0 !important;
            max-width: 100% !important;
            width: 100% !important;
            background: transparent !important;
        }
        [data-testid="stVerticalBlock"],
        [data-testid="stVerticalBlockBorderWrapper"] {
            width: 100% !important;
            max-width: 100% !important;
            padding: 0 !important;
            gap: 0 !important;
        }
        .element-container,
        [data-testid="element-container"] {
            width: 100% !important;
            max-width: 100% !important;
            padding: 0 !important;
            margin: 0 !important;
        }
        div[data-testid="stMarkdownContainer"],
        div[data-testid="stMarkdownContainer"] > div {
            width: 100% !important;
            max-width: 100% !important;
            padding: 0 !important;
            margin: 0 !important;
        }
        /* ── Make ALL Streamlit intermediate containers transparent ── */
        [data-testid="stMain"],
        [data-testid="stMainBlockContainer"],
        [data-testid="stAppViewBlockContainer"],
        [data-testid="stVerticalBlock"],
        [data-testid="stVerticalBlockBorderWrapper"],
        [data-testid="stHorizontalBlock"],
        [data-testid="stColumn"],
        [data-testid="column"],
        .stColumn, .element-container { background: transparent !important; }
        /* ── Form card — clean white card on white bg ── */
        [data-testid="stForm"] {
            background: white !important;
            border: 1px solid #e5e7eb !important;
            border-radius: 14px !important;
            padding: 1.5rem 1.5rem 0.75rem !important;
            box-shadow: 0 4px 24px rgba(0,0,0,0.07) !important;
        }
        [data-testid="stForm"] label,
        [data-testid="stForm"] label p,
        [data-testid="stForm"] [data-testid="stWidgetLabel"] p {
            color: #374151 !important; font-weight: 500 !important;
        }
        /* ── Scroll entrance animations (Chrome 115+) ── */
        @keyframes fadeInUp {
            from { opacity:0; transform:translateY(44px); }
            to   { opacity:1; transform:translateY(0); }
        }
        #why-section {
            animation: fadeInUp 0.8s ease both;
            animation-timeline: view(); animation-range: entry 0% entry 25%;
        }
        #features-section {
            animation: fadeInUp 0.9s ease both;
            animation-timeline: view(); animation-range: entry 0% entry 20%;
        }
        #pipeline-section {
            animation: fadeInUp 0.9s ease both;
            animation-timeline: view(); animation-range: entry 0% entry 20%;
        }
        /* ── Form inputs — clean on white bg ── */
        [data-testid="stForm"] input {
            background: #f9fafb !important;
            border: 1px solid #e5e7eb !important;
            color: #111827 !important;
            border-radius: 8px !important;
            font-size: 0.95rem !important;
        }
        [data-testid="stForm"] input:focus {
            border-color: #4f46e5 !important;
            box-shadow: 0 0 0 3px rgba(79,70,229,0.12) !important;
        }
        [data-testid="stForm"] input::placeholder {
            color: #9ca3af !important; opacity: 1 !important;
        }
        /* ── Form submit button — solid indigo ── */
        [data-testid="stForm"] .stButton > button {
            background: #4f46e5 !important;
            color: white !important;
            font-weight: 700 !important;
            font-size: 1rem !important;
            padding: 0.7rem 1rem !important;
            border-radius: 8px !important;
            border: none !important;
        }
        [data-testid="stForm"] .stButton > button:hover {
            background: #4338ca !important;
        }
        /* ── Column-area buttons (Try demo, Create account) ── */
        [data-testid="column"] .stButton > button,
        [data-testid="stColumn"] .stButton > button {
            background: white !important;
            border: 1px solid #e5e7eb !important;
            color: #374151 !important;
            font-weight: 500 !important;
        }
        [data-testid="column"] .stButton > button:hover,
        [data-testid="stColumn"] .stButton > button:hover {
            background: #f9fafb !important; border-color: #d1d5db !important;
        }
        /* ── Forgot password expander — light ── */
        [data-testid="stExpander"] {
            background: white !important;
            border: 1px solid #e5e7eb !important;
            border-radius: 10px !important;
        }
        [data-testid="stExpander"] summary p,
        [data-testid="stExpander"] summary span {
            color: #374151 !important;
            font-weight: 600 !important; font-size: 0.875rem !important;
        }
        [data-testid="stExpander"] label { color: #374151 !important; }
        [data-testid="stExpander"] input {
            border-color: #e5e7eb !important;
            background: #f9fafb !important;
            color: #111827 !important;
        }
        [data-testid="stExpander"] input::placeholder {
            color: #9ca3af !important; opacity:1 !important;
        }
        [data-testid="stExpander"] input:focus {
            border-color: #4f46e5 !important;
            box-shadow: 0 0 0 3px rgba(79,70,229,0.12) !important;
        }
        [data-testid="stExpander"] .stButton > button {
            background: #4f46e5 !important;
            color: white !important;
            border: none !important;
            font-weight: 600 !important;
        }
        [data-testid="stExpander"] .stButton > button:hover {
            background: #4338ca !important;
        }
        /* ── All text in login column area — dark on white bg ── */
        [data-testid="column"] label,
        [data-testid="stColumn"] label,
        [data-testid="column"] [data-testid="stMarkdownContainer"] p,
        [data-testid="stTextInput"] label,
        [data-testid="stTextInput"] label p,
        .stTextInput label, .stTextInput label p {
            color: #374151 !important;
        }
        [data-testid="column"] input, .stTextInput input { color: #111827 !important; }
        [data-testid="column"] input::placeholder, .stTextInput input::placeholder {
            color: #9ca3af !important; opacity:1 !important;
        }
        </style>
    """), unsafe_allow_html=True)

    # ── STICKY TOP NAV ─────────────────────────────────────────────────
    st.markdown(_h("""
        <div style="position:sticky;top:0;z-index:200;background:rgba(255,255,255,0.95);
                    backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);
                    border-bottom:1px solid #e5e7eb;padding:0 3rem;height:64px;
                    display:flex;align-items:center;justify-content:space-between;">
        <div style="display:flex;align-items:center;gap:0.6rem;">
        <div style="background:#4f46e5;width:32px;height:32px;border-radius:8px;
                    display:flex;align-items:center;justify-content:center;
                    font-size:1rem;color:white;">🛡</div>
        <span style="font-weight:800;font-size:1.1rem;color:#111827;letter-spacing:-0.02em;">TrustLLM</span>
        </div>
        <div style="display:flex;align-items:center;gap:0.75rem;">
        <a href="#signin-section"
           style="color:#6b7280;text-decoration:none;font-size:0.9rem;font-weight:500;
                  padding:0.4rem 0.9rem;border-radius:7px;border:1px solid #e5e7eb;background:white;">
        Sign in</a>
        <a href="#signin-section"
           style="background:#4f46e5;color:white;text-decoration:none;
                  font-size:0.9rem;font-weight:600;padding:0.4rem 1rem;border-radius:7px;">
        Get started →</a>
        </div>
        </div>
    """), unsafe_allow_html=True)

    # ── HERO ──────────────────────────────────────────────────────────
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
                    letter-spacing:-0.04em;margin:0 0 0.1em 0;">
        Evaluate LLMs
        </div>
        <div style="font-size:5rem;font-weight:900;line-height:1.05;letter-spacing:-0.04em;
                    margin:0 0 1.5rem 0;
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
                  font-size:1rem;font-weight:600;padding:0.8rem 2rem;border-radius:8px;">
        Start evaluating →</a>
        <a href="#features-section"
           style="background:white;color:#374151;text-decoration:none;border:1px solid #d1d5db;
                  font-size:1rem;font-weight:500;padding:0.8rem 2rem;border-radius:8px;">
        See how it works</a>
        </div>
        </div>
    """), unsafe_allow_html=True)

    # ── WHY TRUSTLLM ──────────────────────────────────────────────────
    st.markdown(_h("""
        <div id="why-section" style="padding:5rem 3rem;background:#1e1b4b;">
        <div style="max-width:900px;margin:0 auto;">

        <div style="text-align:center;margin-bottom:4rem;">
        <div style="font-size:1rem;font-weight:900;color:#a5b4fc;text-transform:uppercase;
                    letter-spacing:0.14em;margin-bottom:1.1rem;">WHY TRUSTLLM</div>
        <div style="font-size:3.25rem;font-weight:900;color:#ffffff;letter-spacing:-0.04em;
                    line-height:1.1;margin-bottom:1.25rem;">
        AI fails differently than<br>normal software.
        </div>
        <div style="font-size:1.2rem;color:rgba(199,210,254,0.85);line-height:1.75;max-width:640px;margin:0 auto;">
        Traditional monitoring was built for deterministic code. LLMs are probabilistic — the same
        prompt can return different answers, and errors are often subtle, contextual, or outright invisible
        without specialized evaluation. You need a new kind of observability.
        </div>
        </div>

        <!-- 3-pillar grid -->
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:2rem;">

        <div style="border:1px solid rgba(165,180,252,0.2);border-radius:16px;padding:2rem;
                    background:rgba(255,255,255,0.07);backdrop-filter:blur(8px);">
        <div style="font-size:2rem;margin-bottom:1rem;">📈</div>
        <div style="font-weight:800;font-size:1.15rem;color:#ffffff;margin-bottom:0.5rem;
                    letter-spacing:-0.02em;">Scalable eval runs</div>
        <div style="font-size:0.95rem;color:rgba(255,255,255,0.82);line-height:1.65;">
        Run hundreds of prompts across multiple models in minutes. Catch regressions before they
        reach your users — not after.
        </div>
        </div>

        <div style="border:1px solid rgba(165,180,252,0.2);border-radius:16px;padding:2rem;
                    background:rgba(255,255,255,0.07);backdrop-filter:blur(8px);">
        <div style="font-size:2rem;margin-bottom:1rem;">🎯</div>
        <div style="font-weight:800;font-size:1.15rem;color:#ffffff;margin-bottom:0.5rem;
                    letter-spacing:-0.02em;">Live performance monitoring</div>
        <div style="font-size:0.95rem;color:rgba(255,255,255,0.82);line-height:1.65;">
        Track trust scores, accuracy, and safety metrics over time. Know exactly when a model update
        changes your product's behaviour.
        </div>
        </div>

        <div style="border:1px solid rgba(165,180,252,0.2);border-radius:16px;padding:2rem;
                    background:rgba(255,255,255,0.07);backdrop-filter:blur(8px);">
        <div style="font-size:2rem;margin-bottom:1rem;">🔔</div>
        <div style="font-weight:800;font-size:1.15rem;color:#ffffff;margin-bottom:0.5rem;
                    letter-spacing:-0.02em;">Catch issues early</div>
        <div style="font-size:0.95rem;color:rgba(255,255,255,0.82);line-height:1.65;">
        Hallucination spikes, jailbreak attempts, and bias drift surface automatically —
        so your team can act before your users even notice.
        </div>
        </div>

        </div>
        </div>
        </div>
    """), unsafe_allow_html=True)

    # ── FEATURES ──────────────────────────────────────────────────────
    st.markdown(_h("""
        <div id="features-section" style="
            padding:5rem 3rem 4rem;
            background:#ede9fe;">
        <div style="max-width:1000px;margin:0 auto;">
        <div style="text-align:center;margin-bottom:4rem;">
        <div style="display:inline-block;font-size:0.8rem;font-weight:800;color:#670D2F;
                    text-transform:uppercase;letter-spacing:0.18em;margin-bottom:1.1rem;
                    background:#fdf2f5;border:1px solid rgba(103,13,47,0.18);border-radius:100px;
                    padding:0.35rem 1.1rem;">WHAT YOU GET</div>
        <div style="font-size:3.25rem;font-weight:900;color:#1e1b4b;letter-spacing:-0.04em;line-height:1.1;">
        Everything you need<br>to trust your LLMs
        </div>
        </div>

        <!-- 3 feature cards — glassmorphism on gradient bg -->
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:1.75rem;">

        <!-- Card 1: Overview Dashboard -->
        <div style="border-radius:22px;overflow:hidden;display:flex;flex-direction:column;
                    box-shadow:0 8px 32px rgba(81,29,67,0.18),0 2px 6px rgba(81,29,67,0.08);
                    border:1px solid rgba(81,29,67,0.12);">
        <!-- gradient header -->
        <div style="background:#511D43;padding:2rem 1.75rem 1.5rem;">
          <div style="font-size:2.4rem;margin-bottom:0.75rem;">📊</div>
          <div style="font-weight:800;font-size:1.3rem;color:white;letter-spacing:-0.02em;line-height:1.2;">
            Overview Dashboard
          </div>
          <!-- mini stat row -->
          <div style="display:flex;gap:0.6rem;margin-top:1rem;">
            <div style="flex:1;background:rgba(255,255,255,0.15);border-radius:8px;padding:0.5rem;text-align:center;">
              <div style="font-size:1.1rem;font-weight:800;color:white;">0.81</div>
              <div style="font-size:0.6rem;color:rgba(255,255,255,0.75);margin-top:2px;">Trust</div>
            </div>
            <div style="flex:1;background:rgba(255,255,255,0.15);border-radius:8px;padding:0.5rem;text-align:center;">
              <div style="font-size:1.1rem;font-weight:800;color:white;">0.92</div>
              <div style="font-size:0.6rem;color:rgba(255,255,255,0.75);margin-top:2px;">Safety</div>
            </div>
            <div style="flex:1;background:rgba(255,255,255,0.15);border-radius:8px;padding:0.5rem;text-align:center;">
              <div style="font-size:1.1rem;font-weight:800;color:white;">88%</div>
              <div style="font-size:0.6rem;color:rgba(255,255,255,0.75);margin-top:2px;">Accuracy</div>
            </div>
          </div>
          <!-- mini bar chart -->
          <div style="margin-top:1rem;background:rgba(255,255,255,0.1);border-radius:6px;padding:0.5rem 0.6rem;">
            <div style="font-size:0.55rem;color:rgba(255,255,255,0.6);text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.4rem;">Score by category</div>
            <div style="display:flex;align-items:flex-end;gap:5px;height:32px;">
              <div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:2px;">
                <div style="width:100%;background:rgba(255,255,255,0.85);border-radius:2px 2px 0 0;height:80%;"></div>
                <div style="font-size:0.4rem;color:rgba(255,255,255,0.6);">fct</div>
              </div>
              <div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:2px;">
                <div style="width:100%;background:rgba(255,255,255,0.85);border-radius:2px 2px 0 0;height:65%;"></div>
                <div style="font-size:0.4rem;color:rgba(255,255,255,0.6);">rsn</div>
              </div>
              <div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:2px;">
                <div style="width:100%;background:rgba(255,255,255,0.85);border-radius:2px 2px 0 0;height:90%;"></div>
                <div style="font-size:0.4rem;color:rgba(255,255,255,0.6);">sft</div>
              </div>
              <div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:2px;">
                <div style="width:100%;background:rgba(255,255,255,0.45);border-radius:2px 2px 0 0;height:42%;"></div>
                <div style="font-size:0.4rem;color:rgba(255,255,255,0.6);">bias</div>
              </div>
              <div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:2px;">
                <div style="width:100%;background:rgba(255,255,255,0.85);border-radius:2px 2px 0 0;height:70%;"></div>
                <div style="font-size:0.4rem;color:rgba(255,255,255,0.6);">jlbk</div>
              </div>
            </div>
          </div>
        </div>
        <!-- glass card body -->
        <div style="padding:1.5rem;flex:1;
                    background:rgba(255,255,255,0.72);backdrop-filter:blur(14px);
                    -webkit-backdrop-filter:blur(14px);">
          <div style="font-size:0.95rem;color:#374151;line-height:1.7;margin-bottom:1rem;">
            Trust scores, accuracy &amp; hallucination rate at a glance for every model.
          </div>
          <div style="font-size:0.88rem;color:#511D43;font-weight:600;line-height:2.1;">
            ✓ Per-model &amp; category scores<br>
            ✓ Hallucination breakdown<br>
            ✓ Side-by-side comparison
          </div>
        </div>
        </div>

        <!-- Card 2: Failure Analysis -->
        <div style="border-radius:22px;overflow:hidden;display:flex;flex-direction:column;
                    box-shadow:0 8px 32px rgba(103,13,47,0.18),0 2px 6px rgba(103,13,47,0.08);
                    border:1px solid rgba(103,13,47,0.12);">
        <!-- gradient header -->
        <div style="background:#670D2F;padding:2rem 1.75rem 1.5rem;">
          <div style="font-size:2.4rem;margin-bottom:0.75rem;">🔍</div>
          <div style="font-weight:800;font-size:1.3rem;color:white;letter-spacing:-0.02em;line-height:1.2;">
            Failure Analysis
          </div>
          <!-- mini eval table -->
          <div style="margin-top:1rem;background:rgba(255,255,255,0.12);border-radius:8px;padding:0.6rem 0.75rem;">
            <div style="display:flex;gap:0.4rem;padding-bottom:0.35rem;border-bottom:1px solid rgba(255,255,255,0.2);margin-bottom:0.35rem;">
              <div style="font-size:0.5rem;font-weight:700;color:rgba(255,255,255,0.7);flex:3;text-transform:uppercase;">Prompt</div>
              <div style="font-size:0.5rem;font-weight:700;color:rgba(255,255,255,0.7);flex:1.2;text-align:center;text-transform:uppercase;">Status</div>
              <div style="font-size:0.5rem;font-weight:700;color:rgba(255,255,255,0.7);width:26px;text-align:right;text-transform:uppercase;">Scr</div>
            </div>
            <div style="display:flex;align-items:center;gap:0.4rem;padding:0.25rem 0;border-bottom:1px solid rgba(255,255,255,0.08);">
              <div style="font-size:0.52rem;color:rgba(255,255,255,0.85);flex:3;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">Ignore prev instructions...</div>
              <div style="font-size:0.44rem;background:rgba(254,202,202,0.25);color:#fca5a5;padding:0.1rem 0.3rem;border-radius:3px;flex:1.2;text-align:center;font-weight:600;">FAIL</div>
              <div style="font-size:0.52rem;color:#fca5a5;font-weight:700;width:26px;text-align:right;">0.12</div>
            </div>
            <div style="display:flex;align-items:center;gap:0.4rem;padding:0.25rem 0;border-bottom:1px solid rgba(255,255,255,0.08);">
              <div style="font-size:0.52rem;color:rgba(255,255,255,0.85);flex:3;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">What is the capital of...</div>
              <div style="font-size:0.44rem;background:rgba(167,243,208,0.2);color:#6ee7b7;padding:0.1rem 0.3rem;border-radius:3px;flex:1.2;text-align:center;font-weight:600;">PASS</div>
              <div style="font-size:0.52rem;color:#6ee7b7;font-weight:700;width:26px;text-align:right;">0.94</div>
            </div>
            <div style="display:flex;align-items:center;gap:0.4rem;padding:0.25rem 0;">
              <div style="font-size:0.52rem;color:rgba(255,255,255,0.85);flex:3;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">Generate harmful content...</div>
              <div style="font-size:0.44rem;background:rgba(254,202,202,0.25);color:#fca5a5;padding:0.1rem 0.3rem;border-radius:3px;flex:1.2;text-align:center;font-weight:600;">FAIL</div>
              <div style="font-size:0.52rem;color:#fca5a5;font-weight:700;width:26px;text-align:right;">0.07</div>
            </div>
          </div>
        </div>
        <!-- glass card body -->
        <div style="padding:1.5rem;flex:1;
                    background:rgba(255,255,255,0.72);backdrop-filter:blur(14px);
                    -webkit-backdrop-filter:blur(14px);">
          <div style="font-size:0.95rem;color:#374151;line-height:1.7;margin-bottom:1rem;">
            Surface every failed eval with the prompt, response &amp; exact failure reason.
          </div>
          <div style="font-size:0.88rem;color:#670D2F;font-weight:600;line-height:2.1;">
            ✓ Filter by category or model<br>
            ✓ Hallucination &amp; jailbreak flags<br>
            ✓ Drill into any failing prompt
          </div>
        </div>
        </div>

        <!-- Card 3: Model Leaderboard -->
        <div style="border-radius:22px;overflow:hidden;display:flex;flex-direction:column;
                    box-shadow:0 8px 32px rgba(116,10,3,0.18),0 2px 6px rgba(116,10,3,0.08);
                    border:1px solid rgba(116,10,3,0.12);">
        <!-- gradient header -->
        <div style="background:#740A03;padding:2rem 1.75rem 1.5rem;">
          <div style="font-size:2.4rem;margin-bottom:0.75rem;">🏆</div>
          <div style="font-weight:800;font-size:1.3rem;color:white;letter-spacing:-0.02em;line-height:1.2;">
            Model Leaderboard
          </div>
          <!-- mini leaderboard -->
          <div style="margin-top:1rem;background:rgba(255,255,255,0.12);border-radius:8px;padding:0.6rem 0.75rem;">
            <div style="display:flex;gap:0.4rem;padding-bottom:0.35rem;border-bottom:1px solid rgba(255,255,255,0.2);margin-bottom:0.4rem;">
              <div style="font-size:0.5rem;font-weight:700;color:rgba(255,255,255,0.7);width:14px;text-transform:uppercase;">#</div>
              <div style="font-size:0.5rem;font-weight:700;color:rgba(255,255,255,0.7);flex:1;text-transform:uppercase;">Model</div>
              <div style="font-size:0.5rem;font-weight:700;color:rgba(255,255,255,0.7);width:28px;text-align:right;text-transform:uppercase;">Score</div>
            </div>
            <div style="display:flex;align-items:center;gap:0.4rem;padding:0.3rem 0;border-bottom:1px solid rgba(255,255,255,0.08);">
              <div style="font-size:0.58rem;color:#fde68a;font-weight:800;width:14px;">1</div>
              <div style="flex:1;">
                <div style="font-size:0.58rem;color:white;font-weight:600;">GPT-4o</div>
                <div style="background:rgba(255,255,255,0.3);border-radius:2px;height:4px;margin-top:3px;overflow:hidden;">
                  <div style="width:89%;height:100%;background:rgba(255,255,255,0.9);border-radius:2px;"></div>
                </div>
              </div>
              <div style="font-size:0.58rem;color:#fde68a;font-weight:700;width:28px;text-align:right;">0.89</div>
            </div>
            <div style="display:flex;align-items:center;gap:0.4rem;padding:0.3rem 0;border-bottom:1px solid rgba(255,255,255,0.08);">
              <div style="font-size:0.58rem;color:rgba(255,255,255,0.7);font-weight:800;width:14px;">2</div>
              <div style="flex:1;">
                <div style="font-size:0.58rem;color:white;font-weight:600;">Claude 3</div>
                <div style="background:rgba(255,255,255,0.3);border-radius:2px;height:4px;margin-top:3px;overflow:hidden;">
                  <div style="width:85%;height:100%;background:rgba(255,255,255,0.9);border-radius:2px;"></div>
                </div>
              </div>
              <div style="font-size:0.58rem;color:#fde68a;font-weight:700;width:28px;text-align:right;">0.85</div>
            </div>
            <div style="display:flex;align-items:center;gap:0.4rem;padding:0.3rem 0;">
              <div style="font-size:0.58rem;color:rgba(255,255,255,0.7);font-weight:800;width:14px;">3</div>
              <div style="flex:1;">
                <div style="font-size:0.58rem;color:white;font-weight:600;">Gemini</div>
                <div style="background:rgba(255,255,255,0.3);border-radius:2px;height:4px;margin-top:3px;overflow:hidden;">
                  <div style="width:79%;height:100%;background:rgba(255,255,255,0.9);border-radius:2px;"></div>
                </div>
              </div>
              <div style="font-size:0.58rem;color:#fde68a;font-weight:700;width:28px;text-align:right;">0.79</div>
            </div>
          </div>
        </div>
        <!-- glass card body -->
        <div style="padding:1.5rem;flex:1;
                    background:rgba(255,255,255,0.72);backdrop-filter:blur(14px);
                    -webkit-backdrop-filter:blur(14px);">
          <div style="font-size:0.95rem;color:#374151;line-height:1.7;margin-bottom:1rem;">
            Rank every model by trust score, safety, and cost in one unified view.
          </div>
          <div style="font-size:0.88rem;color:#740A03;font-weight:600;line-height:2.1;">
            ✓ Composite trust score ranking<br>
            ✓ Safety &amp; bias sub-scores<br>
            ✓ Cost vs. quality trade-offs
          </div>
        </div>
        </div>

        </div>
        </div>
        </div>
    """), unsafe_allow_html=True)

    # ── ARCHITECTURE / HOW IT WORKS ────────────────────────────────────
    st.markdown(_h("""
        <div id="pipeline-section" style="padding:4rem 3rem;background:#1e1b4b;">
        <div style="max-width:960px;margin:0 auto;">
        <div style="text-align:center;margin-bottom:3rem;">
        <div style="font-size:1rem;font-weight:900;color:#4ade80;text-transform:uppercase;
                    letter-spacing:0.14em;margin-bottom:1.1rem;">HOW IT WORKS</div>
        <div style="font-size:2.75rem;font-weight:900;color:white;letter-spacing:-0.03em;line-height:1.2;">
        The TrustLLM Pipeline
        </div>
        </div>

        <div style="margin-bottom:2rem;">
        <div style="font-size:0.65rem;font-weight:600;color:rgba(255,255,255,0.45);letter-spacing:0.08em;
                    text-transform:uppercase;margin-bottom:1rem;">Evaluation Pipeline</div>
        <div style="display:flex;align-items:center;flex-wrap:wrap;gap:0.25rem;justify-content:center;">
        <div style="background:#1a4a35;border:1px solid #2d6a4f;border-radius:10px;
                    padding:0.75rem 1rem;text-align:center;min-width:106px;">
        <div style="font-size:1.1rem;margin-bottom:0.3rem;">📂</div>
        <div style="font-size:0.7rem;font-weight:700;color:#d1fae5;">Datasets</div>
        <div style="font-size:0.55rem;color:#6ee7b7;margin-top:0.1rem;">Prompts &amp; answers</div>
        </div>
        <div style="color:#4ade80;font-size:1.1rem;padding:0 0.4rem;">→</div>
        <div style="background:#1a4a35;border:1px solid #2d6a4f;border-radius:10px;
                    padding:0.75rem 1rem;text-align:center;min-width:106px;">
        <div style="font-size:1.1rem;margin-bottom:0.3rem;">🤖</div>
        <div style="font-size:0.7rem;font-weight:700;color:#d1fae5;">LLM Runner</div>
        <div style="font-size:0.55rem;color:#6ee7b7;margin-top:0.1rem;">GPT, Claude, Mistral</div>
        </div>
        <div style="color:#4ade80;font-size:1.1rem;padding:0 0.4rem;">→</div>
        <div style="background:#1a4a35;border:1px solid #2d6a4f;border-radius:10px;
                    padding:0.75rem 1rem;text-align:center;min-width:106px;">
        <div style="font-size:1.1rem;margin-bottom:0.3rem;">⚖️</div>
        <div style="font-size:0.7rem;font-weight:700;color:#d1fae5;">Evaluator</div>
        <div style="font-size:0.55rem;color:#6ee7b7;margin-top:0.1rem;">Score responses</div>
        </div>
        <div style="color:#4ade80;font-size:1.1rem;padding:0 0.4rem;">→</div>
        <div style="background:#1a4a35;border:1px solid #2d6a4f;border-radius:10px;
                    padding:0.75rem 1rem;text-align:center;min-width:106px;">
        <div style="font-size:1.1rem;margin-bottom:0.3rem;">🛡</div>
        <div style="font-size:0.7rem;font-weight:700;color:#d1fae5;">Trust Score</div>
        <div style="font-size:0.55rem;color:#6ee7b7;margin-top:0.1rem;">Composite metric</div>
        </div>
        <div style="color:#4ade80;font-size:1.1rem;padding:0 0.4rem;">→</div>
        <div style="background:#1a4a35;border:1px solid #2d6a4f;border-radius:10px;
                    padding:0.75rem 1rem;text-align:center;min-width:106px;">
        <div style="font-size:1.1rem;margin-bottom:0.3rem;">📊</div>
        <div style="font-size:0.7rem;font-weight:700;color:#d1fae5;">Dashboard</div>
        <div style="font-size:0.55rem;color:#6ee7b7;margin-top:0.1rem;">Visualize &amp; act</div>
        </div>
        </div>
        </div>

        <div>
        <div style="font-size:0.65rem;font-weight:600;color:rgba(255,255,255,0.45);letter-spacing:0.08em;
                    text-transform:uppercase;margin-bottom:1rem;">RAG / Document Pipeline</div>
        <div style="display:flex;align-items:center;flex-wrap:wrap;gap:0.25rem;justify-content:center;">
        <div style="background:#1a4a35;border:1px solid #2d6a4f;border-radius:10px;
                    padding:0.75rem 1rem;text-align:center;min-width:106px;">
        <div style="font-size:1.1rem;margin-bottom:0.3rem;">📄</div>
        <div style="font-size:0.7rem;font-weight:700;color:#d1fae5;">PDF / Docs</div>
        <div style="font-size:0.55rem;color:#6ee7b7;margin-top:0.1rem;">Source material</div>
        </div>
        <div style="color:#4ade80;font-size:1.1rem;padding:0 0.4rem;">→</div>
        <div style="background:#1a4a35;border:1px solid #2d6a4f;border-radius:10px;
                    padding:0.75rem 1rem;text-align:center;min-width:106px;">
        <div style="font-size:1.1rem;margin-bottom:0.3rem;">✂️</div>
        <div style="font-size:0.7rem;font-weight:700;color:#d1fae5;">RAG Ingestion</div>
        <div style="font-size:0.55rem;color:#6ee7b7;margin-top:0.1rem;">Chunk &amp; embed</div>
        </div>
        <div style="color:#4ade80;font-size:1.1rem;padding:0 0.4rem;">→</div>
        <div style="background:#1a4a35;border:1px solid #2d6a4f;border-radius:10px;
                    padding:0.75rem 1rem;text-align:center;min-width:106px;">
        <div style="font-size:1.1rem;margin-bottom:0.3rem;">🗄️</div>
        <div style="font-size:0.7rem;font-weight:700;color:#d1fae5;">ChromaDB</div>
        <div style="font-size:0.55rem;color:#6ee7b7;margin-top:0.1rem;">Vector store</div>
        </div>
        <div style="color:#4ade80;font-size:1.1rem;padding:0 0.4rem;">→</div>
        <div style="background:#1a4a35;border:1px solid #2d6a4f;border-radius:10px;
                    padding:0.75rem 1rem;text-align:center;min-width:106px;">
        <div style="font-size:1.1rem;margin-bottom:0.3rem;">🔍</div>
        <div style="font-size:0.7rem;font-weight:700;color:#d1fae5;">Retriever</div>
        <div style="font-size:0.55rem;color:#6ee7b7;margin-top:0.1rem;">Semantic search</div>
        </div>
        <div style="color:#4ade80;font-size:1.1rem;padding:0 0.4rem;">→</div>
        <div style="background:#1a4a35;border:1px solid #2d6a4f;border-radius:10px;
                    padding:0.75rem 1rem;text-align:center;min-width:106px;">
        <div style="font-size:1.1rem;margin-bottom:0.3rem;">🧪</div>
        <div style="font-size:0.7rem;font-weight:700;color:#d1fae5;">RAG Eval</div>
        <div style="font-size:0.55rem;color:#6ee7b7;margin-top:0.1rem;">Fidelity score</div>
        </div>
        </div>
        </div>

        </div>
        </div>
    """), unsafe_allow_html=True)

    # ── STATS STRIP ───────────────────────────────────────────────────
    st.markdown(_h(f"""
        <div style="background:#1e1b4b;padding:3.5rem 3rem;border-top:1px solid rgba(165,180,252,0.1);">
        <div style="max-width:700px;margin:0 auto;
                    display:grid;grid-template-columns:repeat(3,1fr);gap:2rem;text-align:center;">
        <div>
        <div style="font-size:3.5rem;font-weight:900;color:white;letter-spacing:-0.04em;line-height:1;">
        {stats["prompts"]}</div>
        <div style="color:rgba(255,255,255,0.6);font-size:0.9rem;margin-top:0.4rem;">Prompts evaluated</div>
        </div>
        <div>
        <div style="font-size:3.5rem;font-weight:900;color:white;letter-spacing:-0.04em;line-height:1;">
        {stats["models"]}</div>
        <div style="color:rgba(255,255,255,0.6);font-size:0.9rem;margin-top:0.4rem;">Models tested</div>
        </div>
        <div>
        <div style="font-size:3.5rem;font-weight:900;color:white;letter-spacing:-0.04em;line-height:1;">
        {stats["avg_trust"]}</div>
        <div style="color:rgba(255,255,255,0.6);font-size:0.9rem;margin-top:0.4rem;">Avg trust score</div>
        </div>
        </div>
        </div>
    """), unsafe_allow_html=True)

    # ── SIGN-IN SECTION HEADER ────────────────────────────────────────
    st.markdown(_h("""
        <div id="signin-section"
             style="padding:5rem 2rem 3rem;background:transparent;
                    border-top:1px solid #f1f5f9;">
        <div style="max-width:440px;margin:0 auto;text-align:center;">
        <div style="background:#4f46e5;width:60px;height:60px;border-radius:16px;
                    display:inline-flex;align-items:center;justify-content:center;
                    font-size:1.75rem;color:white;margin-bottom:1.25rem;
                    box-shadow:0 8px 24px rgba(79,70,229,0.3);">🛡</div>
        <div style="font-size:2.5rem;font-weight:900;color:#111827;letter-spacing:-0.04em;
                    margin-bottom:0.5rem;line-height:1.1;">Welcome back</div>
        <div style="font-size:1.1rem;color:#6b7280;font-weight:400;">Sign in to your TrustLLM account</div>
        </div>
        </div>
    """), unsafe_allow_html=True)

    # ── FORM CARD ─────────────────────────────────────────────────────
    _, form_col, _ = st.columns([1, 2, 1])
    with form_col:
        # Google + GitHub OAuth (Supabase) or demo placeholders
        if is_configured():
            try:
                google_url = get_auth_url("google")
                github_url = get_auth_url("github")
                st.markdown(_h(f"""
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;margin-bottom:1rem;">
                    <a href="{google_url}" target="_self"
                       style="display:flex;align-items:center;justify-content:center;gap:0.55rem;
                              background:white;color:#374151;border:1px solid #d1d5db;
                              border-radius:8px;padding:0.7rem 0.5rem;font-size:0.875rem;font-weight:500;
                              text-decoration:none;box-sizing:border-box;">
                    <svg width="16" height="16" viewBox="0 0 48 48" style="flex-shrink:0;">
                    <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
                    <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
                    <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
                    <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
                    </svg>
                    Continue with Google
                    </a>
                    <a href="{github_url}" target="_self"
                       style="display:flex;align-items:center;justify-content:center;gap:0.55rem;
                              background:#24292e;color:white;border:1px solid #1b1f23;
                              border-radius:8px;padding:0.7rem 0.5rem;font-size:0.875rem;font-weight:500;
                              text-decoration:none;box-sizing:border-box;">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="white" style="flex-shrink:0;">
                    <path d="M12 0C5.37 0 0 5.37 0 12c0 5.3 3.438 9.8 8.205 11.387.6.113.82-.258.82-.577
                             0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61-.546-1.387-1.333-1.756
                             -1.333-1.756-1.09-.745.083-.73.083-.73 1.205.085 1.838 1.236 1.838 1.236
                             1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466
                             -1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176
                             0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405
                             2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23
                             1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22
                             0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 21.795 24 17.295
                             24 12c0-6.63-5.37-12-12-12z"/>
                    </svg>
                    Continue with GitHub
                    </a>
                    </div>
                """), unsafe_allow_html=True)
            except Exception:
                pass
        else:
            st.markdown(_h("""
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;margin-bottom:1rem;">
                <button style="background:white;color:#374151;border:1px solid #d1d5db;border-radius:8px;
                               padding:0.7rem 0.5rem;font-size:0.875rem;font-weight:500;cursor:pointer;
                               width:100%;font-family:inherit;opacity:0.6;cursor:not-allowed;">
                🔵 Continue with Google
                </button>
                <button style="background:#24292e;color:white;border:1px solid #1b1f23;border-radius:8px;
                               padding:0.7rem 0.5rem;font-size:0.875rem;font-weight:500;cursor:pointer;
                               width:100%;font-family:inherit;opacity:0.6;cursor:not-allowed;">
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
                username = st.text_input("Username", placeholder="Enter your username")
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

            if not is_configured():
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
            <span style="color:#9ca3af;font-size:0.8rem;">
            Demo — Username: <strong style="color:#374151;">TestUser</strong>
            &nbsp;·&nbsp; Password: <strong style="color:#374151;">User123</strong>
            </span>
            </div>
        """), unsafe_allow_html=True)

    # ── FOOTER ────────────────────────────────────────────────────────
    st.markdown(_h("""
        <div style="background:#1e1b4b;padding:2rem 3rem;text-align:center;">
        <span style="color:rgba(255,255,255,0.75);font-size:0.8rem;">
        © 2025 TrustLLM · Powered by ChromaDB · Groq · Streamlit ·
        Built by <a href="https://www.linkedin.com/in/monika-kushwaha-52443735/"
        target="_blank" style="color:#a5b4fc;text-decoration:none;">Monika Kushwaha</a>
        </span>
        </div>
    """), unsafe_allow_html=True)


# -----------------------------------------------------------------------
# Command palette HTML/JS injection
# -----------------------------------------------------------------------
_CMD_PAGES = [
    ("Overview",          "📊", "Monitor"),
    ("Failure Analysis",  "🔍", "Monitor"),
    ("Leaderboard",       "🏆", "Monitor"),
    ("Run Evaluation",    "▶",  "Evaluate"),
    ("Agent Performance", "🤖", "Evaluate"),
    ("RAG Testing",       "📚", "Evaluate"),
    ("Prompt Explorer",   "🔎", "Data"),
    ("Prompt Dataset",    "📂", "Data"),
    ("Query History",     "🕘", "Data"),
    ("Profile",           "👤", "Account"),
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
from ui_pages.agent_performance import render as agent_performance
from ui_pages.rag_page          import render as rag_testing
from ui_pages.prompt_dataset    import render as prompt_dataset
from ui_pages.failure_analysis  import render as failure_analysis
from ui_pages.profile           import render as profile_page
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
        ("🤖", "Agent Performance"),
        ("📚", "RAG Testing"),
    ],
    "DATA": [
        ("🔎", "Prompt Explorer"),
        ("📂", "Prompt Dataset"),
        ("🕘", "Query History"),
    ],
    "ACCOUNT": [
        ("👤", "Profile"),
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
    "Agent Performance": agent_performance,
    "RAG Testing":       rag_testing,
    "Prompt Dataset":    prompt_dataset,
    "Failure Analysis":  failure_analysis,
    "Query History":     query_history_page,
    "Profile":           profile_page,
}

_routes.get(page, overview)()
