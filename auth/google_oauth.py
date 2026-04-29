"""
auth/google_oauth.py — Google OAuth 2.0 helpers for TrustLLM.

Flow (Streamlit-compatible):
    1. Call get_auth_url() → redirect the browser to Google.
    2. Google redirects back to REDIRECT_URI with ?code=...
    3. Streamlit reloads; detect st.query_params["code"].
    4. Call exchange_code(code) → returns normalised user_info dict.

Environment variables (set in .env or .streamlit/secrets.toml):
    GOOGLE_CLIENT_ID
    GOOGLE_CLIENT_SECRET
    OAUTH_REDIRECT_URI   (default: http://localhost:8501)
"""

import os
import secrets

from authlib.integrations.requests_client import OAuth2Session

GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
REDIRECT_URI         = os.getenv("OAUTH_REDIRECT_URI", "http://localhost:8501")

_AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_URL         = "https://oauth2.googleapis.com/token"
_USERINFO_URL      = "https://www.googleapis.com/oauth2/v3/userinfo"


def is_configured() -> bool:
    """Return True when Google credentials are present in the environment."""
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)


def generate_state() -> str:
    return secrets.token_urlsafe(24)


def get_auth_url(state: str) -> str:
    """Build the Google authorisation URL to redirect the user to."""
    client = OAuth2Session(
        client_id=GOOGLE_CLIENT_ID,
        redirect_uri=REDIRECT_URI,
        scope="openid email profile",
    )
    url, _ = client.create_authorization_url(
        _AUTHORIZATION_URL,
        state=state,
        access_type="offline",
        prompt="select_account",
    )
    return url


def exchange_code(code: str) -> dict:
    """
    Exchange the authorisation code for tokens, fetch user-info from Google,
    and return a normalised dict:
        { id, name, email, picture }
    """
    client = OAuth2Session(
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
    )
    client.fetch_token(_TOKEN_URL, code=code)
    resp = client.get(_USERINFO_URL)
    resp.raise_for_status()
    raw = resp.json()

    return {
        "id":      raw.get("sub", raw.get("id", "")),
        "name":    raw.get("name", raw.get("given_name", "User")),
        "email":   raw.get("email", ""),
        "picture": raw.get("picture", ""),
    }
