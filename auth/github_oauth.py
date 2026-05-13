"""
auth/github_oauth.py — GitHub OAuth 2.0 helpers for TrustLLM.

Flow:
    1. get_auth_url(state) → redirect browser to GitHub
    2. GitHub redirects back to OAUTH_REDIRECT_URI with ?code=...&state=...
    3. exchange_code(code) → normalised { id, name, email, picture }

Secrets (Streamlit secrets or env vars):
    GITHUB_CLIENT_ID
    GITHUB_CLIENT_SECRET
    OAUTH_REDIRECT_URI
"""

import os
import secrets as _secrets

from authlib.integrations.requests_client import OAuth2Session

_AUTHORIZATION_URL = "https://github.com/login/oauth/authorize"
_TOKEN_URL         = "https://github.com/login/oauth/access_token"
_USERINFO_URL      = "https://api.github.com/user"
_EMAILS_URL        = "https://api.github.com/user/emails"


def _secret(key: str, default: str = "") -> str:
    """Read from Streamlit secrets first, then env vars."""
    try:
        import streamlit as st
        return st.secrets.get(key, os.getenv(key, default))
    except Exception:
        return os.getenv(key, default)


def is_configured() -> bool:
    return bool(_secret("GITHUB_CLIENT_ID") and _secret("GITHUB_CLIENT_SECRET"))


def generate_state() -> str:
    return _secrets.token_urlsafe(24)


def get_auth_url(state: str) -> str:
    """Return the GitHub OAuth authorization URL."""
    client = OAuth2Session(
        client_id=_secret("GITHUB_CLIENT_ID"),
        redirect_uri=_secret("OAUTH_REDIRECT_URI", "http://localhost:8501"),
        scope="user:email read:user",
    )
    url, _ = client.create_authorization_url(_AUTHORIZATION_URL, state=state)
    return url


def exchange_code(code: str) -> dict:
    """
    Exchange authorization code for GitHub user info.
    Returns normalised dict: { id, name, email, picture }
    """
    redirect_uri = _secret("OAUTH_REDIRECT_URI", "http://localhost:8501")
    client = OAuth2Session(
        client_id=_secret("GITHUB_CLIENT_ID"),
        client_secret=_secret("GITHUB_CLIENT_SECRET"),
        redirect_uri=redirect_uri,
    )
    client.fetch_token(
        _TOKEN_URL,
        code=code,
        headers={"Accept": "application/json"},
    )

    resp = client.get(_USERINFO_URL, headers={"Accept": "application/vnd.github+json"})
    resp.raise_for_status()
    raw = resp.json()

    # GitHub user endpoint may return null email — fetch verified primary separately
    email = raw.get("email") or ""
    if not email:
        try:
            er = client.get(_EMAILS_URL, headers={"Accept": "application/vnd.github+json"})
            if er.ok:
                emails = er.json()
                primary = next(
                    (e["email"] for e in emails if e.get("primary") and e.get("verified")),
                    None,
                )
                email = primary or (emails[0]["email"] if emails else "")
        except Exception:
            pass

    return {
        "id":      f"github:{raw.get('id', '')}",
        "name":    raw.get("name") or raw.get("login", "User"),
        "email":   email,
        "picture": raw.get("avatar_url", ""),
    }
