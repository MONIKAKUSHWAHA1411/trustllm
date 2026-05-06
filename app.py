"""
app.py — TrustLLM main entry point.

Auth flow:
    1. Local .env / st.secrets checked for SUPABASE_URL + SUPABASE_KEY.
    2. If Supabase credentials present  → show "Sign in with Google" button (via Supabase OAuth).
    3. If Supabase redirects back with ?code= → exchange for user info.
    4. Fall-back username/password login always available.
    5. All authenticated users are upserted into SQLite (db/database.py).
"""

import json
import os
from pathlib import Path
from typing import Optional, List

import streamlit as st

# Load .env before anything else touches os.getenv
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

from db.database import init_db, upsert_user, touch_user
from auth.supabase_auth import is_configured, get_auth_url, exchange_code

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
    """Convert users.json record to the canonical user shape used everywhere."""
    return {
        "id":      f"local:{u['username']}",
        "name":    u.get("display_name", u["username"]),
        "email":   u.get("email", ""),
        "picture": "",
        "role":    u.get("role", "viewer"),
    }


def _create_local_user(username: str, password: str, display_name: str = "", email: str = "") -> Optional[dict]:
    """Add a new user to users.json. Returns the user dict or None if username taken."""
    with open(USERS_PATH) as f:
        data = json.load(f)

    # Check for duplicate username
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
# OAuth callback — handle ?code= before rendering anything
# -----------------------------------------------------------------------
def _handle_oauth_callback() -> None:
    """If query params contain 'code', complete the Supabase OAuth exchange."""
    params = st.query_params
    code = params.get("code")
    if not code:
        return

    # Clear params immediately so a page refresh won't re-trigger
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
# Login page — professional design
# -----------------------------------------------------------------------
def _show_login() -> None:
    # Hide sidebar on login page
    st.markdown(
        """<style>
        section[data-testid="stSidebar"] { display: none !important; }
        section.main > div { overflow: hidden !important; }
        header[data-testid="stHeader"] { display: none !important; }
        </style>""",
        unsafe_allow_html=True,
    )

    # ---- Hero / branding ----
    st.markdown(
        """
        <div style="text-align:center;margin-top:2.5rem;margin-bottom:1rem;">
            <div style="display:inline-flex;align-items:center;justify-content:center;
                        width:64px;height:64px;background:linear-gradient(135deg,#2563eb 0%,#7c3aed 100%);
                        border-radius:16px;margin-bottom:0.8rem;">
                <span style="font-size:2rem;">🛡</span>
            </div>
            <h1 style="margin:0;font-size:2.2rem;font-weight:800;
                       background:linear-gradient(135deg,#60a5fa,#a78bfa);
                       -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
                TrustLLM
            </h1>
            <p style="color:#94a3b8;font-size:0.95rem;margin-top:0.3rem;">
                AI Model Evaluation &amp; Trust Scoring Platform
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Center the login card
    _, col, _ = st.columns([1.2, 1, 1.2])
    with col:
        # ---- Google OAuth (Supabase) ----
        if is_configured():
            try:
                auth_url = get_auth_url()
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
                    '<div style="text-align:center;color:#475569;font-size:0.78rem;'
                    'margin:0.75rem 0;display:flex;align-items:center;gap:0.5rem;">'
                    '<div style="flex:1;height:1px;background:#334155;"></div>'
                    '<span>or continue with email</span>'
                    '<div style="flex:1;height:1px;background:#334155;"></div>'
                    '</div>',
                    unsafe_allow_html=True,
                )
            except Exception:
                pass  # Supabase not reachable; fall through to form login

        # ---- Tabs: Sign In / Create Account ----
        tab_signin, tab_create = st.tabs(["Sign In", "Create Account"])

        with tab_signin:
            with st.form("login_form"):
                username = st.text_input("Username", placeholder="Enter your username")
                password = st.text_input("Password", type="password", placeholder="Enter your password")
                submitted = st.form_submit_button("Sign in", use_container_width=True)

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

            # Show demo credentials only when Supabase isn't configured
            if not is_configured():
                st.markdown(
                    '<div style="text-align:center;font-size:0.78rem;color:#64748b;'
                    'margin-top:0.5rem;padding:0.5rem;background:#0f172a;border-radius:6px;">'
                    'Demo credentials: <strong style="color:#94a3b8;">TestUser</strong> / '
                    '<strong style="color:#94a3b8;">User123</strong>'
                    '</div>',
                    unsafe_allow_html=True,
                )

        with tab_create:
            with st.form("create_account_form"):
                new_name = st.text_input("Display Name", placeholder="Your full name")
                new_user = st.text_input("Username", placeholder="Choose a username", key="ca_user")
                new_email = st.text_input("Email (optional)", placeholder="you@example.com", key="ca_email")
                new_pass = st.text_input("Password", type="password", placeholder="Min 6 characters", key="ca_pass")
                new_pass2 = st.text_input("Confirm Password", type="password", placeholder="Re-enter password", key="ca_pass2")
                create_btn = st.form_submit_button("Create Account", use_container_width=True)

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
                        st.success("Account created! You can now sign in.")
                    else:
                        st.error("Username already taken. Choose a different one.")

        # ---- Forgot password ----
        with st.expander("Forgot password?"):
            fp_user = st.text_input("Username", key="fp_username", placeholder="Enter your username")
            fp_new  = st.text_input("New password", type="password", key="fp_new", placeholder="New password")
            fp_conf = st.text_input("Confirm", type="password", key="fp_conf", placeholder="Confirm new password")
            if st.button("Reset password", key="fp_submit", use_container_width=True):
                if not fp_user or not fp_new:
                    st.error("Please fill in all fields.")
                elif fp_new != fp_conf:
                    st.error("Passwords do not match.")
                elif len(fp_new) < 6:
                    st.error("Password must be at least 6 characters.")
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
                        st.success("Password updated. You can now sign in.")
                    else:
                        st.error("Username not found.")

    # ---- Footer ----
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        """
        <div style="text-align:center;font-size:11px;color:#475569;margin-top:1rem;">
            <div style="margin-bottom:0.3rem;">
                Powered by ChromaDB &middot; Groq &middot; Streamlit
            </div>
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
def _user_label(name: str) -> str:
    """Plain-text label for the popover trigger (Streamlit escapes HTML in labels)."""
    return f"👤 {name}"


user = st.session_state["user"]
user_name    = user.get("name",    user.get("display_name", "User"))

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
            _user_label(user_name),
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
