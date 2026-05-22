"""
ui_pages/api_keys.py — TrustLLM Pro API Keys settings
=======================================================
Per-provider input fields for Claude, GPT, Gemini, Mistral, and Phi.
Keys are encrypted at rest via auth/api_keys.py and never leave this
TrustLLM instance — they travel only to the model provider you select.
"""

import sys
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from auth.api_keys import (
    clear_key,
    encryption_configured,
    get_key,
    has_key,
    set_key,
)
from llm_runner.providers import PROVIDERS


# -----------------------------------------------------------------------
# Per-provider block
# -----------------------------------------------------------------------

def _provider_block(provider_id: str, meta: dict):
    """Render one provider's status, get-key link, input, save/clear buttons."""
    display = meta["display_name"]
    url = meta["api_key_url"]
    hint = meta["key_prefix_hint"]
    models = meta["models"]

    saved = has_key(provider_id)

    with st.container(border=True):
        # Title row + status + get-key link
        col_title, col_status, col_link = st.columns([3, 1, 2])
        with col_title:
            st.markdown(f"#### {display}")
        with col_status:
            if saved:
                st.markdown(
                    "<span style='color:#22c55e;font-weight:600;'>✓ Saved</span>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    "<span style='color:#64748b;'>⊘ No key</span>",
                    unsafe_allow_html=True,
                )
        with col_link:
            st.markdown(f"🔑 [Get your own key →]({url})")

        model_names = " · ".join(name for name, _ in models)
        st.caption(f"Supported models: {model_names}")

        # Input — masked dots if saved, empty otherwise
        placeholder = "•" * 24 if saved else hint
        new_value = st.text_input(
            f"API key for {display}",
            type="password",
            placeholder=placeholder,
            key=f"input_{provider_id}",
            label_visibility="collapsed",
        )

        # Action buttons
        col_save, col_clear, _ = st.columns([1, 1, 4])
        with col_save:
            disabled = not new_value.strip()
            if st.button("Save", key=f"save_{provider_id}", type="primary", disabled=disabled):
                if set_key(provider_id, new_value.strip()):
                    st.success(f"✓ {display} key saved (encrypted).")
                    st.rerun()
                else:
                    st.error("Couldn't save — check that `API_KEYS_ENCRYPTION_KEY` is set in Streamlit secrets.")
        with col_clear:
            if st.button("Clear", key=f"clear_{provider_id}", disabled=not saved):
                clear_key(provider_id)
                st.toast(f"{display} key removed.", icon="🗑")
                st.rerun()


# -----------------------------------------------------------------------
# Main render
# -----------------------------------------------------------------------

def render():
    st.title("🔑 API Keys")
    st.caption(
        "Bring your own API keys to unlock real cloud-model evaluations in TrustLLM Pro. "
        "Each provider links to where you get a key."
    )
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    if not encryption_configured():
        st.error(
            "⚠️ **Encryption not configured.** Add `API_KEYS_ENCRYPTION_KEY` to your "
            "Streamlit Cloud secrets to enable persistent API key storage. Without this, "
            "the Save button won't work."
        )
        with st.expander("How to generate an encryption key"):
            st.markdown(
                "Pick **one** of these:\n\n"
                "1. **Recommended** — run this in a terminal:\n"
                "   ```bash\n"
                "   python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"\n"
                "   ```\n"
                "   Copy the output into Streamlit Cloud → Settings → Secrets as:\n"
                "   ```toml\n"
                "   API_KEYS_ENCRYPTION_KEY = \"<paste-the-key-here>\"\n"
                "   ```\n\n"
                "2. **Quick & dirty** — set any passphrase ≥ 16 chars. TrustLLM will SHA-256 it. "
                "Lose the passphrase = lose all stored keys.\n"
            )
        return

    st.info(
        "🔒 Keys are **encrypted at rest** with Fernet (AES-128) and stored per-user. "
        "They never leave this TrustLLM instance except when calling the model provider you selected. "
        "Click **Clear** anytime to remove a key."
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # One block per provider
    for provider_id, meta in PROVIDERS.items():
        _provider_block(provider_id, meta)
        st.markdown("<br>", unsafe_allow_html=True)
