"""Resend-backed email delivery for TrustLLM.

send_welcome_email_async() fires a daemon thread so it never blocks the login
flow. The caller is responsible for marking welcome_email_sent=True in the
user store BEFORE calling this function — that's what prevents duplicate sends
if Streamlit re-runs the script.
"""

import logging
import os
import threading

from .email_template import get_welcome_html, get_welcome_text

logger = logging.getLogger(__name__)


def _secret(key: str, default: str = "") -> str:
    """Read from Streamlit secrets first, fall back to env vars.

    Streamlit Cloud only exposes secrets via st.secrets (not os.environ),
    so we must check st.secrets first. Local dev can still use env vars.
    """
    try:
        import streamlit as st
        return st.secrets.get(key, os.getenv(key, default))
    except Exception:
        return os.getenv(key, default)


def _deliver(to_email: str, display_name: str) -> bool:
    """Send via Resend SDK. Returns True on success."""
    try:
        import resend  # imported here so the app starts without resend installed

        api_key = _secret("RESEND_API_KEY", "")
        if not api_key:
            logger.error("RESEND_API_KEY is not set — skipping welcome email")
            return False

        resend.api_key = api_key
        from_addr = _secret("EMAIL_FROM", "monikakushwaha@trustllm.site")

        params: resend.Emails.SendParams = {
            "from": from_addr,
            "to": [to_email],
            "subject": "Welcome to TrustLLM 🚀",
            "html": get_welcome_html(display_name),
            "text": get_welcome_text(display_name),
        }

        result = resend.Emails.send(params)
        logger.info("Welcome email delivered to %s (Resend id=%s)", to_email, result.get("id"))
        return True

    except Exception:
        logger.exception("Failed to send welcome email to %s", to_email)
        return False


def send_welcome_email_async(to_email: str, display_name: str = "") -> threading.Thread:
    """
    Dispatch the welcome email on a background daemon thread.

    The caller must have already marked welcome_email_sent=True in the user
    store before calling this. That optimistic write prevents duplicate sends
    even if the Streamlit script re-runs before the thread completes.
    """
    def _worker():
        _deliver(to_email, display_name)

    t = threading.Thread(target=_worker, daemon=True, name="welcome-email")
    t.start()
    return t


def send_welcome_email_sync(to_email: str, display_name: str = "") -> bool:
    """Blocking send — useful for testing or CLI scripts."""
    return _deliver(to_email, display_name)


def send_welcome_email_with_result(to_email: str, display_name: str = "") -> tuple:
    """Sync send that returns (success: bool, message: str) for UI display.

    Surfaces the exact failure reason (missing key, Resend rejection, etc.)
    so it can be shown to the user during signup. Unlike _deliver, this does
    not swallow exceptions — it captures the message for the caller.
    """
    try:
        import resend  # lazy import; app must start even if resend isn't installed
    except Exception as e:
        return False, f"resend package not importable: {type(e).__name__}: {e}"

    api_key = _secret("RESEND_API_KEY", "")
    if not api_key:
        return False, "RESEND_API_KEY is not set in Streamlit secrets"

    resend.api_key = api_key
    from_addr = _secret("EMAIL_FROM", "monikakushwaha@trustllm.site")

    try:
        result = resend.Emails.send({
            "from": from_addr,
            "to": [to_email],
            "subject": "Welcome to TrustLLM 🚀",
            "html": get_welcome_html(display_name),
            "text": get_welcome_text(display_name),
        })
        rid = result.get("id") if isinstance(result, dict) else getattr(result, "id", "?")
        return True, f"Email queued via Resend (id={rid}, from={from_addr})"
    except Exception as e:
        return False, f"Resend rejected send (from={from_addr}): {type(e).__name__}: {e}"
