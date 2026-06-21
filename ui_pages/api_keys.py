"""
ui_pages/api_keys.py — TrustLLM "Bring Your Own Key"
=====================================================
Vercel-AI-Gateway-style provider list: each provider is a dark row with a
circular logo, name + connection status, and an Add / Manage action (a popover
holding the key input). Keys are encrypted at rest via auth/api_keys.py and
never leave this TrustLLM instance — they travel only to the provider you call.
"""

import sys
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from auth.api_keys import (
    clear_key,
    encryption_configured,
    has_key,
    set_key,
)
from llm_runner.providers import PROVIDERS


# -----------------------------------------------------------------------
# Provider logos — circular badges (inline SVG / emoji / monogram).
# Kept here (not in providers.py) so the registry stays presentation-free.
# -----------------------------------------------------------------------
_LOGOS = {
    "claude": {"bg": "#ffffff", "svg": (
        "<svg width='24' height='24' viewBox='0 0 24 24' fill='#CC785C'>"
        "<path d='M12 2l1.7 6.1L20 6l-4.4 5L22 12.9l-6.7.2L17 19l-5-3.5L7 19l1.7-5.9"
        "L2 12.9 8.4 11 4 6l6.3 2.1z'/></svg>")},
    "gpt": {"bg": "#000000", "svg": (
        "<svg width='24' height='24' viewBox='0 0 24 24' fill='#ffffff'>"
        "<circle cx='12' cy='4' r='2'/><circle cx='19' cy='8' r='2'/>"
        "<circle cx='19' cy='16' r='2'/><circle cx='12' cy='20' r='2'/>"
        "<circle cx='5' cy='16' r='2'/><circle cx='5' cy='8' r='2'/></svg>")},
    "gemini": {"bg": "#ffffff", "svg": (
        "<svg width='26' height='26' viewBox='0 0 24 24'><defs>"
        "<linearGradient id='gem' x1='0' x2='1' y1='0' y2='1'>"
        "<stop offset='0' stop-color='#4796E3'/><stop offset='.5' stop-color='#9177C7'/>"
        "<stop offset='1' stop-color='#D56F9D'/></linearGradient></defs>"
        "<path d='M12 1c.5 5.7 5.3 10.5 11 11-5.7.5-10.5 5.3-11 11-.5-5.7-5.3-10.5-11-11"
        "C6.7 11.3 11.5 6.7 12 1z' fill='url(#gem)'/></svg>")},
    "mistral": {"bg": "#ffffff", "svg": (
        "<svg width='24' height='24' viewBox='0 0 24 24'>"
        "<rect x='3' y='4' width='18' height='3.3' fill='#FFD000'/>"
        "<rect x='3' y='9' width='18' height='3.3' fill='#FF8205'/>"
        "<rect x='3' y='14' width='18' height='3.3' fill='#FA500F'/>"
        "<rect x='3' y='19' width='18' height='1.9' fill='#E10500'/></svg>")},
    "phi": {"bg": "#FFD21E", "emoji": "\U0001F917"},
    "together": {"bg": "#1668FF", "letter": "T", "fg": "#ffffff"},
    "fireworks": {"bg": "#5019C5", "svg": (
        "<svg width='24' height='24' viewBox='0 0 24 24' stroke='#fff' stroke-width='2' "
        "stroke-linecap='round'><path d='M12 3v5M12 16v5M3 12h5M16 12h5M6 6l3 3M15 15l3 3"
        "M18 6l-3 3M9 15l-3 3'/></svg>")},
    "cerebras": {"bg": "#F4694B", "letter": "C", "fg": "#ffffff"},
}


def _logo_html(provider_id: str) -> str:
    spec = _LOGOS.get(provider_id, {"bg": "#27272a", "letter": "?", "fg": "#fff"})
    if "emoji" in spec:
        inner = f"<span style='font-size:24px;line-height:1'>{spec['emoji']}</span>"
    elif "svg" in spec:
        inner = spec["svg"]
    else:
        inner = (f"<span style='color:{spec.get('fg', '#fff')};font-weight:700;"
                 f"font-size:20px'>{spec['letter']}</span>")
    return f"<div class='byok-logo' style='background:{spec['bg']}'>{inner}</div>"


_PAGE_CSS = """
<style>
/* Circular provider logo */
.byok-row{display:flex;align-items:center;gap:15px;}
.byok-logo{width:46px;height:46px;flex:0 0 46px;border-radius:50%;display:flex;align-items:center;
  justify-content:center;overflow:hidden;box-shadow:0 0 0 1px rgba(255,255,255,.06);}
.byok-name{font-weight:600;font-size:1.02rem;color:#fafafa;line-height:1.2;}
.byok-sub{font-size:.8rem;margin-top:3px;}
.byok-on{color:#22c55e;font-weight:600;}
.byok-off{color:#8b8b94;}
/* Each provider row → a dark Vercel-style card (scoped via :has to rows only) */
[data-testid="stHorizontalBlock"]:has(.byok-name){
  background:#0b0b0d;border:1px solid #1f1f25;border-radius:12px;
  padding:12px 20px;margin-bottom:10px;align-items:center;
  transition:background .15s ease,border-color .15s ease;}
[data-testid="stHorizontalBlock"]:has(.byok-name):hover{
  background:#16161a;border-color:#2e2e37;}
/* Add / Manage button (popover trigger) → outline pill */
[data-testid="stPopover"] button{
  background:transparent!important;border:1px solid #3f3f46!important;color:#fafafa!important;
  border-radius:8px!important;font-weight:600!important;font-size:.88rem!important;padding:.4rem 1.1rem!important;}
[data-testid="stPopover"] button:hover{background:#27272a!important;border-color:#6b6b76!important;}
</style>
"""


def _provider_row(provider_id: str, meta: dict):
    saved = has_key(provider_id)
    c_main, c_action = st.columns([8, 2], vertical_alignment="center")
    with c_main:
        status = ("<span class='byok-on'>● Connected</span>" if saved
                  else "<span class='byok-off'>Not connected</span>")
        st.markdown(
            f"<div class='byok-row'>{_logo_html(provider_id)}"
            f"<div><div class='byok-name'>{meta['display_name']}</div>"
            f"<div class='byok-sub'>{status}</div></div></div>",
            unsafe_allow_html=True,
        )
    with c_action:
        with st.popover("Manage" if saved else "Add", use_container_width=True):
            st.markdown(f"**{meta['display_name']}**")
            st.caption("Models: " + " · ".join(n for n, _ in meta["models"]))
            st.markdown(f"[Get your API key →]({meta['api_key_url']})")
            value = st.text_input(
                f"API key for {meta['display_name']}",
                type="password",
                placeholder=("•" * 20 if saved else meta["key_prefix_hint"]),
                key=f"byok_in_{provider_id}",
                label_visibility="collapsed",
            )
            b_save, b_clear = st.columns(2)
            with b_save:
                if st.button("Save", key=f"byok_save_{provider_id}", type="primary",
                             disabled=not value.strip(), use_container_width=True):
                    if set_key(provider_id, value.strip()):
                        st.success("Key saved (encrypted).")
                        st.rerun()
                    else:
                        st.error("Set `API_KEYS_ENCRYPTION_KEY` in secrets.")
            with b_clear:
                if st.button("Remove", key=f"byok_clear_{provider_id}",
                             disabled=not saved, use_container_width=True):
                    clear_key(provider_id)
                    st.toast(f"{meta['display_name']} key removed.", icon="🗑")
                    st.rerun()


def render():
    st.markdown(_PAGE_CSS, unsafe_allow_html=True)
    st.title("Bring Your Own Key")
    st.caption(
        "Connect your provider API keys to run real cloud-model evaluations. "
        "Keys are encrypted at rest and only ever sent to the provider you call."
    )

    if not encryption_configured():
        st.error(
            "⚠️ **Encryption not configured.** Add `API_KEYS_ENCRYPTION_KEY` to your "
            "Streamlit secrets to enable persistent key storage — without it, Save won't work."
        )
        with st.expander("How to generate an encryption key"):
            st.markdown(
                "Run this and paste the output into Streamlit secrets:\n"
                "```bash\n"
                "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"\n"
                "```\n"
                "```toml\n"
                "API_KEYS_ENCRYPTION_KEY = \"<paste-here>\"\n"
                "```"
            )
        return

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    for provider_id, meta in PROVIDERS.items():
        _provider_row(provider_id, meta)
