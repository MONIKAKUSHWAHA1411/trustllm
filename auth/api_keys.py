"""
auth/api_keys.py — TrustLLM Pro BYOK (Bring Your Own Key) storage
===================================================================
Persists per-user API keys for cloud model providers (Claude, GPT, Gemini,
Mistral, Phi/HuggingFace), encrypted at rest with Fernet (AES-128-CBC + HMAC).

Encryption
----------
The encryption secret is read from:
  1. Streamlit secret `API_KEYS_ENCRYPTION_KEY`, or
  2. Environment variable `API_KEYS_ENCRYPTION_KEY`.

Accepted formats:
  • A raw Fernet key (44-char URL-safe base64), or
  • Any passphrase (we hash it to derive a key).

If the secret is rotated, all stored keys become unreadable — that's the
expected behaviour and forces users to re-enter their keys.

Storage layout
--------------
Encrypted blob per user at:
    data/api_keys/{safe_user_id}.enc

The file contains a JSON dict { provider: key } encrypted as a single blob.
"""

import base64
import hashlib
import json
import os
from pathlib import Path
from typing import Dict, Optional

import streamlit as st

BASE_DIR = Path(__file__).resolve().parents[1]
KEYS_DIR = BASE_DIR / "data" / "api_keys"

SUPPORTED_PROVIDERS = ("claude", "gpt", "gemini", "mistral", "phi")

_SESSION_CACHE_KEY = "_api_keys_cache"


# -----------------------------------------------------------------------
# Encryption helpers
# -----------------------------------------------------------------------

def _read_encryption_secret() -> str:
    """Read the encryption secret from Streamlit secrets or env. Empty if unset."""
    try:
        secret = st.secrets.get("API_KEYS_ENCRYPTION_KEY", os.getenv("API_KEYS_ENCRYPTION_KEY", ""))
    except Exception:
        secret = os.getenv("API_KEYS_ENCRYPTION_KEY", "")
    return secret or ""


def encryption_configured() -> bool:
    """True iff an encryption secret is configured."""
    return bool(_read_encryption_secret())


def _fernet():
    """Return a configured Fernet instance, or None if unavailable."""
    secret = _read_encryption_secret()
    if not secret:
        return None
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        return None

    # If the secret is already a valid Fernet key, use it directly.
    try:
        return Fernet(secret.encode())
    except Exception:
        pass

    # Otherwise, derive a 32-byte key from the passphrase via SHA-256.
    derived = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
    return Fernet(derived)


# -----------------------------------------------------------------------
# Per-user file paths
# -----------------------------------------------------------------------

def _safe_user_id() -> str:
    user = st.session_state.get("user", {}) or {}
    raw = user.get("id") or user.get("username") or "anonymous"
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in str(raw))


def _user_keys_path() -> Path:
    KEYS_DIR.mkdir(parents=True, exist_ok=True)
    return KEYS_DIR / f"{_safe_user_id()}.enc"


# -----------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------

def load_keys() -> Dict[str, str]:
    """Load all API keys for the current user. Returns {} on any failure."""
    cached = st.session_state.get(_SESSION_CACHE_KEY)
    if cached is not None:
        return cached

    fernet = _fernet()
    path = _user_keys_path()
    if not fernet or not path.exists():
        return {}

    try:
        decrypted = fernet.decrypt(path.read_bytes())
        keys = json.loads(decrypted.decode())
        if not isinstance(keys, dict):
            return {}
    except Exception:
        # Corrupted blob, wrong key, etc. — refuse silently to avoid leaking info.
        return {}

    st.session_state[_SESSION_CACHE_KEY] = keys
    return keys


def save_keys(keys: Dict[str, str]) -> bool:
    """Encrypt and persist all keys for the current user."""
    fernet = _fernet()
    if not fernet:
        return False

    # Drop empty values, keep only supported providers
    clean = {p: v.strip() for p, v in keys.items() if v and p in SUPPORTED_PROVIDERS}

    try:
        encrypted = fernet.encrypt(json.dumps(clean).encode())
        _user_keys_path().write_bytes(encrypted)
    except Exception:
        return False

    st.session_state[_SESSION_CACHE_KEY] = clean
    return True


def get_key(provider: str) -> Optional[str]:
    """Return the stored API key for a provider, or None."""
    return load_keys().get(provider)


def has_key(provider: str) -> bool:
    """True iff the current user has a key stored for this provider."""
    return bool(get_key(provider))


def set_key(provider: str, key: str) -> bool:
    """Set/update one provider's key. Returns True on success."""
    if provider not in SUPPORTED_PROVIDERS:
        return False
    keys = dict(load_keys())
    keys[provider] = key
    return save_keys(keys)


def clear_key(provider: str) -> bool:
    """Remove one provider's key. Returns True on success."""
    keys = dict(load_keys())
    keys.pop(provider, None)
    return save_keys(keys)
