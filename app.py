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
def _show_login() -> None:
    # ── CSS (Streamlit overrides — form & layout) ─────────────────────
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
        [data-testid="stMain"] h1,[data-testid="stMain"] h2,
        [data-testid="stMain"] h3,[data-testid="stMain"] h4{
            font-family:'Inter',system-ui,sans-serif!important;
            color:#0A0A0A!important;-webkit-text-fill-color:#0A0A0A!important;}
        [data-testid="stMain"] p,[data-testid="stMain"] label,
        [data-testid="stMain"] span:not([data-testid="stIconMaterial"]){
            font-family:'Inter',system-ui,sans-serif;}
        [data-testid="stForm"]{background:transparent!important;border:none!important;padding:0!important;box-shadow:none!important;}
        [data-testid="stTextInputRootElement"],[data-baseweb="input"],[data-baseweb="base-input"]{
            background:#FFFFFF!important;border-color:#E5E7EB!important;}
        [data-testid="stTextInputRootElement"]{border:1px solid #E5E7EB!important;border-radius:8px!important;}
        [data-testid="stTextInputRootElement"]:focus-within{border-color:#E8290B!important;box-shadow:0 0 0 3px rgba(232,41,11,0.1)!important;}
        [data-testid="stTextInputRootElement"] input{color:#0A0A0A!important;background:transparent!important;}
        [data-testid="stTextInput"] label{color:#374151!important;font-size:0.85rem!important;font-weight:500!important;}
        [data-testid="stFormSubmitButton"] button,[data-testid="stForm"] .stButton>button{
            background:#E8290B!important;color:white!important;border:none!important;
            border-radius:8px!important;font-weight:600!important;font-size:0.9rem!important;
            min-height:52px!important;padding:0!important;display:flex!important;
            align-items:center!important;justify-content:center!important;}
        [data-testid="stFormSubmitButton"] button:hover,[data-testid="stForm"] .stButton>button:hover{background:#C42208!important;}
        [data-testid="stBaseButton-secondary"]{width:100%!important;}
        [data-testid="stBaseButton-secondary"] button{
            min-height:52px!important;padding:0!important;display:flex!important;
            align-items:center!important;justify-content:center!important;width:100%!important;}
        [data-testid="stForm"] [data-testid="InputInstructions"]{display:none!important;}
        .stAlert{border-radius:8px!important;}
        </style>
    """), unsafe_allow_html=True)

    # ── MARKETING LANDING (single self-contained iframe) ──────────────
    _components.html("""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body{font-family:'Inter',system-ui,sans-serif;background:#fff;color:#0A0A0A;overflow-x:hidden}
:root{--red:#E8290B;--red-d:#C42208;--red-p:#FEF2F0;--ink:#0A0A0A;--gray:#6B7280;--bdr:#E5E7EB}

/* Entrance */
@keyframes enter{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:none}}
@keyframes enterL{from{opacity:0;transform:translateX(-24px)}to{opacity:1;transform:none}}
@keyframes enterR{from{opacity:0;transform:translateX(24px)}to{opacity:1;transform:none}}
@keyframes wordFade{0%,100%{opacity:0;transform:translateY(10px)}4%,13%{opacity:1;transform:none}17%{opacity:0;transform:translateY(-10px)}17.1%,99%{opacity:0;transform:translateY(10px)}}
@keyframes gradBg{0%,100%{background-color:#FFF1EE}50%{background-color:#FFE8E0}}
@keyframes sparkMove{0%{left:-8px;opacity:1}100%{left:calc(100% + 8px);opacity:.3}}

.e{animation:enter .65s cubic-bezier(.2,.7,.3,1) both}
.eL{animation:enterL .65s cubic-bezier(.2,.7,.3,1) both}
.eR{animation:enterR .65s cubic-bezier(.2,.7,.3,1) both}
.d1{animation-delay:.1s}.d2{animation-delay:.2s}.d3{animation-delay:.3s}
.d4{animation-delay:.4s}.d5{animation-delay:.5s}.d6{animation-delay:.6s}
.d7{animation-delay:.7s}.d8{animation-delay:.8s}

#prog{position:fixed;top:0;left:0;height:3px;width:0;background:var(--red);z-index:9999;pointer-events:none}

/* Banner */
#banner{background:var(--red);color:#fff;padding:.55rem 1rem;text-align:center;font-size:.82rem;font-weight:500;display:flex;align-items:center;justify-content:center;gap:.5rem;position:relative}
#banner a{color:#fff;font-weight:700;text-decoration:underline}
#banner .close{position:absolute;right:1rem;top:50%;transform:translateY(-50%);background:none;border:none;color:#fff;cursor:pointer;font-size:1.1rem;line-height:1;padding:0}

/* Nav */
nav{background:#fff;border-bottom:1px solid var(--bdr);padding:0 2rem;height:60px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:50}
.logo{display:flex;align-items:center;gap:.5rem;text-decoration:none}
.logo .mk{background:var(--red);width:26px;height:26px;border-radius:5px;display:flex;align-items:center;justify-content:center;color:#fff;font-weight:800;font-size:.8rem}
.logo .nm{font-weight:700;color:#0A0A0A;font-size:.95rem;letter-spacing:-.01em}
.nav-r{display:flex;align-items:center;gap:2rem}
.nav-r a{color:var(--gray);font-size:.85rem;font-weight:500;text-decoration:none}
.nav-cta{background:var(--red)!important;color:#fff!important;padding:.45rem 1rem;border-radius:6px;white-space:nowrap;font-size:.82rem!important;font-weight:600!important;transition:background .2s}
.nav-cta:hover{background:var(--red-d)!important}

/* Hero */
.hero{background:#fff;padding:3rem 2rem 4rem}
.hero-in{max-width:1100px;margin:0 auto;display:grid;grid-template-columns:1fr 1fr;gap:3rem;align-items:start}
@media(max-width:800px){.hero-in{grid-template-columns:1fr}}
.badge{display:inline-flex;align-items:center;gap:.5rem;padding:.3rem .85rem;border:1px solid var(--bdr);border-radius:999px;font-size:.72rem;color:var(--gray);font-weight:500;margin-bottom:1.5rem}
.badge .dot{width:6px;height:6px;border-radius:50%;background:var(--red)}
h1{font-size:clamp(32px,4.5vw,54px);font-weight:800;color:#0A0A0A;line-height:1.05;letter-spacing:-.03em;margin:0 0 .75rem}
.rot{font-size:clamp(26px,3.5vw,42px);font-weight:800;color:#0A0A0A;line-height:1.1;letter-spacing:-.03em;margin-bottom:1rem}
.word-wrap{position:relative;display:inline-block;min-width:12ch;height:1.1em;vertical-align:middle}
.word-wrap span{position:absolute;left:0;width:100%;opacity:0;white-space:nowrap;color:var(--red);font-weight:800;animation:wordFade 12s ease-in-out infinite}
.word-wrap span:nth-child(1){animation-delay:0s}.word-wrap span:nth-child(2){animation-delay:2s}
.word-wrap span:nth-child(3){animation-delay:4s}.word-wrap span:nth-child(4){animation-delay:6s}
.word-wrap span:nth-child(5){animation-delay:8s}.word-wrap span:nth-child(6){animation-delay:10s}
.sub{font-size:.97rem;color:var(--gray);max-width:480px;line-height:1.7;margin:.5rem 0 2rem}
.dim{display:inline;position:relative}
.dim::after{content:'';position:absolute;left:0;right:0;bottom:-1px;height:2px;background:var(--red);transform:scaleX(0);transform-origin:left;transition:transform .28s ease}
.dim:hover::after{transform:scaleX(1)}
.hl w{cursor:default;background-image:linear-gradient(var(--red-p),var(--red-p));background-repeat:no-repeat;background-position:0 88%;background-size:0% 90%;border-radius:3px;transition:background-size .28s cubic-bezier(.2,.7,.2,1),color .28s;padding:0 2px;color:#0A0A0A}
.hl w:hover{background-size:100% 90%;color:var(--red)}
.ctas{display:flex;gap:1rem;flex-wrap:wrap;margin-bottom:2rem}
.btn-p{background:var(--red);color:#fff;font-weight:600;font-size:.9rem;padding:.7rem 1.75rem;border-radius:8px;text-decoration:none;display:inline-block;transition:background .2s}
.btn-p:hover{background:var(--red-d)}
.btn-s{background:#fff;color:#0A0A0A;font-weight:500;font-size:.9rem;padding:.7rem 1.75rem;border-radius:8px;text-decoration:none;display:inline-block;border:1px solid var(--bdr);transition:border-color .2s,color .2s}
.btn-s:hover{border-color:var(--red);color:var(--red)}
.hero-chips{display:flex;flex-wrap:wrap;gap:1.5rem;padding-top:1.5rem;border-top:1px solid var(--bdr)}
.hero-chips span{font-size:.78rem;color:#9CA3AF}

/* Score panel */
.score-panel{background:#FAFAFA;border:1px solid var(--bdr);border-radius:12px;padding:1.35rem 1.5rem}
.run-tag{font-family:ui-monospace,monospace;font-size:.72rem;color:var(--gray);margin-bottom:1rem;padding:.35rem .75rem;background:#F3F4F6;border-radius:4px;display:inline-block}
.srow{display:flex;align-items:center;gap:.75rem;margin-bottom:.65rem}
.slabel{width:90px;color:#374151;font-size:.78rem;font-weight:500;flex-shrink:0}
.sbar{flex:1;height:6px;background:#F3F4F6;border-radius:3px;overflow:hidden}
.sfill{height:100%;border-radius:3px;background:var(--red);width:0;transition:width 1.2s cubic-bezier(.2,.7,.3,1)}
.sval{width:28px;text-align:right;font-size:.78rem;font-weight:600;color:#0A0A0A;flex-shrink:0}
.sample-note{display:inline-flex;align-items:center;gap:.35rem;margin-top:.85rem;font-size:.68rem;color:var(--gray)}
.green-dot{width:6px;height:6px;border-radius:50%;background:#10B981;display:inline-block;flex-shrink:0}
.live-dot{width:7px;height:7px;border-radius:50%;background:#10B981;display:inline-block;flex-shrink:0;animation:pulse 1.4s ease-in-out infinite}
@keyframes pulse{0%,100%{opacity:1;box-shadow:0 0 0 0 #4ade8066}50%{opacity:.5;box-shadow:0 0 0 6px #4ade8000}}
@keyframes rowflash{0%,12%{opacity:1;background:rgba(232,41,11,.06)}18%,100%{opacity:.38;background:transparent}}
.srow.live{animation:rowflash 6s linear infinite}
.srow:nth-child(2){animation-delay:0s}.srow:nth-child(3){animation-delay:1.2s}
.srow:nth-child(4){animation-delay:2.4s}.srow:nth-child(5){animation-delay:3.6s}.srow:nth-child(6){animation-delay:4.8s}

/* Stats */
.stats{background:#F9FAFB;border-top:1px solid var(--bdr);padding:3rem 2rem}
.stats-grid{max-width:900px;margin:0 auto;display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--bdr)}
@media(max-width:560px){.stats-grid{grid-template-columns:repeat(2,1fr)}}
.stat{background:#F9FAFB;padding:1.75rem 1.5rem;text-align:center}
.stat-n{font-size:2.6rem;font-weight:800;color:#0A0A0A;letter-spacing:-.03em;line-height:1}
.stat-l{font-size:.78rem;color:var(--gray);margin-top:.4rem;font-weight:500}

/* Dock */
.dock-sec{padding:3.5rem 2rem;background:#fff;border-top:1px solid var(--bdr)}
.dock-in{max-width:900px;margin:0 auto}
.eyebrow{font-size:.7rem;font-weight:700;letter-spacing:.15em;color:var(--red);margin-bottom:.75rem;text-transform:uppercase}
.sec-h{font-size:clamp(1.4rem,2.5vw,1.9rem);font-weight:800;color:#0A0A0A;letter-spacing:-.02em;margin:0 0 2rem}
.dock{display:flex;flex-wrap:wrap;gap:.75rem;align-items:flex-end;perspective:800px}
.ditem{background:#fff;border:1px solid var(--bdr);border-radius:8px;padding:.85rem 1.25rem;cursor:default;text-align:center;transition:transform .2s,box-shadow .2s,border-color .2s;transform-style:preserve-3d;min-width:120px}
.ditem:hover{transform:translateY(-8px) scale(1.06);box-shadow:0 12px 32px rgba(232,41,11,.15);border-color:var(--red)}
.dicon{font-size:1.4rem;margin-bottom:.35rem}
.dname{font-size:.82rem;font-weight:600;color:#0A0A0A}
.ddesc{font-size:.68rem;color:var(--gray);margin-top:.2rem}

/* Pipeline */
.pipe-sec{padding:4rem 2rem;background:var(--red-p);border-top:3px solid var(--red)}
.pipe-in{max-width:900px;margin:0 auto}
.pipe-row{display:flex;align-items:center;gap:0;flex-wrap:nowrap;margin-top:2rem;overflow-x:auto}
@media(max-width:640px){.pipe-row{flex-direction:column;align-items:stretch}}
.pnode{background:#fff;border:1.5px solid var(--bdr);border-radius:10px;padding:1rem 1.25rem;text-align:center;min-width:140px;flex:1;transition:border-color .2s,box-shadow .2s}
.pnode:hover{border-color:var(--red);box-shadow:0 4px 20px rgba(232,41,11,.12)}
.picon{font-size:1.3rem;margin-bottom:.3rem}
.plabel{font-size:.78rem;font-weight:700;color:#0A0A0A}
.psub{font-size:.68rem;color:var(--gray);margin-top:.15rem}
.pconn{flex:0 0 48px;display:flex;align-items:center;justify-content:center;position:relative;height:48px;overflow:hidden}
.parrow{position:absolute;width:100%;height:2px;background:linear-gradient(to right,var(--red),rgba(232,41,11,.3));top:50%;transform:translateY(-50%)}
.pspark{position:absolute;width:8px;height:8px;border-radius:50%;background:var(--red);top:50%;transform:translateY(-50%);animation:sparkMove 1.8s linear infinite}
@media(max-width:640px){.pconn{width:48px;height:40px;flex:0 0 auto;transform:rotate(90deg)}}

/* BYOK */
.byok{background:#FFF1EE;padding:3rem 2rem;border-top:3px solid var(--red)}
.byok-in{max-width:800px;margin:0 auto}
.byok h2{font-size:clamp(1.5rem,3vw,2.2rem);font-weight:800;color:#0A0A0A;letter-spacing:-.02em;margin:0 0 .75rem}
.byok p{color:var(--gray);font-size:.92rem;line-height:1.7;max-width:600px;margin:0 0 1.75rem}
.bchips{display:flex;flex-wrap:wrap;gap:.75rem}
.bchip{background:#fff;border:1px solid var(--red);color:var(--red);padding:.45rem 1rem;font-size:.8rem;font-weight:600;border-radius:6px}

/* How */
.how{padding:4rem 2rem;animation:gradBg 6s ease-in-out infinite}
.how-in{max-width:800px;margin:0 auto}
.steps{display:flex;flex-direction:column;position:relative}
.step{display:flex;gap:1.25rem;padding:1.5rem 0;border-bottom:1px solid rgba(0,0,0,.08);align-items:flex-start}
.step:last-child{border-bottom:none}
.snum{background:var(--red);min-width:36px;height:36px;border-radius:4px;display:flex;align-items:center;justify-content:center;color:#fff;font-size:.75rem;font-weight:700;flex-shrink:0}
.stitle{font-weight:600;color:#0A0A0A;margin-bottom:.3rem}
.sbody{font-size:.84rem;color:var(--gray);line-height:1.65}
.step-line{position:absolute;left:18px;top:36px;width:2px;background:var(--red);height:0;max-height:calc(100% - 72px);transition:height 1s cubic-bezier(.2,.7,.3,1);pointer-events:none}

/* Features */
.feat-sec{background:#fff;padding:4rem 2rem;border-top:1px solid var(--bdr)}
.feat-in{max-width:900px;margin:0 auto}
.feat-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:1px;background:var(--bdr)}
.fc{background:#fff;padding:1.5rem 1.25rem;transition:all .25s ease;cursor:default}
.fc:hover{box-shadow:0 8px 24px rgba(232,41,11,.12);position:relative;z-index:1}
.ft{font-weight:600;color:#0A0A0A;margin-bottom:.4rem}
.fd{font-size:.83rem;color:var(--gray);line-height:1.6;margin:0 0 1rem}
.fl{color:var(--red);font-size:.83rem;font-weight:600;text-decoration:none}

/* Models */
.model-sec{background:#F9FAFB;padding:4rem 2rem;border-top:1px solid var(--bdr)}
.model-in{max-width:900px;margin:0 auto}
.tab-bar{display:flex;position:relative;background:#F3F4F6;border-radius:8px;padding:3px;gap:2px;margin-bottom:1.5rem;overflow-x:auto}
.tab-pill{position:absolute;background:#fff;border-radius:6px;box-shadow:0 1px 4px rgba(0,0,0,.1);transition:all .28s cubic-bezier(.4,0,.2,1);pointer-events:none;top:3px;height:calc(100% - 6px)}
.tbtn{padding:.5rem 1.25rem;font-size:.82rem;font-weight:500;color:var(--gray);background:none;border:none;cursor:pointer;border-radius:6px;white-space:nowrap;transition:color .2s;position:relative;z-index:1;font-family:'Inter',sans-serif}
.tbtn.active{color:#0A0A0A;font-weight:600}
.tpanel{display:none;animation:enter .3s ease}
.tpanel.active{display:block}
.mchips{display:flex;flex-wrap:wrap;gap:.6rem}
.mchip{background:#fff;border:1px solid var(--bdr);color:#374151;padding:.4rem .9rem;font-size:.8rem;font-weight:500;border-radius:6px;transition:border-color .2s,color .2s}
.mchip:hover{border-color:var(--red);color:var(--red)}

/* Footer */
footer{background:#F9FAFB;border-top:1px solid var(--bdr);padding:2rem 1rem;text-align:center}
.flinks{display:flex;flex-wrap:wrap;justify-content:center;gap:1rem;margin-bottom:.75rem}
.flinks a{font-size:.85rem;color:var(--gray);text-decoration:none}
.flinks a:hover{color:var(--red)}
.fcopy{font-size:.78rem;color:var(--gray);line-height:1.6}
.fcopy a{color:var(--red);text-decoration:none}

.mag{display:inline-block}

@media(prefers-reduced-motion:reduce){
  *{animation-duration:.01ms!important;animation-iteration-count:1!important;transition-duration:.01ms!important}
  .step-line{height:calc(100% - 72px)!important}
}
</style>
</head>
<body>
<div id="prog"></div>

<div id="banner">
  ✦ TrustLLM now supports 21 models across 9 providers, including open-source —
  <a href="#sign-in">Try it →</a>
  <button class="close" onclick="this.parentElement.style.display='none';try{localStorage.setItem('tl_b','1')}catch(e){}">×</button>
</div>

<nav>
  <a class="logo" href="/">
    <span class="mk">T</span>
    <span class="nm">TrustLLM</span>
  </a>
  <div class="nav-r">
    <a href="#features">Features</a>
    <a href="#how-it-works">How It Works</a>
    <a href="#sign-in" class="nav-cta mag">Join Now →</a>
  </div>
</nav>

<section class="hero">
  <div class="hero-in">
    <div class="eL">
      <div class="badge"><span class="dot"></span>AI Trust Evaluation Platform</div>
      <h1>Your LLMs.<br><span style="color:var(--red)">Honestly</span> Evaluated.</h1>
      <div class="rot">Evaluate
        <span class="word-wrap">
          <span>Truthfulness</span><span>Safety</span><span>Fairness</span><span>Robustness</span><span>Privacy</span><span>Ethics</span>
        </span>
        in every response.
      </div>
      <p class="sub hl">Run rigorous trust benchmarks across <w>safety</w>, <w>fairness</w>, <w>robustness</w>, <w>privacy</w>, and <w>truthfulness</w>. Get verdicts, not vanity metrics.</p>
      <div class="ctas">
        <a href="#sign-in" class="btn-p mag">Start Evaluating →</a>
        <a href="#how-it-works" class="btn-s mag">See how it works</a>
      </div>
      <div class="hero-chips e d3">
        <span>✓ No GPU required</span>
        <span>✓ RAG-ready</span>
        <span>✓ Local inference</span>
        <span>✓ <span class="cnt" data-to="500" data-sfx="+">500+</span> eval prompts</span>
      </div>
    </div>
    <div class="eR d1">
      <div class="score-panel">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1rem"><span class="run-tag" style="margin-bottom:0">evaluation_run · gpt-4o</span><span style="display:flex;align-items:center;gap:6px;font-size:.72rem;color:#10B981"><span class="live-dot"></span>scoring</span></div>
        <div class="srow live"><span class="slabel">Truthfulness</span><div class="sbar"><div class="sfill" data-w="91"></div></div><span class="sval">91</span></div>
        <div class="srow live"><span class="slabel">Safety</span><div class="sbar"><div class="sfill" data-w="88"></div></div><span class="sval">88</span></div>
        <div class="srow live"><span class="slabel">Fairness</span><div class="sbar"><div class="sfill" data-w="83"></div></div><span class="sval">83</span></div>
        <div class="srow live"><span class="slabel">Privacy</span><div class="sbar"><div class="sfill" data-w="95"></div></div><span class="sval">95</span></div>
        <div class="srow live"><span class="slabel">Robustness</span><div class="sbar"><div class="sfill" data-w="79"></div></div><span class="sval">79</span></div>
        <div class="srow live"><span class="slabel">Ethics</span><div class="sbar"><div class="sfill" data-w="87"></div></div><span class="sval">87</span></div>
        <div class="sample-note"><span class="green-dot"></span>Illustrative sample data — sign in to run real evaluations</div>
      </div>
    </div>
  </div>
</section>

<section class="stats">
  <div class="stats-grid">
    <div class="stat e d1"><div class="stat-n cnt" data-to="6">6</div><div class="stat-l">Trust Dimensions</div></div>
    <div class="stat e d2"><div class="stat-n cnt" data-to="21">21</div><div class="stat-l">Models Evaluated</div></div>
    <div class="stat e d3"><div class="stat-n cnt" data-to="9">9</div><div class="stat-l">Providers</div></div>
    <div class="stat e d4"><div class="stat-n cnt" data-to="500" data-sfx="+">500+</div><div class="stat-l">Eval Prompts</div></div>
  </div>
</section>

<section class="dock-sec">
  <div class="dock-in">
    <p class="eyebrow">— SIX TRUST DIMENSIONS</p>
    <h2 class="sec-h e d1">What gets measured.</h2>
    <div class="dock e d2">
      <div class="ditem"><div class="dicon">🛡️</div><div class="dname">Safety</div><div class="ddesc">Refusal &amp; harm prevention</div></div>
      <div class="ditem"><div class="dicon">⚖️</div><div class="dname">Fairness</div><div class="ddesc">Bias detection across groups</div></div>
      <div class="ditem"><div class="dicon">🔒</div><div class="dname">Privacy</div><div class="ddesc">PII &amp; data protection</div></div>
      <div class="ditem"><div class="dicon">🎯</div><div class="dname">Truthfulness</div><div class="ddesc">Hallucination resistance</div></div>
      <div class="ditem"><div class="dicon">💪</div><div class="dname">Robustness</div><div class="ddesc">Adversarial resilience</div></div>
      <div class="ditem"><div class="dicon">🤝</div><div class="dname">Ethics</div><div class="ddesc">Machine ethics alignment</div></div>
    </div>
  </div>
</section>

<section class="pipe-sec">
  <div class="pipe-in">
    <p class="eyebrow">— EVALUATION PIPELINE</p>
    <h2 class="sec-h e d1">How a trust score is computed.</h2>
    <div class="pipe-row e d2">
      <div class="pnode"><div class="picon">📝</div><div class="plabel">Prompt</div><div class="psub">Adversarial test cases</div></div>
      <div class="pconn"><div class="parrow"></div><div class="pspark"></div></div>
      <div class="pnode"><div class="picon">🔍</div><div class="plabel">Retrieval</div><div class="psub">RAG context injection</div></div>
      <div class="pconn"><div class="parrow"></div><div class="pspark" style="animation-delay:.6s"></div></div>
      <div class="pnode"><div class="picon">⚖️</div><div class="plabel">LLM-as-Judge</div><div class="psub">Score each dimension</div></div>
      <div class="pconn"><div class="parrow"></div><div class="pspark" style="animation-delay:1.2s"></div></div>
      <div class="pnode"><div class="picon">📊</div><div class="plabel">Score</div><div class="psub">Trust verdict + report</div></div>
    </div>
  </div>
</section>

<section class="byok">
  <div class="byok-in e">
    <p class="eyebrow">— BRING YOUR OWN KEY</p>
    <h2>Your Keys. Any Model.<br><span style="color:var(--red)">Full Trust Report.</span></h2>
    <p>Connect your own API keys for OpenAI, Anthropic, Google, Together AI, Fireworks, or Cerebras and benchmark ChatGPT, Claude, Gemini, and 18 open-source models head-to-head — on your data, your prompts, in real time.</p>
    <div class="bchips">
      <span class="bchip">ChatGPT · OpenAI</span>
      <span class="bchip">Claude · Anthropic</span>
      <span class="bchip">Gemini · Google</span>
      <span class="bchip">Open Source · Free Tier</span>
    </div>
  </div>
</section>

<section class="how" id="how-it-works">
  <div class="how-in">
    <p class="eyebrow">— HOW IT WORKS</p>
    <h2 class="sec-h">5 Steps to a Trust Score.</h2>
    <div class="steps e" id="steps-col">
      <div class="step-line" id="step-line"></div>
      <div class="step"><div class="snum">01</div><div><div class="stitle">Connect Your Models</div><div class="sbody">Add your LLM endpoint or paste API keys for OpenAI, Anthropic, Google, Together AI, Fireworks, Cerebras, or any OpenAI-compatible API.</div></div></div>
      <div class="step"><div class="snum">02</div><div><div class="stitle">Select Evaluation Dimensions</div><div class="sbody">Choose from Safety, Fairness, Robustness, Privacy, Truthfulness, and Machine Ethics — or run the full suite.</div></div></div>
      <div class="step"><div class="snum">03</div><div><div class="stitle">Run Adversarial Prompts</div><div class="sbody">500+ curated prompts probe jailbreaks, bias probes, hallucination traps, privacy leaks, and more.</div></div></div>
      <div class="step"><div class="snum">04</div><div><div class="stitle">Get Scored Verdicts</div><div class="sbody">Each response is scored by a judge LLM and rule-based classifiers. Results aggregate into per-dimension scores and a Trust Score.</div></div></div>
      <div class="step"><div class="snum">05</div><div><div class="stitle">Compare and Decide</div><div class="sbody">Color-coded leaderboard shows where each model excels and fails. Export reports and track regressions over time.</div></div></div>
    </div>
  </div>
</section>

<section class="feat-sec" id="features">
  <div class="feat-in">
    <p class="eyebrow">— FEATURES</p>
    <h2 class="sec-h e d1">Everything you need to trust your LLM.</h2>
    <div class="feat-grid">
      <div class="fc e d2"><div class="ft">Single Prompt Eval</div><p class="fd">Test any prompt against a model instantly. See trust scores across all six dimensions in real time.</p><a class="fl" href="#sign-in">Explore →</a></div>
      <div class="fc e d3"><div class="ft">Batch Evaluation</div><p class="fd">Run your full prompt dataset through multiple models at once. Compare side-by-side at scale.</p><a class="fl" href="#sign-in">Explore →</a></div>
      <div class="fc e d4"><div class="ft">RAG Testing</div><p class="fd">Upload documents, build a ChromaDB vector store, and evaluate retrieval faithfulness and grounding accuracy.</p><a class="fl" href="#sign-in">Explore →</a></div>
      <div class="fc e d5"><div class="ft">Agent Performance</div><p class="fd">Benchmark autonomous agents on tool-call accuracy, hallucination rate, and semantic correctness.</p><a class="fl" href="#sign-in">Explore →</a></div>
    </div>
  </div>
</section>

<section class="model-sec" id="models">
  <div class="model-in">
    <p class="eyebrow">— MODELS EVALUATED</p>
    <h2 class="sec-h e d1"><span class="cnt" data-to="21">21</span> Models. <span class="cnt" data-to="9">9</span> Providers.</h2>
    <div class="tab-bar e d2" id="tab-bar">
      <div class="tab-pill" id="tab-pill"></div>
      <button class="tbtn active" data-tab="openai">OpenAI</button>
      <button class="tbtn" data-tab="anthropic">Anthropic</button>
      <button class="tbtn" data-tab="google">Google</button>
      <button class="tbtn" data-tab="oss">Open Source</button>
    </div>
    <div class="tpanel active" data-panel="openai">
      <div class="mchips">
        <span class="mchip">GPT-4o</span><span class="mchip">GPT-4o mini</span><span class="mchip">GPT-4 Turbo</span>
      </div>
    </div>
    <div class="tpanel" data-panel="anthropic">
      <div class="mchips">
        <span class="mchip">Claude 3.5 Sonnet</span><span class="mchip">Claude 3.5 Haiku</span><span class="mchip">Claude 3 Opus</span>
      </div>
    </div>
    <div class="tpanel" data-panel="google">
      <div class="mchips">
        <span class="mchip">Gemini 2.0 Flash</span><span class="mchip">Gemini 2.0 Flash Lite</span><span class="mchip">Gemini 1.5 Pro</span>
      </div>
    </div>
    <div class="tpanel" data-panel="oss">
      <div class="mchips">
        <span class="mchip">Qwen 2.5 72B</span><span class="mchip">Llama 3.3 70B</span><span class="mchip">Llama 3.1 8B</span><span class="mchip">DeepSeek R1</span><span class="mchip">Mistral Large</span><span class="mchip">Mixtral 8x7B</span>
      </div>
    </div>
  </div>
</section>


<script>
(function(){
var R=window.matchMedia('(prefers-reduced-motion:reduce)').matches;

// Auto-resize iframe height in parent
function resize(){
  try{
    // Measure the body's layout height — NOT documentElement.scrollHeight,
    // which is floored by the iframe's own viewport height and so can only
    // ever grow the frame (that caused a runaway ~9000px blank gap).
    var h=document.body.offsetHeight;
    if(h<100)return;  // ignore transient/pre-layout readings (avoid collapsing)
    var fs=window.parent.document.querySelectorAll('iframe');
    for(var i=0;i<fs.length;i++){
      try{if(fs[i].contentWindow===window){
        // Clear any stale min-height first — a previously-set tall min-height
        // would floor the element and ignore a smaller height (the bug).
        fs[i].style.minHeight='0px';
        fs[i].style.height=h+'px';
        break;
      }}catch(e){}
    }
  }catch(e){}
}
resize();
// Re-measure for a few seconds so the frame converges to the final content
// height once fonts/width have settled (a single early read can be too tall).
var _t=0,_iv=setInterval(function(){resize();if(++_t>24)clearInterval(_iv);},250);
window.addEventListener('load',resize);
window.addEventListener('resize',resize);
new ResizeObserver(function(){resize();}).observe(document.body);

// Scroll progress bar (listens to parent page scroll)
try{
  window.parent.addEventListener('scroll',function(){
    try{
      var d=window.parent.document.documentElement;
      var el=document.getElementById('prog');
      if(el){var p=d.scrollTop/(d.scrollHeight-d.clientHeight)||0;el.style.width=Math.min(p,1)*100+'%';}
    }catch(e){}
  },{passive:true});
}catch(e){}

// Anchor links → scroll parent
document.querySelectorAll('a[href^="#"]').forEach(function(a){
  a.addEventListener('click',function(e){
    e.preventDefault();
    var id=a.getAttribute('href').slice(1);
    try{
      var el=window.parent.document.getElementById(id);
      if(el){el.scrollIntoView({behavior:'smooth'});}
      else{window.parent.scrollTo({top:window.parent.document.body.scrollHeight,behavior:'smooth'});}
    }catch(e){}
  });
});

// Count-up
function countUp(el){
  if(R){el.textContent=el.dataset.to+(el.dataset.sfx||'');return;}
  var to=+el.dataset.to,sfx=el.dataset.sfx||'',s=null,dur=1100;
  requestAnimationFrame(function f(t){
    if(!s)s=t;var p=Math.min((t-s)/dur,1),ease=1-Math.pow(1-p,3);
    el.textContent=Math.round(ease*to)+sfx;
    if(p<1)requestAnimationFrame(f);
  });
}
setTimeout(function(){document.querySelectorAll('.cnt').forEach(countUp);},R?0:700);

// Score bar fill
setTimeout(function(){
  document.querySelectorAll('.sfill').forEach(function(el){
    el.style.width=(el.dataset.w||'0')+'%';
  });
},R?0:500);

// Step connector line
var sc=document.getElementById('steps-col'),sl=document.getElementById('step-line');
if(sc&&sl){
  var h=sc.offsetHeight-72;
  if(R){sl.style.height=h+'px';}
  else{setTimeout(function(){sl.style.height=h+'px';},900);}
}

// Magnetic buttons
function wireMag(el){
  if(el._m)return;el._m=true;
  el.addEventListener('mousemove',function(ev){
    var r=el.getBoundingClientRect();
    el.style.transform='translate('+(ev.clientX-r.left-r.width/2)*.22+'px,'+(ev.clientY-r.top-r.height/2)*.22+'px)';
  });
  el.addEventListener('mouseleave',function(){el.style.transform='';});
}
if(!R)document.querySelectorAll('.mag').forEach(wireMag);

// macOS dock proximity magnification + 3D tilt
(function(){
  if(R)return;
  var dock=document.querySelector('.dock');
  if(dock){
    var dcards=[].slice.call(dock.querySelectorAll('.ditem'));
    var MAX=1.38,RANGE=170,LIFT=20;
    dock.addEventListener('mousemove',function(ev){
      dcards.forEach(function(c){
        var r=c.getBoundingClientRect();
        var cx=r.left+r.width/2;
        var d=Math.abs(ev.clientX-cx);
        var f=Math.max(0,1-d/RANGE);
        c.style.transform='translateY('+(- LIFT*f)+'px) scale('+(1+(MAX-1)*f)+')';
        c.style.zIndex=Math.round(f*10);
        c.style.borderColor=f>.5?'var(--red)':'';
        // per-card tilt
        var px=(ev.clientX-r.left)/r.width-.5;
        var py=(ev.clientY-r.top)/r.height-.5;
        c.style.transform+=' rotateY('+(px*14)+'deg) rotateX('+(-py*14)+'deg)';
      });
    });
    dock.addEventListener('mouseleave',function(){
      dcards.forEach(function(c){c.style.transform='';c.style.zIndex='';c.style.borderColor='';});
    });
  }
  // 3D tilt on feature cards (no proximity)
  document.querySelectorAll('.fc').forEach(function(el){
    if(el._t)return;el._t=true;
    el.addEventListener('mousemove',function(ev){
      var r=el.getBoundingClientRect();
      var x=((ev.clientY-r.top)/r.height-.5)*12,y=-((ev.clientX-r.left)/r.width-.5)*12;
      el.style.transform='perspective(600px) rotateX('+x+'deg) rotateY('+y+'deg) translateY(-4px)';
      el.style.boxShadow='0 8px 24px rgba(232,41,11,.12)';
    });
    el.addEventListener('mouseleave',function(){el.style.transform='';el.style.boxShadow='';});
  });
})();

// Tab switcher with sliding pill
var bar=document.getElementById('tab-bar'),pill=document.getElementById('tab-pill');
function setPill(btn){
  if(!btn||!bar)return;
  var br=bar.getBoundingClientRect(),r=btn.getBoundingClientRect();
  pill.style.left=(r.left-br.left+bar.scrollLeft)+'px';
  pill.style.width=r.width+'px';
}
function activateTab(id){
  document.querySelectorAll('.tbtn').forEach(function(b){b.classList.toggle('active',b.dataset.tab===id);});
  document.querySelectorAll('.tpanel').forEach(function(p){p.classList.toggle('active',p.dataset.panel===id);});
  setPill(document.querySelector('.tbtn[data-tab="'+id+'"]'));
}
document.querySelectorAll('.tbtn').forEach(function(btn){
  btn.addEventListener('click',function(){activateTab(btn.dataset.tab);});
});
setTimeout(function(){setPill(document.querySelector('.tbtn.active'));},150);

// Banner: restore dismissed state
try{if(localStorage.getItem('tl_b')==='1'){var b=document.getElementById('banner');if(b)b.style.display='none';}}catch(e){}
})();
</script>
</body>
</html>""", height=3700, scrolling=False)

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

            if st.button("CREATE ACCOUNT →", key="to_create", use_container_width=True):
                st.session_state.login_mode = "create"
                st.rerun()

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

    # ── FOOTER ────────────────────────────────────────────────────────
    st.markdown(_h("""
        <div style="background:#F9FAFB;border-top:1px solid #E5E7EB;padding:32px 16px;
                    text-align:center;font-family:'Inter',system-ui,sans-serif;box-sizing:border-box;width:100%;">
          <div style="display:flex;flex-wrap:wrap;justify-content:center;gap:16px;margin-bottom:12px;">
            <a href="#features" style="font-size:14px;color:#6B7280;text-decoration:none;">How it works</a>
            <a href="#how-it-works" style="font-size:14px;color:#6B7280;text-decoration:none;">Trust dimensions</a>
            <a href="#models" style="font-size:14px;color:#6B7280;text-decoration:none;">Models</a>
            <a href="#sign-in" style="font-size:14px;color:#6B7280;text-decoration:none;">Sign in</a>
          </div>
          <p style="font-size:13px;color:#6B7280;line-height:1.6;margin:0;">
            © 2025 TrustLLM · AI Model Evaluation Platform · Powered by ChromaDB · Groq · Streamlit ·
            <span style="white-space:nowrap;">Built by
              <a href="https://www.linkedin.com/in/monika-kushwaha-52443735" target="_blank"
                 rel="noopener noreferrer" style="color:#E8420A;text-decoration:none;">Monika Kushwaha</a>
            </span>
          </p>
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
    ("RAG Testing",       "📚", "Evaluate"),
    ("RAG Debugger",      "🧪", "Evaluate"),
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

# -----------------------------------------------------------------------
# Feature tour — shown once after first login
# -----------------------------------------------------------------------
_TOUR_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body{font-family:'Inter',system-ui,sans-serif;background:#fff;color:#0A0A0A;overflow:hidden;height:100%}
:root{--red:#E8290B;--red-d:#C42208;--red-p:#FEF2F0;--ink:#0A0A0A;--gray:#6B7280;--bdr:#E5E7EB;--off:#F9F8F6}

/* Slide track */
.track{display:flex;height:100vh;transition:transform .55s cubic-bezier(.4,0,.2,1)}
.slide{min-width:100vw;height:100vh;overflow-y:auto;padding:3rem 2rem 5rem;display:flex;flex-direction:column;align-items:center;justify-content:flex-start}

/* Header */
.tour-hdr{width:100%;max-width:860px;display:flex;align-items:center;justify-content:space-between;margin-bottom:2.5rem;flex-shrink:0}
.tour-logo{display:flex;align-items:center;gap:.5rem;font-weight:700;font-size:.95rem;color:#0A0A0A}
.tour-logo .mk{background:var(--red);width:24px;height:24px;border-radius:5px;display:flex;align-items:center;justify-content:center;color:#fff;font-weight:800;font-size:.75rem}
.skip-btn{background:none;border:none;cursor:pointer;font-size:.82rem;color:var(--gray);font-family:'Inter',sans-serif;padding:.35rem .75rem;border-radius:6px;transition:color .2s,background .2s}
.skip-btn:hover{color:#0A0A0A;background:#F3F4F6}

/* Dots */
.dots{display:flex;gap:.5rem;justify-content:center;margin-bottom:2rem;flex-shrink:0}
.dot{width:8px;height:8px;border-radius:50%;background:#E5E7EB;transition:all .3s cubic-bezier(.4,0,.2,1)}
.dot.on{background:var(--red);width:24px;border-radius:4px}

/* Content area */
.slide-body{width:100%;max-width:860px;flex:1}
.eyebrow{font-size:.7rem;font-weight:700;letter-spacing:.15em;color:var(--red);text-transform:uppercase;margin-bottom:.75rem;display:flex;align-items:center;gap:.5rem}
.eyebrow .ldot{width:6px;height:6px;border-radius:50%;background:var(--red);animation:lpulse 1.4s ease-in-out infinite}
@keyframes lpulse{0%,100%{box-shadow:0 0 0 0 rgba(232,41,11,.5)}50%{box-shadow:0 0 0 6px rgba(232,41,11,0)}}
h2.tour-h{font-family:'Space Grotesk',sans-serif;font-size:clamp(1.8rem,4vw,2.8rem);font-weight:700;letter-spacing:-.02em;line-height:1.08;margin:0 0 1rem;color:#0A0A0A}
.tour-lead{font-size:1.02rem;color:var(--gray);line-height:1.7;max-width:52ch;margin:0 0 2.5rem}
.hl w{cursor:default;background-image:linear-gradient(var(--red-p),var(--red-p));background-repeat:no-repeat;background-position:0 88%;background-size:0% 90%;border-radius:3px;transition:background-size .28s cubic-bezier(.2,.7,.2,1),color .28s;padding:0 2px}
.hl w:hover{background-size:100% 90%;color:var(--red)}

/* Slide 1 — stat tiles */
.stat-row{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--bdr);border:1px solid var(--bdr);border-radius:12px;overflow:hidden;margin-top:1rem}
@media(max-width:560px){.stat-row{grid-template-columns:repeat(2,1fr)}}
.stile{background:#fff;padding:1.5rem 1.25rem;text-align:center}
.stile .sn{font-family:'Space Grotesk',sans-serif;font-size:2.2rem;font-weight:700;color:#0A0A0A;letter-spacing:-.03em;line-height:1}
.stile .sl{font-size:.75rem;color:var(--gray);margin-top:.35rem;font-weight:500}

/* Slide 2 — scoring panel replica */
.score-demo{background:var(--off);border:1px solid var(--bdr);border-radius:14px;padding:1.5rem}
.run-row{display:flex;align-items:center;justify-content:space-between;margin-bottom:1.25rem}
.run-tag{font-family:ui-monospace,monospace;font-size:.72rem;color:var(--gray);padding:.35rem .75rem;background:#F3F4F6;border-radius:4px}
.live-ind{display:flex;align-items:center;gap:6px;font-size:.72rem;color:#10B981}
.livepulse{width:7px;height:7px;border-radius:50%;background:#10B981;animation:lpulse 1.4s ease-in-out infinite}
.drow{display:flex;align-items:center;gap:.75rem;padding:.6rem 0;border-top:1px solid rgba(0,0,0,.06);font-size:.82rem}
.drow:first-child{border-top:none}
@keyframes dflash{0%,12%{opacity:1;background:rgba(232,41,11,.06)}18%,100%{opacity:.38;background:transparent}}
.drow.anim{animation:dflash 6s linear infinite;border-radius:6px;margin:0 -.5rem;padding:.6rem .5rem}
.drow:nth-child(2){animation-delay:0s}.drow:nth-child(3){animation-delay:1.2s}.drow:nth-child(4){animation-delay:2.4s}.drow:nth-child(5){animation-delay:3.6s}.drow:nth-child(6){animation-delay:4.8s}.drow:nth-child(7){animation-delay:6s}
.dlabel{width:88px;color:#374151;font-weight:500;flex-shrink:0}
.dbar{flex:1;height:6px;background:#E5E7EB;border-radius:3px;overflow:hidden}
.dfill{height:100%;border-radius:3px;background:var(--red);width:0;transition:width 1.2s cubic-bezier(.2,.7,.3,1)}
.dval{width:28px;text-align:right;font-weight:600;color:#0A0A0A;flex-shrink:0}

/* Slide 3 — dimension dock */
.tour-dock{display:flex;flex-wrap:wrap;gap:.75rem;align-items:flex-end;perspective:900px;margin-top:1rem}
.tdc{background:#fff;border:1.5px solid var(--bdr);border-radius:12px;padding:.9rem 1.1rem;cursor:default;text-align:center;transition:transform .18s ease,box-shadow .18s,border-color .18s;transform-style:preserve-3d;min-width:110px}
.tdico{font-size:1.35rem;margin-bottom:.3rem}
.tdname{font-family:'Space Grotesk',sans-serif;font-size:.82rem;font-weight:600;color:#0A0A0A}
.tddesc{font-size:.67rem;color:var(--gray);margin-top:.15rem}

/* Slide 4 — leaderboard mini */
.mini-lb{border:1px solid var(--bdr);border-radius:12px;overflow:hidden}
.lb-head{display:grid;grid-template-columns:32px 1fr 80px 80px 80px;gap:1rem;padding:.65rem 1rem;background:var(--off);font-size:.72rem;font-weight:600;color:var(--gray);text-transform:uppercase;letter-spacing:.08em}
@media(max-width:500px){.lb-head{grid-template-columns:32px 1fr 80px}.lb-head .hd,.lb-head .hp{display:none}}
.lb-row{display:grid;grid-template-columns:32px 1fr 80px 80px 80px;gap:1rem;padding:.75rem 1rem;border-top:1px solid var(--bdr);font-size:.83rem;align-items:center;transition:background .2s}
.lb-row:hover{background:var(--off)}
@media(max-width:500px){.lb-row{grid-template-columns:32px 1fr 80px}.lb-row .hd,.lb-row .hp{display:none}}
.rank{font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:.85rem}
.rank.r1{color:var(--red)}
.mname{font-weight:600;color:#0A0A0A}
.mprov{font-size:.72rem;color:var(--gray)}
.trust{font-family:'Space Grotesk',sans-serif;font-weight:700;color:#0A0A0A;font-size:.92rem}
.badge{display:inline-block;padding:.2rem .6rem;border-radius:99px;font-size:.68rem;font-weight:600}
.badge.good{background:rgba(16,185,129,.12);color:#047857}
.badge.med{background:rgba(245,158,11,.12);color:#92400E}

/* Slide 5 — welcome to dashboard */
.ready-card{background:var(--red);border-radius:16px;padding:2.5rem;color:#fff;text-align:center;max-width:480px;margin:0 auto}
.ready-card h3{font-family:'Space Grotesk',sans-serif;font-size:1.8rem;font-weight:700;letter-spacing:-.02em;margin-bottom:.75rem}
.ready-card p{font-size:.9rem;opacity:.88;line-height:1.65;margin-bottom:1.75rem}
.ready-card .quick-links{display:flex;flex-wrap:wrap;gap:.6rem;justify-content:center}
.ready-card .qlink{background:rgba(255,255,255,.18);border:1px solid rgba(255,255,255,.3);color:#fff;padding:.45rem 1rem;border-radius:6px;font-size:.8rem;font-weight:500;text-decoration:none;backdrop-filter:blur(4px);transition:background .2s}
.ready-card .qlink:hover{background:rgba(255,255,255,.28)}

/* Nav buttons */
.tour-nav{position:fixed;bottom:0;left:0;right:0;padding:1.25rem 2rem;display:flex;align-items:center;justify-content:space-between;background:rgba(255,255,255,.92);backdrop-filter:blur(8px);border-top:1px solid var(--bdr);z-index:50}
.nav-back{background:none;border:1.5px solid var(--bdr);color:#374151;padding:.6rem 1.5rem;border-radius:8px;font-size:.88rem;font-weight:500;cursor:pointer;font-family:'Inter',sans-serif;transition:border-color .2s,color .2s}
.nav-back:hover{border-color:#0A0A0A;color:#0A0A0A}
.nav-next{background:var(--red);color:#fff;border:none;padding:.6rem 1.75rem;border-radius:8px;font-size:.88rem;font-weight:600;cursor:pointer;font-family:'Inter',sans-serif;transition:background .2s}
.nav-next:hover{background:var(--red-d)}
.nav-done{background:#0A0A0A;color:#fff;border:none;padding:.6rem 1.75rem;border-radius:8px;font-size:.88rem;font-weight:600;cursor:pointer;font-family:'Inter',sans-serif;transition:opacity .2s}
.nav-done:hover{opacity:.85}

/* Entrance */
@keyframes slIn{from{opacity:0;transform:translateY(18px)}to{opacity:1;transform:none}}
.sl-enter{animation:slIn .5s cubic-bezier(.2,.7,.3,1) both}
.sl-d1{animation-delay:.08s}.sl-d2{animation-delay:.16s}.sl-d3{animation-delay:.24s}.sl-d4{animation-delay:.32s}

@media(prefers-reduced-motion:reduce){
  *{animation-duration:.01ms!important;transition-duration:.01ms!important}
}
</style>
</head>
<body>

<div class="track" id="track">

  <!-- SLIDE 1: Welcome -->
  <div class="slide">
    <div class="tour-hdr">
      <div class="tour-logo"><span class="mk">T</span>TrustLLM</div>
      <button class="skip-btn" onclick="done()">Skip tour</button>
    </div>
    <div class="dots" id="dots"></div>
    <div class="slide-body">
      <p class="eyebrow sl-enter"><span class="ldot"></span>Step 1 of 5</p>
      <h2 class="tour-h sl-enter sl-d1">You're in.<br>Here's what TrustLLM does.</h2>
      <p class="tour-lead sl-enter sl-d2 hl"><w>TrustLLM</w> runs <w>adversarial</w> <w>benchmarks</w> against your LLMs and scores every response across <w>six</w> <w>trust</w> <w>dimensions</w> — so you catch hallucinations, bias, and safety failures before your users do.</p>
      <div class="stat-row sl-enter sl-d3">
        <div class="stile"><div class="sn cnt" data-to="6">6</div><div class="sl">Trust dimensions</div></div>
        <div class="stile"><div class="sn cnt" data-to="21">21</div><div class="sl">Models</div></div>
        <div class="stile"><div class="sn cnt" data-to="9">9</div><div class="sl">Providers</div></div>
        <div class="stile"><div class="sn cnt" data-to="500" data-sfx="+">500+</div><div class="sl">Eval prompts</div></div>
      </div>
    </div>
  </div>

  <!-- SLIDE 2: Scoring panel -->
  <div class="slide">
    <div class="tour-hdr">
      <div class="tour-logo"><span class="mk">T</span>TrustLLM</div>
      <button class="skip-btn" onclick="done()">Skip tour</button>
    </div>
    <div class="dots" id="dots2"></div>
    <div class="slide-body">
      <p class="eyebrow sl-enter"><span class="ldot"></span>Step 2 of 5</p>
      <h2 class="tour-h sl-enter sl-d1">Every response, scored live.</h2>
      <p class="tour-lead sl-enter sl-d2">As your LLM responds, the judge pipeline scores it across all six dimensions in real time. No hand-labelling. No guessing.</p>
      <div class="score-demo sl-enter sl-d3">
        <div class="run-row">
          <span class="run-tag">evaluation_run · gpt-4o</span>
          <span class="live-ind"><span class="livepulse"></span>scoring live</span>
        </div>
        <div class="drow anim"><span class="dlabel">Truthfulness</span><div class="dbar"><div class="dfill" data-w="91"></div></div><span class="dval">91</span></div>
        <div class="drow anim"><span class="dlabel">Safety</span><div class="dbar"><div class="dfill" data-w="88"></div></div><span class="dval">88</span></div>
        <div class="drow anim"><span class="dlabel">Fairness</span><div class="dbar"><div class="dfill" data-w="83"></div></div><span class="dval">83</span></div>
        <div class="drow anim"><span class="dlabel">Privacy</span><div class="dbar"><div class="dfill" data-w="95"></div></div><span class="dval">95</span></div>
        <div class="drow anim"><span class="dlabel">Robustness</span><div class="dbar"><div class="dfill" data-w="79"></div></div><span class="dval">79</span></div>
        <div class="drow anim"><span class="dlabel">Ethics</span><div class="dbar"><div class="dfill" data-w="87"></div></div><span class="dval">87</span></div>
      </div>
    </div>
  </div>

  <!-- SLIDE 3: Dimension dock -->
  <div class="slide">
    <div class="tour-hdr">
      <div class="tour-logo"><span class="mk">T</span>TrustLLM</div>
      <button class="skip-btn" onclick="done()">Skip tour</button>
    </div>
    <div class="dots" id="dots3"></div>
    <div class="slide-body">
      <p class="eyebrow sl-enter"><span class="ldot"></span>Step 3 of 5</p>
      <h2 class="tour-h sl-enter sl-d1">Six trust dimensions, independently scored.</h2>
      <p class="tour-lead sl-enter sl-d2">Each dimension targets a different failure mode. You can run the full suite or focus on the ones that matter most to your use case.</p>
      <div class="tour-dock sl-enter sl-d3" id="tdock">
        <div class="tdc"><div class="tdico">🎯</div><div class="tdname">Truthfulness</div><div class="tddesc">factual accuracy &amp; grounding</div></div>
        <div class="tdc"><div class="tdico">🛡️</div><div class="tdname">Safety</div><div class="tddesc">harmful content &amp; jailbreak</div></div>
        <div class="tdc"><div class="tdico">⚖️</div><div class="tdname">Fairness</div><div class="tddesc">demographic bias &amp; toxicity</div></div>
        <div class="tdc"><div class="tdico">🔒</div><div class="tdname">Privacy</div><div class="tddesc">PII leakage &amp; data handling</div></div>
        <div class="tdc"><div class="tdico">🧪</div><div class="tdname">Robustness</div><div class="tddesc">adversarial &amp; prompt injection</div></div>
        <div class="tdc"><div class="tdico">🧭</div><div class="tdname">Ethics</div><div class="tddesc">responsible AI principles</div></div>
      </div>
    </div>
  </div>

  <!-- SLIDE 4: Leaderboard -->
  <div class="slide">
    <div class="tour-hdr">
      <div class="tour-logo"><span class="mk">T</span>TrustLLM</div>
      <button class="skip-btn" onclick="done()">Skip tour</button>
    </div>
    <div class="dots" id="dots4"></div>
    <div class="slide-body">
      <p class="eyebrow sl-enter"><span class="ldot"></span>Step 4 of 5</p>
      <h2 class="tour-h sl-enter sl-d1">Compare models head-to-head.</h2>
      <p class="tour-lead sl-enter sl-d2">The leaderboard aggregates all runs into a ranked Trust Score. See exactly where each model excels and where it fails.</p>
      <div class="mini-lb sl-enter sl-d3">
        <div class="lb-head"><span>#</span><span>Model</span><span>Trust Score</span><span class="hd">Halluc.</span><span class="hp">Safety</span></div>
        <div class="lb-row"><span class="rank r1">1</span><div><div class="mname">Llama 3.3 70B</div><div class="mprov">Groq</div></div><span class="trust">87.4</span><span class="badge good hd">Low</span><span class="badge good hp">Pass</span></div>
        <div class="lb-row"><span class="rank">2</span><div><div class="mname">GPT-4o</div><div class="mprov">OpenAI</div></div><span class="trust">84.1</span><span class="badge good hd">Low</span><span class="badge med hp">Review</span></div>
        <div class="lb-row"><span class="rank">3</span><div><div class="mname">Claude 3.5 Sonnet</div><div class="mprov">Anthropic</div></div><span class="trust">82.9</span><span class="badge med hd">Med</span><span class="badge good hp">Pass</span></div>
        <div class="lb-row"><span class="rank">4</span><div><div class="mname">Gemini 2.0 Flash</div><div class="mprov">Google</div></div><span class="trust">79.3</span><span class="badge med hd">Med</span><span class="badge med hp">Review</span></div>
      </div>
      <p style="font-size:.72rem;color:var(--gray);margin-top:.65rem">Sample data — run evaluations to populate your own leaderboard</p>
    </div>
  </div>

  <!-- SLIDE 5: Ready -->
  <div class="slide" style="justify-content:center">
    <div class="tour-hdr">
      <div class="tour-logo"><span class="mk">T</span>TrustLLM</div>
      <button class="skip-btn" onclick="done()">Skip</button>
    </div>
    <div class="slide-body" style="display:flex;align-items:center;justify-content:center">
      <div class="ready-card sl-enter">
        <div style="font-size:2.5rem;margin-bottom:1rem">🛡️</div>
        <h3>Your dashboard is ready.</h3>
        <p>Run your first evaluation, explore the leaderboard, or test your RAG pipeline — everything you need to trust your LLMs is here.</p>
        <div class="quick-links">
          <a class="qlink" href="?page=Run+Evaluation">▶ Run Evaluation</a>
          <a class="qlink" href="?page=Leaderboard">🏆 Leaderboard</a>
          <a class="qlink" href="?page=Overview">📊 Overview</a>
          <a class="qlink" href="?page=RAG+Testing">📚 RAG Testing</a>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- Nav bar -->
<div class="tour-nav" id="tnav">
  <button class="nav-back" id="btnBack" onclick="prev()" style="visibility:hidden">← Back</button>
  <button class="nav-next" id="btnNext" onclick="next()">Next →</button>
</div>

<script>
var R=matchMedia('(prefers-reduced-motion:reduce)').matches;
var cur=0,total=5;
var track=document.getElementById('track');
var btnBack=document.getElementById('btnBack');
var btnNext=document.getElementById('btnNext');

// Build dots in each slide header
['dots','dots2','dots3','dots4'].forEach(function(id,si){
  var el=document.getElementById(id);
  if(!el)return;
  for(var i=0;i<total;i++){
    var d=document.createElement('div');
    d.className='dot'+(i===si+0?' on':'');
    el.appendChild(d);
  }
});
// Rebuild dots dynamically
function updateDots(){
  document.querySelectorAll('.dots').forEach(function(el){
    [].slice.call(el.children).forEach(function(d,i){
      d.className='dot'+(i===cur?' on':'');
    });
  });
}

function goTo(n){
  n=Math.max(0,Math.min(n,total-1));
  cur=n;
  track.style.transform='translateX(-'+(cur*100)+'vw)';
  btnBack.style.visibility=cur===0?'hidden':'visible';
  if(cur===total-1){
    btnNext.style.display='none';
    document.getElementById('tnav').insertAdjacentHTML('beforeend','<button class="nav-done" onclick="done()">Start using TrustLLM →</button>');
  } else {
    btnNext.style.display='';
    var doneBtn=document.querySelector('.nav-done');
    if(doneBtn)doneBtn.remove();
  }
  updateDots();
  // re-trigger bar fills on slide 2
  if(cur===1){
    setTimeout(function(){
      document.querySelectorAll('.dfill').forEach(function(el){
        el.style.width=(el.dataset.w||0)+'%';
      });
    },R?0:400);
  }
  // re-run count-ups on slide 1
  if(cur===0){
    document.querySelectorAll('.cnt').forEach(function(el){
      el.textContent=el.dataset.to+(el.dataset.sfx||'');
    });
    setTimeout(function(){document.querySelectorAll('.cnt').forEach(countUp);},R?0:300);
  }
}
function next(){goTo(cur+1);}
function prev(){goTo(cur-1);}
function done(){
  // Click the native Streamlit "Start using TrustLLM" button to set session state
  try{
    var btns=window.parent.document.querySelectorAll('[data-testid="stButton"] button');
    for(var i=0;i<btns.length;i++){
      if(btns[i].innerText.indexOf('TrustLLM')>=0||btns[i].innerText.indexOf('Start')>=0){
        btns[i].click();return;
      }
    }
    // Fallback: click any visible button in the parent
    if(btns.length>0)btns[0].click();
  }catch(e){}
}

// Count-up
function countUp(el){
  if(R){el.textContent=el.dataset.to+(el.dataset.sfx||'');return;}
  var to=+el.dataset.to,sfx=el.dataset.sfx||'',s=null,dur=900;
  requestAnimationFrame(function f(t){
    if(!s)s=t;var p=Math.min((t-s)/dur,1),e=1-Math.pow(1-p,3);
    el.textContent=Math.round(e*to)+sfx;if(p<1)requestAnimationFrame(f);
  });
}
setTimeout(function(){document.querySelectorAll('.cnt').forEach(countUp);},R?0:500);

// Score bar fill (slide 2)
setTimeout(function(){
  document.querySelectorAll('.dfill').forEach(function(el){
    el.style.width=(el.dataset.w||0)+'%';
  });
},R?0:800);

// macOS dock on slide 3
(function(){
  if(R)return;
  var dock=document.getElementById('tdock');
  if(!dock)return;
  var cards=[].slice.call(dock.querySelectorAll('.tdc'));
  var MAX=1.35,RANGE=160,LIFT=18;
  dock.addEventListener('mousemove',function(ev){
    cards.forEach(function(c){
      var r=c.getBoundingClientRect();
      var cx=r.left+r.width/2;
      var d=Math.abs(ev.clientX-cx);
      var f=Math.max(0,1-d/RANGE);
      var px=(ev.clientX-r.left)/r.width-.5;
      var py=(ev.clientY-r.top)/r.height-.5;
      c.style.transform='translateY(-'+(LIFT*f)+'px) scale('+(1+(MAX-1)*f)+') perspective(600px) rotateY('+(px*14)+'deg) rotateX('+((-py)*14)+'deg)';
      c.style.zIndex=Math.round(f*10);
      c.style.borderColor=f>.4?'#E8290B':'';
    });
  });
  dock.addEventListener('mouseleave',function(){
    cards.forEach(function(c){c.style.transform='';c.style.zIndex='';c.style.borderColor='';});
  });
})();

// Keyboard nav
document.addEventListener('keydown',function(e){
  if(e.key==='ArrowRight'||e.key==='Enter')next();
  else if(e.key==='ArrowLeft')prev();
  else if(e.key==='Escape')done();
});

// Listen for tour-done from parent (if any)
try{
  window.parent.addEventListener('message',function(e){
    if(e.data&&e.data.type==='tl-tour-complete')done();
  });
}catch(ex){}

// Init
updateDots();
</script>
</body>
</html>"""


def _show_tour() -> None:
    import streamlit.components.v1 as _components
    _components.html(_TOUR_HTML, height=700, scrolling=False)
    st.markdown("""
        <style>
        section.main .block-container{padding:0!important;max-width:100%!important;}
        [data-testid="stMain"],[data-testid="stMainBlockContainer"],[data-testid="stAppViewBlockContainer"]{
            width:100%!important;max-width:100%!important;padding:0!important;}
        </style>
    """, unsafe_allow_html=True)
    if st.button("Start using TrustLLM →", use_container_width=True, type="primary", key="tour_finish"):
        st.session_state["tour_done"] = True
        st.rerun()


# Auth gate
# -----------------------------------------------------------------------
if not st.session_state.get("logged_in"):
    _show_login()
    st.stop()

# Show feature tour once after first login
if not st.session_state.get("tour_done"):
    _show_tour()
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
from ui_pages.experiments       import render as rag_debugger
from ui_pages.prompt_dataset    import render as prompt_dataset
from ui_pages.failure_analysis  import render as failure_analysis
from ui_pages.profile           import render as profile_page
from ui_pages.api_keys          import render as api_keys_page
from ui_pages.query_history     import render as query_history_page
from ui_pages.methodology       import render as methodology

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
        ("🧪", "RAG Debugger"),
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
    "LEARN": [
        ("📖", "Methodology"),
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
# Quick API-key paste (TrustLLM Pro BYOK)
# Per-provider "get your key" links now live on the Bring Your Own Key page.
# -----------------------------------------------------------------------
from llm_runner.providers import PROVIDERS as _PRO_PROVIDERS  # noqa: E402

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
    "RAG Debugger":      rag_debugger,
    "Prompt Dataset":    prompt_dataset,
    "Failure Analysis":  failure_analysis,
    "Query History":     query_history_page,
    "Profile":           profile_page,
    "API Keys":          api_keys_page,
    "Methodology":       methodology,
}

_routes.get(page, overview)()
