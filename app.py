import streamlit as st
import json
from pathlib import Path

from ui_pages.overview import render as overview
from ui_pages.prompt_explorer import render as prompt_explorer
from ui_pages.leaderboard import render as leaderboard
from ui_pages.run_eval import render as run_eval
from ui_pages.agent_performance import render as agent_performance
from ui_pages.rag_page import render as rag_testing
from ui_pages.prompt_dataset import render as prompt_dataset
from ui_pages.failure_analysis import render as failure_analysis

BASE_DIR = Path(__file__).resolve().parent

# -------------------------------
# PAGE CONFIG
# -------------------------------
st.set_page_config(
    page_title="TrustLLM",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------
# LOAD CSS
# -------------------------------
def load_css():
    with open(BASE_DIR / "style.css") as f:
        st.markdown(
            f"<style>{f.read()}</style>",
            unsafe_allow_html=True
        )

load_css()


# -------------------------------
# AUTH HELPERS
# -------------------------------
def _load_users():
    with open(BASE_DIR / "users.json") as f:
        return json.load(f)["users"]


def _authenticate(username, password):
    for u in _load_users():
        if u["username"] == username and u["password"] == password:
            return u
    return None

def _show_login():
    # -------------------------------
    # CLEAN NO-SCROLL FIX
    # -------------------------------
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
            max-width: 100%;
        }

        html, body, [data-testid="stAppViewContainer"] {
            overflow: hidden;
        }

        .login-box {
            margin-top: 8vh;
        }

        .login-footer {
            position: fixed;
            bottom: 10px;
            width: 100%;
            text-align: center;
            font-size: 12px;
            color: #94a3b8;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # -------------------------------
    # HEADER
    # -------------------------------
    st.markdown(
        """
        <div class="login-box" style="text-align:center;">
            <div style="font-size:3rem;">🛡</div>
            <h1 style="margin-bottom:0;">TrustLLM</h1>
            <p style="color:#94a3b8;">AI Model Evaluation Platform</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # -------------------------------
    # LOGIN FORM
    # -------------------------------
    col_l, col_form, col_r = st.columns([1.5, 1, 1.5])
    with col_form:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", use_container_width=True)

        if submitted:
            user = _authenticate(username, password)
            if user:
                st.session_state["logged_in"] = True
                st.session_state["user"] = user
                st.rerun()
            else:
                st.error("Invalid username or password.")

        st.caption("Username: **TestUser**  •  Password: **User123**")

    # -------------------------------
    # FOOTER
    # -------------------------------
    st.markdown(
        """
        <div class="login-footer">
            Built by 
            <a href="https://www.linkedin.com/in/monika-kushwaha-52443735/" 
            target="_blank" 
            style="color:#60a5fa; text-decoration:none;">
            Monika Kushwaha
            </a>
        </div>
        """,
        unsafe_allow_html=True
    )


# -----------------------------------------------
# GATE: show login if not authenticated
# -----------------------------------------------
if not st.session_state.get("logged_in"):
    _show_login()
    st.stop()


# ===============================================
# AUTHENTICATED APP
# ===============================================

# -------------------------------
# LOAD PROJECTS
# -------------------------------
with open(BASE_DIR / "projects.json") as _pf:
    _projects_data = json.load(_pf)["projects"]
_project_names = ["All Projects"] + [p["name"] for p in _projects_data]

# -------------------------------
# TOP HEADER BAR
# -------------------------------
header = st.container()
with header:
    h1, h2, h3, h4, h5 = st.columns([1.2, 2, 2, 0.8, 0.8])
    with h1:
        st.markdown("**🛡 TrustLLM**")
    with h2:
        selected_project = st.selectbox(
            "Project",
            _project_names,
            label_visibility="collapsed",
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
        st.markdown(
            '<a href="#compare" class="header-btn">⚖️ Compare</a>',
            unsafe_allow_html=True,
        )

st.markdown('<hr class="header-divider">', unsafe_allow_html=True)

# Resolve selected project
_selected_categories = None
if selected_project != "All Projects":
    for p in _projects_data:
        if p["name"] == selected_project:
            _selected_categories = p["categories"]
            break

st.session_state["project_categories"] = _selected_categories

# -------------------------------
# SIDEBAR
# -------------------------------
user = st.session_state["user"]
st.sidebar.markdown("## 🛡 TrustLLM")
st.sidebar.caption(f"Signed in as **{user['display_name']}**")

st.sidebar.divider()

page = st.sidebar.radio(
    "Navigation",
    [
        "Overview",
        "Prompt Explorer",
        "Leaderboard",
        "Run Evaluation",
        "Agent Performance",
        "RAG Testing",
        "Prompt Dataset",
        "Failure Analysis",
    ]
)

st.sidebar.divider()

if st.sidebar.button("Sign out", use_container_width=True):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

st.sidebar.caption("TrustLLM • LLM Evaluation Toolkit")

# -------------------------------
# ROUTER
# -------------------------------
if page == "Overview":
    overview()

elif page == "Prompt Explorer":
    prompt_explorer()

elif page == "Leaderboard":
    leaderboard()

elif page == "Run Evaluation":
    run_eval()

elif page == "Agent Performance":
    agent_performance()

elif page == "RAG Testing":
    rag_testing()

elif page == "Prompt Dataset":
    prompt_dataset()

elif page == "Failure Analysis":
    failure_analysis()
