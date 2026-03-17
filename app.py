import streamlit as st

# -------------------- PAGE CONFIG --------------------
st.set_page_config(
    page_title="TrustLLM",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
header {visibility: hidden;}
footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)
# -------------------- CUSTOM CSS --------------------
st.markdown("""
<style>

/* Kill Streamlit default spacing */
section.main > div {
    padding-top: 0rem;
    padding-bottom: 0rem;
}
[data-testid="stAppViewContainer"] {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100vh;
}

/* Background */
.stApp {
    background: radial-gradient(circle at top, #0b1b2b, #020617);
    color: white;
}

/* Card */
.login-card {
    background: rgba(255, 255, 255, 0.05);
    padding: 35px;
    border-radius: 16px;
    width: 360px;
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,0.1);
    box-shadow: 0 10px 40px rgba(0,0,0,0.6);
}

/* Title */
.title {
    text-align: center;
    font-size: 34px;
    font-weight: 700;
    margin-bottom: 5px;
}

.subtitle {
    text-align: center;
    font-size: 14px;
    color: #9CA3AF;
    margin-bottom: 25px;
}

/* Inputs */
.stTextInput>div>div>input {
    background-color: #0f172a;
    color: white;
    border-radius: 10px;
    border: 1px solid #1f2937;
    padding: 10px;
}

/* Button */
.stButton>button {
    width: 100%;
    background: linear-gradient(90deg, #2563eb, #1d4ed8);
    color: white;
    border-radius: 10px;
    padding: 10px;
    font-weight: 600;
    border: none;
}

.stButton>button:hover {
    background: linear-gradient(90deg, #1d4ed8, #1e40af);
}

/* Footer */
.footer {
    text-align: center;
    font-size: 12px;
    color: #6B7280;
    margin-top: 15px;
}

</style>
""", unsafe_allow_html=True)

# -------------------- CENTER WRAPPER --------------------

# -------------------- LOGIN CARD --------------------
st.markdown('<div class="login-card">', unsafe_allow_html=True)

st.markdown('<div class="title">🔐 TrustLLM</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">AI Model Evaluation Platform</div>', unsafe_allow_html=True)

# Inputs
username = st.text_input("Username", placeholder="Enter username")
password = st.text_input("Password", type="password", placeholder="Enter password")

# Login button
if st.button("Sign in"):
    if username == "TestUser" and password == "User123":
        st.success("Login successful 🚀")
        st.session_state["logged_in"] = True
    else:
        st.error("Invalid credentials")

# Demo creds
st.markdown(
    '<div class="footer">Demo: TestUser / User123</div>',
    unsafe_allow_html=True
)

# Branding
st.markdown(
    '<div class="footer">Built by Monika Kushwaha</div>',
    unsafe_allow_html=True
)

st.markdown('</div>', unsafe_allow_html=True)  # card

# -------------------- AFTER LOGIN --------------------
if st.session_state.get("logged_in"):
    st.title("Welcome to TrustLLM Dashboard 🚀")
    st.write("Now your real app starts here.")
