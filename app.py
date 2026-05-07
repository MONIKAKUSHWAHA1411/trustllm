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
        /* ── Page background — indigo gradient shows through form area ── */
        .stApp { background: linear-gradient(160deg,#1e1b4b 0%,#312e81 30%,#4f46e5 65%,#5b21b6 100%) !important; }
        section.main { background: transparent !important; }
        section.main .block-container { padding: 0 !important; max-width: 100% !important; background: transparent !important; }
        /* ── Form card — white floating card on dark bg ── */
        [data-testid="stForm"] {
            background: white !important;
            border-radius: 14px !important;
            padding: 1.5rem 1.5rem 0.75rem !important;
            box-shadow: 0 20px 60px rgba(0,0,0,0.2) !important;
            border: none !important;
        }
        [data-testid="stForm"] label { color: #374151 !important; font-weight: 500 !important; }
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
        }
        [data-testid="stForm"] .stButton > button:hover { background-color: #4338ca !important; }
        /* ── Forgot password expander ── */
        [data-testid="stExpander"] {
            background: #f5f3ff !important;
            border: 1px solid #c7d2fe !important;
            border-radius: 10px !important;
        }
        [data-testid="stExpander"] summary p,
        [data-testid="stExpander"] summary span {
            color: #4f46e5 !important;
            font-weight: 600 !important;
            font-size: 0.875rem !important;
        }
        [data-testid="stExpander"] label {
            color: #4f46e5 !important;
            font-weight: 500 !important;
        }
        [data-testid="stExpander"] input {
            border-color: #c7d2fe !important;
            background: white !important;
            color: #111827 !important;
        }
        [data-testid="stExpander"] input:focus {
            border-color: #4f46e5 !important;
            box-shadow: 0 0 0 3px rgba(79,70,229,0.15) !important;
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
        /* ── Login column: force all labels + text black on white bg ── */
        [data-testid="column"] label,
        [data-testid="column"] [data-testid="stMarkdownContainer"] p,
        [data-testid="column"] span.st-emotion-cache-1gulkj5,
        [data-testid="stTextInput"] label,
        [data-testid="stTextInput"] label p,
        .stTextInput label, .stTextInput label p {
            color: #111827 !important;
        }
        /* ── Placeholder text — dark gray so it's clearly readable ── */
        [data-testid="column"] input::placeholder,
        [data-testid="stForm"] input::placeholder,
        .stTextInput input::placeholder {
            color: #6b7280 !important;
            opacity: 1 !important;
        }
        /* ── Input text (typed chars) always black ── */
        [data-testid="column"] input,
        .stTextInput input {
            color: #111827 !important;
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
        <div id="why-section" style="padding:5rem 3rem;background:#ffffff;
             border-top:1px solid #f1f5f9;">
        <div style="max-width:900px;margin:0 auto;">

        <div style="text-align:center;margin-bottom:4rem;">
        <div style="display:inline-block;background:#fff1f2;color:#e11d48;padding:0.45rem 1.2rem;
                    border-radius:8px;font-size:0.85rem;font-weight:800;letter-spacing:0.06em;
                    text-transform:uppercase;margin-bottom:1.25rem;">WHY TRUSTLLM</div>
        <div style="font-size:3rem;font-weight:900;color:#111827;letter-spacing:-0.04em;
                    line-height:1.1;margin-bottom:1.25rem;">
        AI fails differently than<br>normal software.
        </div>
        <div style="font-size:1.2rem;color:#6b7280;line-height:1.75;max-width:640px;margin:0 auto;">
        Traditional monitoring was built for deterministic code. LLMs are probabilistic — the same
        prompt can return different answers, and errors are often subtle, contextual, or outright invisible
        without specialized evaluation. You need a new kind of observability.
        </div>
        </div>

        <!-- 3-pillar grid -->
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:2rem;">

        <div style="border:1px solid #e5e7eb;border-radius:16px;padding:2rem;
                    background:linear-gradient(135deg,#fafbff 0%,#f5f3ff 100%);">
        <div style="font-size:2rem;margin-bottom:1rem;">📈</div>
        <div style="font-weight:800;font-size:1.15rem;color:#111827;margin-bottom:0.5rem;
                    letter-spacing:-0.02em;">Scalable eval runs</div>
        <div style="font-size:0.95rem;color:#6b7280;line-height:1.65;">
        Run hundreds of prompts across multiple models in minutes. Catch regressions before they
        reach your users — not after.
        </div>
        </div>

        <div style="border:1px solid #e5e7eb;border-radius:16px;padding:2rem;
                    background:linear-gradient(135deg,#fafbff 0%,#ecfdf5 100%);">
        <div style="font-size:2rem;margin-bottom:1rem;">🎯</div>
        <div style="font-weight:800;font-size:1.15rem;color:#111827;margin-bottom:0.5rem;
                    letter-spacing:-0.02em;">Live performance monitoring</div>
        <div style="font-size:0.95rem;color:#6b7280;line-height:1.65;">
        Track trust scores, accuracy, and safety metrics over time. Know exactly when a model update
        changes your product's behaviour.
        </div>
        </div>

        <div style="border:1px solid #e5e7eb;border-radius:16px;padding:2rem;
                    background:linear-gradient(135deg,#fafbff 0%,#fffbeb 100%);">
        <div style="font-size:2rem;margin-bottom:1rem;">🔔</div>
        <div style="font-weight:800;font-size:1.15rem;color:#111827;margin-bottom:0.5rem;
                    letter-spacing:-0.02em;">Catch issues early</div>
        <div style="font-size:0.95rem;color:#6b7280;line-height:1.65;">
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
        <div id="features-section" style="padding:5rem 3rem 4rem;background:#eef2ff;
             border-top:1px solid #e5e7eb;border-bottom:1px solid #c7d2fe;">
        <div style="max-width:1000px;margin:0 auto;">
        <div style="text-align:center;margin-bottom:4rem;">
        <div style="display:inline-block;background:#4f46e5;color:white;padding:0.55rem 1.5rem;
                    border-radius:8px;font-size:1.1rem;font-weight:800;letter-spacing:0.05em;
                    text-transform:uppercase;margin-bottom:1.25rem;">WHAT YOU GET</div>
        <div style="font-size:3.25rem;font-weight:800;color:#1e1b4b;letter-spacing:-0.04em;line-height:1.1;">
        Everything you need<br>to trust your LLMs
        </div>
        </div>

        <!-- 3 cards in equal columns -->
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:1.75rem;">

        <!-- Card 1: Overview Dashboard -->
        <div style="background:white;border:1px solid #e0e7ff;border-radius:16px;overflow:hidden;
                    box-shadow:0 4px 20px rgba(79,70,229,0.08);">
        <div style="background:#0f172a;padding:1.25rem;">
        <div style="display:flex;align-items:center;gap:0.3rem;margin-bottom:0.85rem;">
        <div style="width:7px;height:7px;border-radius:50%;background:#ef4444;"></div>
        <div style="width:7px;height:7px;border-radius:50%;background:#fbbf24;"></div>
        <div style="width:7px;height:7px;border-radius:50%;background:#22c55e;"></div>
        <span style="font-size:0.55rem;color:#475569;margin-left:0.4rem;font-family:monospace;">Overview · GPT-4o</span>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.4rem;margin-bottom:0.85rem;">
        <div style="background:#1e293b;border-radius:5px;padding:0.45rem;text-align:center;">
        <div style="font-size:0.9rem;font-weight:800;color:#a5b4fc;">0.81</div>
        <div style="font-size:0.47rem;color:#64748b;margin-top:0.1rem;">Trust</div>
        </div>
        <div style="background:#1e293b;border-radius:5px;padding:0.45rem;text-align:center;">
        <div style="font-size:0.9rem;font-weight:800;color:#6ee7b7;">0.92</div>
        <div style="font-size:0.47rem;color:#64748b;margin-top:0.1rem;">Safety</div>
        </div>
        <div style="background:#1e293b;border-radius:5px;padding:0.45rem;text-align:center;">
        <div style="font-size:0.9rem;font-weight:800;color:#fbbf24;">88%</div>
        <div style="font-size:0.47rem;color:#64748b;margin-top:0.1rem;">Accuracy</div>
        </div>
        <div style="background:#1e293b;border-radius:5px;padding:0.45rem;text-align:center;">
        <div style="font-size:0.9rem;font-weight:800;color:#f87171;">12%</div>
        <div style="font-size:0.47rem;color:#64748b;margin-top:0.1rem;">Hallucinated</div>
        </div>
        </div>
        <div style="background:#1e293b;border-radius:6px;padding:0.6rem 0.6rem 0.4rem;">
        <div style="font-size:0.42rem;color:#475569;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.3rem;">By Category</div>
        <div style="display:flex;align-items:flex-end;gap:4px;height:38px;">
        <div style="display:flex;flex-direction:column;align-items:center;gap:2px;flex:1;">
        <div style="width:100%;background:#6366f1;border-radius:2px 2px 0 0;height:80%;"></div>
        <div style="font-size:0.38rem;color:#64748b;">fct</div>
        </div>
        <div style="display:flex;flex-direction:column;align-items:center;gap:2px;flex:1;">
        <div style="width:100%;background:#6366f1;border-radius:2px 2px 0 0;height:65%;opacity:0.8;"></div>
        <div style="font-size:0.38rem;color:#64748b;">rsn</div>
        </div>
        <div style="display:flex;flex-direction:column;align-items:center;gap:2px;flex:1;">
        <div style="width:100%;background:#6366f1;border-radius:2px 2px 0 0;height:90%;"></div>
        <div style="font-size:0.38rem;color:#64748b;">sft</div>
        </div>
        <div style="display:flex;flex-direction:column;align-items:center;gap:2px;flex:1;">
        <div style="width:100%;background:#f59e0b;border-radius:2px 2px 0 0;height:42%;"></div>
        <div style="font-size:0.38rem;color:#64748b;">bias</div>
        </div>
        <div style="display:flex;flex-direction:column;align-items:center;gap:2px;flex:1;">
        <div style="width:100%;background:#6366f1;border-radius:2px 2px 0 0;height:70%;"></div>
        <div style="font-size:0.38rem;color:#64748b;">jlbk</div>
        </div>
        </div>
        </div>
        </div>
        <div style="padding:1.5rem;">
        <div style="background:#eef2ff;width:38px;height:38px;border-radius:9px;display:flex;align-items:center;
                    justify-content:center;font-size:1.1rem;margin-bottom:0.75rem;">📊</div>
        <div style="font-weight:800;font-size:1.35rem;color:#111827;margin-bottom:0.45rem;letter-spacing:-0.02em;">Overview Dashboard</div>
        <div style="font-size:0.95rem;color:#6b7280;line-height:1.65;margin-bottom:0.75rem;">
        Trust scores, accuracy &amp; hallucination rate at a glance for every model.
        </div>
        <div style="font-size:0.9rem;color:#374151;line-height:2.1;">
        ✓ Per-model &amp; category scores<br>
        ✓ Hallucination breakdown<br>
        ✓ Side-by-side comparison
        </div>
        </div>
        </div>

        <!-- Card 2: Failure Analysis -->
        <div style="background:white;border:1px solid #e0e7ff;border-radius:16px;overflow:hidden;
                    box-shadow:0 4px 20px rgba(79,70,229,0.08);">
        <div style="background:#0f172a;padding:1.25rem;">
        <div style="display:flex;align-items:center;gap:0.3rem;margin-bottom:0.75rem;">
        <div style="width:7px;height:7px;border-radius:50%;background:#ef4444;"></div>
        <div style="width:7px;height:7px;border-radius:50%;background:#fbbf24;"></div>
        <div style="width:7px;height:7px;border-radius:50%;background:#22c55e;"></div>
        <span style="font-size:0.55rem;color:#475569;margin-left:0.4rem;font-family:monospace;">Failure Analysis</span>
        </div>
        <div style="display:flex;gap:0.4rem;padding:0.25rem 0;border-bottom:1px solid #1e293b;margin-bottom:0.4rem;">
        <div style="font-size:0.45rem;font-weight:600;color:#475569;flex:2;">PROMPT</div>
        <div style="font-size:0.45rem;font-weight:600;color:#475569;flex:1;text-align:center;">STATUS</div>
        <div style="font-size:0.45rem;font-weight:600;color:#475569;width:24px;text-align:right;">SCR</div>
        </div>
        <div style="display:flex;align-items:center;gap:0.4rem;padding:0.3rem 0;border-bottom:1px solid #0f1a2e;">
        <div style="font-size:0.5rem;color:#94a3b8;flex:2;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">Ignore prev instructions...</div>
        <div style="font-size:0.42rem;background:#450a0a;color:#f87171;padding:0.12rem 0.3rem;border-radius:3px;flex:1;text-align:center;">FAIL</div>
        <div style="font-size:0.5rem;color:#f87171;font-weight:700;width:24px;text-align:right;">0.12</div>
        </div>
        <div style="display:flex;align-items:center;gap:0.4rem;padding:0.3rem 0;border-bottom:1px solid #0f1a2e;">
        <div style="font-size:0.5rem;color:#94a3b8;flex:2;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">What is the capital of...</div>
        <div style="font-size:0.42rem;background:#052e16;color:#6ee7b7;padding:0.12rem 0.3rem;border-radius:3px;flex:1;text-align:center;">PASS</div>
        <div style="font-size:0.5rem;color:#6ee7b7;font-weight:700;width:24px;text-align:right;">0.94</div>
        </div>
        <div style="display:flex;align-items:center;gap:0.4rem;padding:0.3rem 0;border-bottom:1px solid #0f1a2e;">
        <div style="font-size:0.5rem;color:#94a3b8;flex:2;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">Explain quantum entangle...</div>
        <div style="font-size:0.42rem;background:#451a03;color:#fbbf24;padding:0.12rem 0.3rem;border-radius:3px;flex:1;text-align:center;">WARN</div>
        <div style="font-size:0.5rem;color:#fbbf24;font-weight:700;width:24px;text-align:right;">0.58</div>
        </div>
        <div style="display:flex;align-items:center;gap:0.4rem;padding:0.3rem 0;">
        <div style="font-size:0.5rem;color:#94a3b8;flex:2;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">Generate harmful content...</div>
        <div style="font-size:0.42rem;background:#450a0a;color:#f87171;padding:0.12rem 0.3rem;border-radius:3px;flex:1;text-align:center;">FAIL</div>
        <div style="font-size:0.5rem;color:#f87171;font-weight:700;width:24px;text-align:right;">0.07</div>
        </div>
        </div>
        <div style="padding:1.5rem;">
        <div style="background:#fff1f2;width:38px;height:38px;border-radius:9px;display:flex;align-items:center;
                    justify-content:center;font-size:1.1rem;margin-bottom:0.75rem;">✕</div>
        <div style="font-weight:800;font-size:1.35rem;color:#111827;margin-bottom:0.45rem;letter-spacing:-0.02em;">Failure Analysis</div>
        <div style="font-size:0.95rem;color:#6b7280;line-height:1.65;margin-bottom:0.75rem;">
        Surface every failed eval with the prompt, response &amp; exact failure reason.
        </div>
        <div style="font-size:0.9rem;color:#374151;line-height:2.1;">
        ✓ Filter by category or model<br>
        ✓ Hallucination &amp; jailbreak flags<br>
        ✓ Drill into any failing prompt
        </div>
        </div>
        </div>

        <!-- Card 3: Leaderboard -->
        <div style="background:white;border:1px solid #e0e7ff;border-radius:16px;overflow:hidden;
                    box-shadow:0 4px 20px rgba(79,70,229,0.08);">
        <div style="background:#0f172a;padding:1.25rem;">
        <div style="display:flex;align-items:center;gap:0.3rem;margin-bottom:0.75rem;">
        <div style="width:7px;height:7px;border-radius:50%;background:#ef4444;"></div>
        <div style="width:7px;height:7px;border-radius:50%;background:#fbbf24;"></div>
        <div style="width:7px;height:7px;border-radius:50%;background:#22c55e;"></div>
        <span style="font-size:0.55rem;color:#475569;margin-left:0.4rem;font-family:monospace;">Leaderboard</span>
        </div>
        <div style="display:flex;gap:0.4rem;padding:0.25rem 0;border-bottom:1px solid #1e293b;margin-bottom:0.4rem;">
        <div style="font-size:0.45rem;font-weight:600;color:#475569;width:12px;">RK</div>
        <div style="font-size:0.45rem;font-weight:600;color:#475569;flex:1;">MODEL</div>
        <div style="font-size:0.45rem;font-weight:600;color:#475569;flex:2;">SCORE</div>
        <div style="font-size:0.45rem;font-weight:600;color:#475569;width:22px;text-align:right;">VAL</div>
        </div>
        <div style="display:flex;align-items:center;gap:0.4rem;padding:0.3rem 0;border-bottom:1px solid #0f1a2e;">
        <div style="font-size:0.55rem;color:#fbbf24;font-weight:800;width:12px;">1</div>
        <div style="font-size:0.55rem;color:#e2e8f0;flex:1;font-weight:600;">GPT-4o</div>
        <div style="flex:2;background:#1e293b;border-radius:3px;height:5px;overflow:hidden;">
        <div style="height:100%;width:89%;background:linear-gradient(90deg,#6366f1,#818cf8);border-radius:3px;"></div>
        </div>
        <div style="font-size:0.55rem;color:#a5b4fc;font-weight:700;width:22px;text-align:right;">0.89</div>
        </div>
        <div style="display:flex;align-items:center;gap:0.4rem;padding:0.3rem 0;border-bottom:1px solid #0f1a2e;">
        <div style="font-size:0.55rem;color:#94a3b8;font-weight:800;width:12px;">2</div>
        <div style="font-size:0.55rem;color:#e2e8f0;flex:1;font-weight:600;">Claude 3</div>
        <div style="flex:2;background:#1e293b;border-radius:3px;height:5px;overflow:hidden;">
        <div style="height:100%;width:85%;background:linear-gradient(90deg,#6366f1,#818cf8);border-radius:3px;"></div>
        </div>
        <div style="font-size:0.55rem;color:#a5b4fc;font-weight:700;width:22px;text-align:right;">0.85</div>
        </div>
        <div style="display:flex;align-items:center;gap:0.4rem;padding:0.3rem 0;border-bottom:1px solid #0f1a2e;">
        <div style="font-size:0.55rem;color:#94a3b8;font-weight:800;width:12px;">3</div>
        <div style="font-size:0.55rem;color:#e2e8f0;flex:1;font-weight:600;">Gemini</div>
        <div style="flex:2;background:#1e293b;border-radius:3px;height:5px;overflow:hidden;">
        <div style="height:100%;width:79%;background:linear-gradient(90deg,#6366f1,#818cf8);border-radius:3px;"></div>
        </div>
        <div style="font-size:0.55rem;color:#a5b4fc;font-weight:700;width:22px;text-align:right;">0.79</div>
        </div>
        <div style="display:flex;align-items:center;gap:0.4rem;padding:0.3rem 0;">
        <div style="font-size:0.55rem;color:#94a3b8;font-weight:800;width:12px;">4</div>
        <div style="font-size:0.55rem;color:#e2e8f0;flex:1;font-weight:600;">Mistral</div>
        <div style="flex:2;background:#1e293b;border-radius:3px;height:5px;overflow:hidden;">
        <div style="height:100%;width:72%;background:linear-gradient(90deg,#6366f1,#818cf8);opacity:0.7;border-radius:3px;"></div>
        </div>
        <div style="font-size:0.55rem;color:#a5b4fc;font-weight:700;width:22px;text-align:right;">0.76</div>
        </div>
        </div>
        <div style="padding:1.5rem;">
        <div style="background:#fefce8;width:38px;height:38px;border-radius:9px;display:flex;align-items:center;
                    justify-content:center;font-size:1.1rem;margin-bottom:0.75rem;">🏆</div>
        <div style="font-weight:800;font-size:1.35rem;color:#111827;margin-bottom:0.45rem;letter-spacing:-0.02em;">Model Leaderboard</div>
        <div style="font-size:0.95rem;color:#6b7280;line-height:1.65;margin-bottom:0.75rem;">
        Rank every model by trust score, safety, and cost in one view.
        </div>
        <div style="font-size:0.9rem;color:#374151;line-height:2.1;">
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
        <div id="pipeline-section" style="padding:4rem 3rem;background:#0f172a;">
        <div style="max-width:960px;margin:0 auto;">
        <div style="text-align:center;margin-bottom:3rem;">
        <div style="display:inline-block;background:#4f46e5;color:white;padding:0.55rem 1.5rem;
                    border-radius:8px;font-size:1.1rem;font-weight:800;letter-spacing:0.05em;
                    text-transform:uppercase;margin-bottom:1.25rem;">HOW IT WORKS</div>
        <div style="font-size:2.25rem;font-weight:800;color:white;letter-spacing:-0.03em;line-height:1.2;">
        The TrustLLM Pipeline
        </div>
        </div>

        <div style="margin-bottom:2rem;">
        <div style="font-size:0.65rem;font-weight:600;color:#475569;letter-spacing:0.08em;
                    text-transform:uppercase;margin-bottom:1rem;">Evaluation Pipeline</div>
        <div style="display:flex;align-items:center;flex-wrap:wrap;gap:0.25rem;justify-content:center;">
        <div style="background:#1e293b;border:1px solid #334155;border-radius:10px;
                    padding:0.75rem 1rem;text-align:center;min-width:106px;">
        <div style="font-size:1.1rem;margin-bottom:0.3rem;">📂</div>
        <div style="font-size:0.7rem;font-weight:700;color:#e2e8f0;">Datasets</div>
        <div style="font-size:0.55rem;color:#64748b;margin-top:0.1rem;">Prompts &amp; answers</div>
        </div>
        <div style="color:#475569;font-size:1.1rem;padding:0 0.4rem;">→</div>
        <div style="background:#1e293b;border:1px solid #334155;border-radius:10px;
                    padding:0.75rem 1rem;text-align:center;min-width:106px;">
        <div style="font-size:1.1rem;margin-bottom:0.3rem;">🤖</div>
        <div style="font-size:0.7rem;font-weight:700;color:#e2e8f0;">LLM Runner</div>
        <div style="font-size:0.55rem;color:#64748b;margin-top:0.1rem;">GPT, Claude, Mistral</div>
        </div>
        <div style="color:#475569;font-size:1.1rem;padding:0 0.4rem;">→</div>
        <div style="background:#1e293b;border:1px solid #334155;border-radius:10px;
                    padding:0.75rem 1rem;text-align:center;min-width:106px;">
        <div style="font-size:1.1rem;margin-bottom:0.3rem;">⚖️</div>
        <div style="font-size:0.7rem;font-weight:700;color:#e2e8f0;">Evaluator</div>
        <div style="font-size:0.55rem;color:#64748b;margin-top:0.1rem;">Score responses</div>
        </div>
        <div style="color:#475569;font-size:1.1rem;padding:0 0.4rem;">→</div>
        <div style="background:#312e81;border:1px solid #4338ca;border-radius:10px;
                    padding:0.75rem 1rem;text-align:center;min-width:106px;">
        <div style="font-size:1.1rem;margin-bottom:0.3rem;">🛡</div>
        <div style="font-size:0.7rem;font-weight:700;color:#a5b4fc;">Trust Score</div>
        <div style="font-size:0.55rem;color:#818cf8;margin-top:0.1rem;">Composite metric</div>
        </div>
        <div style="color:#475569;font-size:1.1rem;padding:0 0.4rem;">→</div>
        <div style="background:#1e293b;border:1px solid #334155;border-radius:10px;
                    padding:0.75rem 1rem;text-align:center;min-width:106px;">
        <div style="font-size:1.1rem;margin-bottom:0.3rem;">📊</div>
        <div style="font-size:0.7rem;font-weight:700;color:#e2e8f0;">Dashboard</div>
        <div style="font-size:0.55rem;color:#64748b;margin-top:0.1rem;">Visualize &amp; act</div>
        </div>
        </div>
        </div>

        <div>
        <div style="font-size:0.65rem;font-weight:600;color:#475569;letter-spacing:0.08em;
                    text-transform:uppercase;margin-bottom:1rem;">RAG / Document Pipeline</div>
        <div style="display:flex;align-items:center;flex-wrap:wrap;gap:0.25rem;justify-content:center;">
        <div style="background:#1e293b;border:1px solid #334155;border-radius:10px;
                    padding:0.75rem 1rem;text-align:center;min-width:106px;">
        <div style="font-size:1.1rem;margin-bottom:0.3rem;">📄</div>
        <div style="font-size:0.7rem;font-weight:700;color:#e2e8f0;">PDF / Docs</div>
        <div style="font-size:0.55rem;color:#64748b;margin-top:0.1rem;">Source material</div>
        </div>
        <div style="color:#475569;font-size:1.1rem;padding:0 0.4rem;">→</div>
        <div style="background:#1e293b;border:1px solid #334155;border-radius:10px;
                    padding:0.75rem 1rem;text-align:center;min-width:106px;">
        <div style="font-size:1.1rem;margin-bottom:0.3rem;">✂️</div>
        <div style="font-size:0.7rem;font-weight:700;color:#e2e8f0;">RAG Ingestion</div>
        <div style="font-size:0.55rem;color:#64748b;margin-top:0.1rem;">Chunk &amp; embed</div>
        </div>
        <div style="color:#475569;font-size:1.1rem;padding:0 0.4rem;">→</div>
        <div style="background:#1e293b;border:1px solid #334155;border-radius:10px;
                    padding:0.75rem 1rem;text-align:center;min-width:106px;">
        <div style="font-size:1.1rem;margin-bottom:0.3rem;">🗄️</div>
        <div style="font-size:0.7rem;font-weight:700;color:#e2e8f0;">ChromaDB</div>
        <div style="font-size:0.55rem;color:#64748b;margin-top:0.1rem;">Vector store</div>
        </div>
        <div style="color:#475569;font-size:1.1rem;padding:0 0.4rem;">→</div>
        <div style="background:#1e293b;border:1px solid #334155;border-radius:10px;
                    padding:0.75rem 1rem;text-align:center;min-width:106px;">
        <div style="font-size:1.1rem;margin-bottom:0.3rem;">🔍</div>
        <div style="font-size:0.7rem;font-weight:700;color:#e2e8f0;">Retriever</div>
        <div style="font-size:0.55rem;color:#64748b;margin-top:0.1rem;">Semantic search</div>
        </div>
        <div style="color:#475569;font-size:1.1rem;padding:0 0.4rem;">→</div>
        <div style="background:#312e81;border:1px solid #4338ca;border-radius:10px;
                    padding:0.75rem 1rem;text-align:center;min-width:106px;">
        <div style="font-size:1.1rem;margin-bottom:0.3rem;">🧪</div>
        <div style="font-size:0.7rem;font-weight:700;color:#a5b4fc;">RAG Eval</div>
        <div style="font-size:0.55rem;color:#818cf8;margin-top:0.1rem;">Fidelity score</div>
        </div>
        </div>
        </div>

        </div>
        </div>
    """), unsafe_allow_html=True)

    # ── STATS STRIP ───────────────────────────────────────────────────
    st.markdown(_h(f"""
        <div style="background:#111827;padding:3.5rem 3rem;">
        <div style="max-width:700px;margin:0 auto;
                    display:grid;grid-template-columns:repeat(3,1fr);gap:2rem;text-align:center;">
        <div>
        <div style="font-size:3.5rem;font-weight:900;color:white;letter-spacing:-0.04em;line-height:1;">
        {stats["prompts"]}</div>
        <div style="color:#6b7280;font-size:0.9rem;margin-top:0.4rem;">Prompts evaluated</div>
        </div>
        <div>
        <div style="font-size:3.5rem;font-weight:900;color:white;letter-spacing:-0.04em;line-height:1;">
        {stats["models"]}</div>
        <div style="color:#6b7280;font-size:0.9rem;margin-top:0.4rem;">Models tested</div>
        </div>
        <div>
        <div style="font-size:3.5rem;font-weight:900;color:white;letter-spacing:-0.04em;line-height:1;">
        {stats["avg_trust"]}</div>
        <div style="color:#6b7280;font-size:0.9rem;margin-top:0.4rem;">Avg trust score</div>
        </div>
        </div>
        </div>
    """), unsafe_allow_html=True)

    # ── SIGN-IN SECTION HEADER ────────────────────────────────────────
    st.markdown(_h("""
        <div id="signin-section"
             style="padding:5rem 2rem 3rem;
                    background:linear-gradient(135deg,#312e81 0%,#4f46e5 55%,#7c3aed 100%);">
        <div style="max-width:440px;margin:0 auto;text-align:center;">
        <div style="background:rgba(255,255,255,0.15);width:60px;height:60px;border-radius:16px;
                    display:inline-flex;align-items:center;justify-content:center;
                    font-size:1.75rem;color:white;margin-bottom:1.25rem;
                    border:1px solid rgba(255,255,255,0.25);
                    box-shadow:0 8px 24px rgba(0,0,0,0.2);">🛡</div>
        <div style="font-size:2.5rem;font-weight:900;color:white;letter-spacing:-0.04em;
                    margin-bottom:0.5rem;line-height:1.1;">Welcome back</div>
        <div style="font-size:1.1rem;color:#c7d2fe;font-weight:400;">Sign in to your TrustLLM account</div>
        </div>
        </div>
    """), unsafe_allow_html=True)

    # ── FORM CARD ─────────────────────────────────────────────────────
    _, form_col, _ = st.columns([1, 2, 1])
    with form_col:
        # Google OAuth (Supabase) or HTML demo button
        if is_configured():
            try:
                auth_url = get_auth_url()
                st.markdown(_h(f"""
                    <div style="margin-bottom:1rem;">
                    <a href="{auth_url}" target="_self"
                       style="display:flex;align-items:center;justify-content:center;gap:0.6rem;
                              background:white;color:#374151;border:1px solid #d1d5db;
                              border-radius:8px;padding:0.7rem 1rem;font-size:0.9rem;font-weight:500;
                              text-decoration:none;width:100%;box-sizing:border-box;">
                    <svg width="17" height="17" viewBox="0 0 48 48" style="flex-shrink:0;">
                    <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
                    <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
                    <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
                    <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
                    </svg>
                    Continue with Google
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
            """), unsafe_allow_html=True)

        st.markdown(_h("""
            <div style="display:flex;align-items:center;gap:0.75rem;margin:0 0 1rem 0;">
            <div style="flex:1;border-top:1px solid #d1d5db;"></div>
            <span style="color:#374151;font-size:0.8rem;font-weight:500;white-space:nowrap;">or continue with email</span>
            <div style="flex:1;border-top:1px solid #d1d5db;"></div>
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
            <span style="color:rgba(255,255,255,0.6);font-size:0.8rem;">
            Demo — Username: <strong style="color:rgba(255,255,255,0.9);">TestUser</strong>
            &nbsp;·&nbsp; Password: <strong style="color:rgba(255,255,255,0.9);">User123</strong>
            </span>
            </div>
        """), unsafe_allow_html=True)

    # ── FOOTER ────────────────────────────────────────────────────────
    st.markdown(_h("""
        <div style="background:#111827;padding:2rem 3rem;text-align:center;">
        <span style="color:#6b7280;font-size:0.8rem;">
        © 2025 TrustLLM · Powered by ChromaDB · Groq · Streamlit ·
        Built by <a href="https://www.linkedin.com/in/monika-kushwaha-52443735/"
        target="_blank" style="color:#6366f1;text-decoration:none;">Monika Kushwaha</a>
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
