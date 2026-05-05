"""
auth/supabase_auth.py — Supabase OAuth helpers for TrustLLM.

Flow (Streamlit-compatible):
    1. Call get_auth_url() → redirect the browser to Supabase (Google provider).
    2. Supabase redirects back to REDIRECT_URI with ?code=...
    3. Streamlit reloads; detect st.query_params["code"].
    4. Call exchange_code(code) → returns normalised user_info dict.

Environment variables (set in .env or .streamlit/secrets.toml):
    SUPABASE_URL
    SUPABASE_KEY           (anon/public key)
    OAUTH_REDIRECT_URI     (default: http://localhost:8501)
"""

import os


def _secret(key: str, default: str = "") -> str:
    """Read from Streamlit secrets first, fall back to env vars."""
    try:
        import streamlit as st
        return st.secrets.get(key, os.getenv(key, default))
    except Exception:
        return os.getenv(key, default)


def is_configured() -> bool:
    """Return True when Supabase credentials are present."""
    return bool(_secret("SUPABASE_URL") and _secret("SUPABASE_KEY"))


def _get_client():
    """Return a Supabase client instance."""
    from supabase import create_client
    return create_client(
        _secret("SUPABASE_URL"),
        _secret("SUPABASE_KEY"),
    )


def get_auth_url() -> str:
    """Build the Supabase OAuth URL (Google provider) to redirect the user to."""
    client = _get_client()
    redirect_uri = _secret("OAUTH_REDIRECT_URI", "http://localhost:8501")
    resp = client.auth.sign_in_with_oauth({
        "provider": "google",
        "options": {
            "redirect_to": redirect_uri,
        },
    })
    return resp.url


def exchange_code(code: str) -> dict:
    """
    Exchange the authorisation code for a Supabase session,
    and return a normalised user dict: { id, name, email, picture }.
    """
    client = _get_client()
    session = client.auth.exchange_code_for_session({"auth_code": code})
    user = session.user

    meta = user.user_metadata or {}
    return {
        "id":      user.id,
        "name":    meta.get("full_name", meta.get("name", "User")),
        "email":   user.email or meta.get("email", ""),
        "picture": meta.get("avatar_url", meta.get("picture", "")),
    }
