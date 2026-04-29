"""
app.py — TrustLLM main entry point.

Auth flow:
    1. Local .env / st.secrets checked for GOOGLE_CLIENT_ID.
    2. If Google credentials present  → show "Sign in with Google" button.
    3. If Google redirects back with ?code= → exchange for user info.
    4. Fall-back username/password login always available.
    5. All authenticated users are upserted into SQLite (db/database.py).
"""

import json
import os
from pathlib import Path

import streamlit as st

# Load .env before anything else touches os.getenv
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

from db.database import init_db, upsert_user, touch_user
from auth.google_oauth import is_configured, generate_state, get_auth_url, exchange_code

BASE_DIR = Path(__file__).resolve().parent

# Ensure DB schema exists on every cold start
init_db()

# -----------------------------------------------------------------------
# Page config  (must be first Streamlit call)
# -----------------------------------------------------------------------
st.set_page_config(
    page_title="TrustLLM",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------
# CSS
# -----------------------------------------------------------------------
def _load_css() -> None:
    with open(BASE_DIR / "style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

_load_css()

# -----------------------------------------------------------------------
# Local-user helpers (username/password fallback)
# -----------------------------------------------------------------------
def _load_local_users() -> list[dict]:
    with open(BASE_DIR / "users.json") as f:
        return json.load(f)["users"]


def _authenticate_local(username: str, password: str) -> dict | None:
    for u in _load_local_users():
        if u["username"] == username and u["password"] == password:
            return u
    return None


def _normalise_local_user(u: dict) -> dict:
    """Convert users.json record to the canonical user shape used everywhere."""
    return {
        "id":      f"local:{u['username']}",
        "name":    u.get("display_name", u["username"]),
        "email":   u.get("email", ""),
        "picture": "",
        "role":    u.get("role", "viewer"),
    }


# -----------------------------------------------------------------------
# OAuth callback — handle ?code= before rendering anything
# -----------------------------------------------------------------------
def _handle_oauth_callback() -> None:
    """If query params contain 'code', complete the OAuth exchange."""
    params = st.query_params
    code = params.get("code")
    if not code:
        return

    # Clear params immediately so a page refresh won't re-trigger
    st.query_params.clear()

    with st.spinner("Signing you in with Google…"):
        try:
            user_info = exchange_code(code)
        except Exception as exc:
            st.error(f"Google sign-in failed: {exc}")
            return

    db_user = upsert_user(user_info)
    st.session_state["logged_in"] = True
    st.session_state["user"] = db_user or user_info
    st.rerun()


_handle_oauth_callback()


# -----------------------------------------------------------------------
# Login page
# -----------------------------------------------------------------------
def _show_login() -> None:
    st.markdown(
        '<style>section.main > div {overflow: hidden !important;}</style>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div style="text-align:center;margin-top:3rem;">
            <div style="font-size:3rem;">🛡</div>
            <h1 style="margin-bottom:0;">TrustLLM</h1>
            <p style="color:#94a3b8;">AI Model Evaluation Platform</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _, col, _ = st.columns([1.5, 1, 1.5])
    with col:
        # ---- Google OAuth button ----
        if is_configured():
            state = generate_state()
            auth_url = get_auth_url(state)
            st.markdown(
                f"""
                <a href="{auth_url}" target="_self" class="google-signin-btn">
                    <svg width="18" height="18" viewBox="0 0 48 48" style="margin-right:10px;vertical-align:middle;">
                        <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
                        <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
                        <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
                        <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
                    </svg>
                    Continue with Google
                </a>
                """,
                unsafe_allow_html=True,
            )
            st.markdown(
                '<div style="text-align:center;color:#475569;font-size:0.8rem;margin:1rem 0;">or sign in with username</div>',
                unsafe_allow_html=True,
            )

        # ---- Username / password form ----
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", use_container_width=True)

        if submitted:
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
            st.caption("Username: **TestUser**  •  Password: **User123**")

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align:center;font-size:12px;color:#94a3b8;">
            Built by
            <a href="https://www.linkedin.com/in/monika-kushwaha-52443735/"
               target="_blank" style="color:#60a5fa;text-decoration:none;">
               Monika Kushwaha
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )


# -----------------------------------------------------------------------
# Gate
# -----------------------------------------------------------------------
if not st.session_state.get("logged_in"):
    _show_login()
    st.stop()

# Keep last_active fresh on every page load
_current_user = st.session_state["user"]
touch_user(_current_user.get("id", ""))

# -----------------------------------------------------------------------
# Lazy page imports (only after auth gate)
# -----------------------------------------------------------------------
from ui_pages.overview        import render as overview
from ui_pages.prompt_explorer import render as prompt_explorer
from ui_pages.leaderboard     import render as leaderboard
from ui_pages.run_eval        import render as run_eval
from ui_pages.agent_performance import render as agent_performance
from ui_pages.rag_page        import render as rag_testing
from ui_pages.prompt_dataset  import render as prompt_dataset
from ui_pages.failure_analysis import render as failure_analysis
from ui_pages.profile         import render as profile_page
from ui_pages.query_history   import render as query_history_page

# -----------------------------------------------------------------------
# Projects
# -----------------------------------------------------------------------
with open(BASE_DIR / "projects.json") as _pf:
    _projects_data = json.load(_pf)["projects"]
_project_names = ["All Projects"] + [p["name"] for p in _projects_data]

# -----------------------------------------------------------------------
# Top header bar
# -----------------------------------------------------------------------
def _avatar_img(picture: str, name: str, size: int = 32) -> str:
    if picture:
        return (
            f'<img src="{picture}" width="{size}" height="{size}" '
            f'style="border-radius:50%;object-fit:cover;vertical-align:middle;" '
            f'referrerpolicy="no-referrer">'
        )
    initials = "".join(w[0].upper() for w in name.split()[:2]) or "U"
    return (
        f'<span style="display:inline-flex;width:{size}px;height:{size}px;border-radius:50%;'
        f'background:#2563eb;align-items:center;justify-content:center;'
        f'font-size:{size // 3}px;font-weight:700;color:#fff;">{initials}</span>'
    )


user = st.session_state["user"]
user_name    = user.get("name",    user.get("display_name", "User"))
user_picture = user.get("picture", "")

header = st.container()
with header:
    h1, h2, h3, h4, h5 = st.columns([1.2, 2, 2, 0.8, 1.1])
    with h1:
        st.markdown("**🛡 TrustLLM**")
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
            '<a href="https://github.com/" target="_blank" class="header-btn">📖 Docs</a>',
            unsafe_allow_html=True,
        )
    with h5:
        # User avatar + popover with profile / logout actions
        with st.popover(
            f"{_avatar_img(user_picture, user_name)} &nbsp;{user_name}",
            use_container_width=True,
        ):
            st.markdown(
                f"<div style='font-size:0.85rem;color:#94a3b8;padding-bottom:0.5rem;'>"
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

# Resolve project category filter
_selected_categories = None
if selected_project != "All Projects":
    for p in _projects_data:
        if p["name"] == selected_project:
            _selected_categories = p["categories"]
            break
st.session_state["project_categories"] = _selected_categories

# -----------------------------------------------------------------------
# Sidebar
# -----------------------------------------------------------------------
st.sidebar.markdown("## 🛡 TrustLLM")
st.sidebar.caption(f"Signed in as **{user_name}**")
st.sidebar.divider()

# Read nav_page override (set by profile page buttons or history reload)
_nav_override = st.session_state.pop("nav_page", None)

_all_pages = [
    "Overview",
    "Prompt Explorer",
    "Leaderboard",
    "Run Evaluation",
    "Agent Performance",
    "RAG Testing",
    "Prompt Dataset",
    "Failure Analysis",
    "Query History",
    "Profile",
]

_default_idx = _all_pages.index(_nav_override) if _nav_override in _all_pages else 0

page = st.sidebar.radio("Navigation", _all_pages, index=_default_idx)

st.sidebar.divider()
if st.sidebar.button("Sign out", use_container_width=True):
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()
st.sidebar.caption("TrustLLM • LLM Evaluation Toolkit")

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

_routes[page]()
