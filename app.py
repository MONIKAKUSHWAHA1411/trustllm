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
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

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

# -------------------------------
# LOGIN UI (FIXED - NO CSS BREAKING APP)
# -------------------------------
def _show_login():

    st.markdown("""
    <style>
    .login-container {
        margin-top: 10vh;
        text-align: center;
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
    """, unsafe_allow_html=True)

    # Header
    st.markdown("""
    <div class="login-container">
        <div style="font-size:3rem;">🛡</div>
        <h1>TrustLLM</h1>
        <p style="color:#94a3b8;">AI Model Evaluation Platform</p>
    </div>
    """, unsafe_allow_html=True)

    # Center form
    col1, col2, col3 = st.columns([1.5, 1, 1.5])

    with col2:
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

        st.caption("Username: TestUser • Password: User123")

    # Footer
    st.markdown("""
    <div class="login-footer">
        Built by Monika Kushwaha
    </div>
    """, unsafe_allow_html=True)


# -------------------------------
# AUTH GATE
# -------------------------------
if not st.session_state.get("logged_in"):
    _show_login()
    st.stop()

# ===============================================
# MAIN APP (RESTORED)
# ===============================================

# -------------------------------
# LOAD PROJECTS
# -------------------------------
with open(BASE_DIR / "projects.json") as f:
    projects_data = json.load(f)["projects"]

project_names = ["All Projects"] + [p["name"] for p in projects_data]

# -------------------------------
# HEADER
# -------------------------------
header = st.container()

with header:
    col1, col2, col3, col4, col5 = st.columns([1.2, 2, 2, 0.8, 0.8])

    with col1:
        st.markdown("**🛡 TrustLLM**")

    with col2:
        selected_project = st.selectbox(
            "Project",
            project_names,
            label_visibility="collapsed"
        )

    with col3:
        selected_env = st.selectbox(
            "Environment",
            ["production", "staging", "development"],
            label_visibility="collapsed"
        )

    with col4:
        st.markdown(
            '<a href="https://github.com/" target="_blank">📖 Docs</a>',
            unsafe_allow_html=True
        )

    with col5:
        st.markdown(
            '<a href="#">⚖️ Compare</a>',
            unsafe_allow_html=True
        )

st.markdown("---")

# -------------------------------
# PROJECT FILTER
# -------------------------------
selected_categories = None

if selected_project != "All Projects":
    for p in projects_data:
        if p["name"] == selected_project:
            selected_categories = p["categories"]
            break

st.session_state["project_categories"] = selected_categories

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
# ROUTING (ALL FEATURES BACK)
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
