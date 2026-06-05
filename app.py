import streamlit as st
import json
import textwrap
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


def _h(html: str) -> str:
    """Strip common indentation so Markdown never misreads HTML as a code block."""
    return textwrap.dedent(html).strip()


# -----------------------------------------------
# PAGE CONFIG
# -----------------------------------------------
st.set_page_config(
    page_title="TrustLLM",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)


# -----------------------------------------------
# LOAD CSS
# -----------------------------------------------
def load_css():
    with open(BASE_DIR / "style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()


# -----------------------------------------------
# AUTH HELPERS
# -----------------------------------------------
def _load_users():
    with open(BASE_DIR / "users.json") as f:
        return json.load(f)["users"]


def _authenticate(username, password):
    for u in _load_users():
        if u["username"] == username and u["password"] == password:
            return u
    return None


# -----------------------------------------------
# LOGIN PAGE  —  VERDICT style
# -----------------------------------------------
def _show_login():
    st.markdown(_h("""
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .stApp { background: #F9F8F6 !important; }
        section.main .block-container {
            padding: 0 !important;
            max-width: 100% !important;
        }
        [data-testid="stForm"] {
            background: white !important;
            border: 1px solid #E4E2DC !important;
            border-radius: 0 !important;
            box-shadow: none !important;
            padding: 2rem !important;
        }
        [data-testid="stForm"] label {
            color: #0E0E0E !important;
            font-size: 0.75rem !important;
            font-weight: 700 !important;
            letter-spacing: 0.08em !important;
            text-transform: uppercase !important;
            font-family: 'Syne', sans-serif !important;
        }
        [data-testid="stForm"] input {
            background-color: #F9F8F6 !important;
            border: 1px solid #E4E2DC !important;
            border-radius: 0 !important;
            color: #0E0E0E !important;
        }
        [data-testid="stForm"] input::placeholder { color: #888888 !important; }
        [data-testid="stForm"] input:focus {
            border-color: #E8290B !important;
            box-shadow: none !important;
        }
        [data-testid="stForm"] .stButton > button {
            background-color: #E8290B !important;
            color: white !important;
            font-weight: 700 !important;
            font-size: 0.8rem !important;
            border-radius: 0 !important;
            border: none !important;
            width: 100%;
            font-family: 'Syne', sans-serif !important;
            letter-spacing: 0.12em !important;
            text-transform: uppercase !important;
        }
        [data-testid="stForm"] .stButton > button:hover {
            background-color: #C42208 !important;
        }
        [data-testid="stForm"] [data-testid="InputInstructions"] {
            display: none !important;
        }
        </style>
        <link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
    """), unsafe_allow_html=True)

    left_col, right_col = st.columns([13, 11])

    # ── LEFT PANEL: Full landing page content (scrollable) ────────────
    with left_col:
        _lp = _h("""
            <div style="background:#0E0E0E;height:100vh;overflow-y:auto;padding:3rem 3.5rem;
                        font-family:'Syne',sans-serif;
                        scrollbar-width:thin;scrollbar-color:#E8290B #1C1C1C;">

              <!-- ════ SECTION 1: HERO ════ -->
              <div style="margin-bottom:0;">
                <div style="display:flex;align-items:center;gap:12px;margin-bottom:3rem;">
                  <div style="background:#E8290B;width:40px;height:40px;display:flex;align-items:center;
                              justify-content:center;font-size:20px;font-weight:800;color:white;flex-shrink:0;">T</div>
                  <div>
                    <div style="color:white;font-size:1.1rem;font-weight:800;letter-spacing:0.03em;">TrustLLM</div>
                    <div style="color:rgba(255,255,255,0.25);font-size:8px;letter-spacing:0.18em;margin-top:2px;">EVAL PLATFORM</div>
                  </div>
                </div>

                <div style="font-size:9px;color:#E8290B;letter-spacing:0.2em;margin-bottom:1.25rem;">
                  — AI TRUST EVALUATION PLATFORM
                </div>

                <div style="color:white;font-size:3.2rem;font-weight:800;line-height:1.05;
                            letter-spacing:-0.02em;margin-bottom:1.5rem;">
                  Your LLMs.<br>
                  <em style="color:#E8290B;font-style:normal;">Honestly</em><br>
                  Evaluated.
                </div>

                <p style="color:rgba(255,255,255,0.45);font-size:0.9rem;line-height:1.7;
                          max-width:400px;margin:0 0 2rem 0;font-family:'Inter',sans-serif;font-weight:300;">
                  Score every model response for correctness, safety, and hallucination.
                  Surface failures fast. Ship with confidence.
                </p>

                <div style="margin-bottom:2rem;font-family:'Inter',sans-serif;">
                  <div style="display:flex;align-items:center;gap:10px;margin-bottom:0.6rem;">
                    <div style="width:16px;height:16px;background:#E8290B;display:flex;align-items:center;
                                justify-content:center;font-size:9px;color:white;font-weight:700;flex-shrink:0;">✓</div>
                    <span style="color:rgba(255,255,255,0.6);font-size:0.85rem;">Trace every prompt, response &amp; tool call in real time</span>
                  </div>
                  <div style="display:flex;align-items:center;gap:10px;margin-bottom:0.6rem;">
                    <div style="width:16px;height:16px;background:#E8290B;display:flex;align-items:center;
                                justify-content:center;font-size:9px;color:white;font-weight:700;flex-shrink:0;">✓</div>
                    <span style="color:rgba(255,255,255,0.6);font-size:0.85rem;">Compare models side-by-side on safety, quality &amp; cost</span>
                  </div>
                  <div style="display:flex;align-items:center;gap:10px;">
                    <div style="width:16px;height:16px;background:#E8290B;display:flex;align-items:center;
                                justify-content:center;font-size:9px;color:white;font-weight:700;flex-shrink:0;">✓</div>
                    <span style="color:rgba(255,255,255,0.6);font-size:0.85rem;">Detect hallucinations, bias &amp; safety violations automatically</span>
                  </div>
                </div>

                <div style="margin-bottom:2.5rem;">
                  <button style="background:transparent;color:white;border:1px solid rgba(255,255,255,0.2);
                                 border-radius:0;padding:0.65rem 1.5rem;font-size:0.8rem;font-weight:700;
                                 cursor:pointer;font-family:'Syne',sans-serif;letter-spacing:0.1em;"
                          onclick="this.textContent='▶ DEMO COMING SOON';setTimeout(function(){this.textContent='Watch Demo ▶';}.bind(this),2500)">
                    Watch Demo ▶
                  </button>
                </div>

                <div style="display:grid;grid-template-columns:repeat(3,1fr);
                            border:1px solid rgba(255,255,255,0.08);margin-bottom:0;">
                  <div style="padding:1.1rem 1.25rem;border-right:1px solid rgba(255,255,255,0.08);">
                    <div style="color:white;font-size:1.75rem;font-weight:800;line-height:1;margin-bottom:0.2rem;">12</div>
                    <div style="color:rgba(255,255,255,0.3);font-size:9px;letter-spacing:0.1em;font-family:'Inter',sans-serif;">MODELS SUPPORTED</div>
                  </div>
                  <div style="padding:1.1rem 1.25rem;border-right:1px solid rgba(255,255,255,0.08);">
                    <div style="color:white;font-size:1.75rem;font-weight:800;line-height:1;margin-bottom:0.2rem;">6</div>
                    <div style="color:rgba(255,255,255,0.3);font-size:9px;letter-spacing:0.1em;font-family:'Inter',sans-serif;">TRUST DIMENSIONS</div>
                  </div>
                  <div style="padding:1.1rem 1.25rem;">
                    <div style="color:#E8290B;font-size:1.75rem;font-weight:800;line-height:1;margin-bottom:0.2rem;">0.76</div>
                    <div style="color:rgba(255,255,255,0.3);font-size:9px;letter-spacing:0.1em;font-family:'Inter',sans-serif;">AVG TRUST SCORE</div>
                  </div>
                </div>
              </div>

              <!-- ════ DIVIDER ════ -->
              <div style="border-top:1px solid rgba(255,255,255,0.08);margin:3rem 0;"></div>

              <!-- ════ SECTION 2: HOW IT WORKS ════ -->
              <div style="margin-bottom:0;">
                <div style="font-size:9px;color:#E8290B;letter-spacing:0.2em;margin-bottom:1.25rem;">— HOW IT WORKS</div>
                <div style="color:white;font-size:2rem;font-weight:800;letter-spacing:-0.02em;line-height:1.1;margin-bottom:0.6rem;">
                  From prompt to trust score in seconds.
                </div>
                <p style="color:rgba(255,255,255,0.35);font-size:0.85rem;font-family:'Inter',sans-serif;margin:0 0 2.5rem 0;line-height:1.6;">
                  Five-stage pipeline — repeatable, deterministic evals.
                </p>

                <!-- Step 01 -->
                <div style="display:flex;gap:1.25rem;margin-bottom:1.5rem;">
                  <div style="flex-shrink:0;display:flex;flex-direction:column;align-items:center;">
                    <div style="background:#E8290B;width:32px;height:32px;display:flex;align-items:center;
                                justify-content:center;font-size:10px;font-weight:800;color:white;letter-spacing:0.05em;">01</div>
                    <div style="width:1px;flex:1;background:rgba(255,255,255,0.08);margin-top:4px;min-height:36px;"></div>
                  </div>
                  <div style="border:1px solid rgba(255,255,255,0.08);padding:1rem 1.25rem;flex:1;">
                    <div style="color:rgba(255,255,255,0.3);font-size:8px;letter-spacing:0.15em;margin-bottom:0.4rem;font-family:'Inter',sans-serif;">INPUT</div>
                    <div style="color:white;font-size:0.95rem;font-weight:700;margin-bottom:0.4rem;">Submit a prompt</div>
                    <div style="color:rgba(255,255,255,0.4);font-size:0.8rem;font-family:'Inter',sans-serif;line-height:1.5;">
                      Type or paste any prompt. Or load a CSV dataset for batch evaluation.
                    </div>
                  </div>
                </div>

                <!-- Step 02 -->
                <div style="display:flex;gap:1.25rem;margin-bottom:1.5rem;">
                  <div style="flex-shrink:0;display:flex;flex-direction:column;align-items:center;">
                    <div style="background:#E8290B;width:32px;height:32px;display:flex;align-items:center;
                                justify-content:center;font-size:10px;font-weight:800;color:white;letter-spacing:0.05em;">02</div>
                    <div style="width:1px;flex:1;background:rgba(255,255,255,0.08);margin-top:4px;min-height:36px;"></div>
                  </div>
                  <div style="border:1px solid rgba(255,255,255,0.08);padding:1rem 1.25rem;flex:1;">
                    <div style="color:rgba(255,255,255,0.3);font-size:8px;letter-spacing:0.15em;margin-bottom:0.4rem;font-family:'Inter',sans-serif;">MODEL SELECTION</div>
                    <div style="color:white;font-size:0.95rem;font-weight:700;margin-bottom:0.4rem;">Pick from 12 models</div>
                    <div style="color:rgba(255,255,255,0.4);font-size:0.8rem;font-family:'Inter',sans-serif;line-height:1.5;">
                      Groq · Claude · GPT · Gemini · Mistral · Phi — choose any or compare all.
                    </div>
                  </div>
                </div>

                <!-- Step 03 -->
                <div style="display:flex;gap:1.25rem;margin-bottom:1.5rem;">
                  <div style="flex-shrink:0;display:flex;flex-direction:column;align-items:center;">
                    <div style="background:#E8290B;width:32px;height:32px;display:flex;align-items:center;
                                justify-content:center;font-size:10px;font-weight:800;color:white;letter-spacing:0.05em;">03</div>
                    <div style="width:1px;flex:1;background:rgba(255,255,255,0.08);margin-top:4px;min-height:36px;"></div>
                  </div>
                  <div style="border:1px solid rgba(255,255,255,0.08);padding:1rem 1.25rem;flex:1;">
                    <div style="color:rgba(255,255,255,0.3);font-size:8px;letter-spacing:0.15em;margin-bottom:0.4rem;font-family:'Inter',sans-serif;">EVAL MODE</div>
                    <div style="color:white;font-size:0.95rem;font-weight:700;margin-bottom:0.6rem;">Choose your test path</div>
                    <div style="display:flex;gap:0.5rem;flex-wrap:wrap;">
                      <span style="background:rgba(255,255,255,0.05);color:rgba(255,255,255,0.55);padding:0.25rem 0.6rem;
                                   font-size:0.72rem;font-family:'Inter',sans-serif;border:1px solid rgba(255,255,255,0.08);">Run Evaluation</span>
                      <span style="background:rgba(255,255,255,0.05);color:rgba(255,255,255,0.55);padding:0.25rem 0.6rem;
                                   font-size:0.72rem;font-family:'Inter',sans-serif;border:1px solid rgba(255,255,255,0.08);">RAG Testing</span>
                      <span style="background:rgba(255,255,255,0.05);color:rgba(255,255,255,0.55);padding:0.25rem 0.6rem;
                                   font-size:0.72rem;font-family:'Inter',sans-serif;border:1px solid rgba(255,255,255,0.08);">Batch Dataset</span>
                    </div>
                  </div>
                </div>

                <!-- Step 04 -->
                <div style="display:flex;gap:1.25rem;margin-bottom:1.5rem;">
                  <div style="flex-shrink:0;display:flex;flex-direction:column;align-items:center;">
                    <div style="background:#E8290B;width:32px;height:32px;display:flex;align-items:center;
                                justify-content:center;font-size:10px;font-weight:800;color:white;letter-spacing:0.05em;">04</div>
                    <div style="width:1px;flex:1;background:rgba(255,255,255,0.08);margin-top:4px;min-height:36px;"></div>
                  </div>
                  <div style="border:1px solid rgba(255,255,255,0.08);padding:1rem 1.25rem;flex:1;">
                    <div style="color:rgba(255,255,255,0.3);font-size:8px;letter-spacing:0.15em;margin-bottom:0.4rem;font-family:'Inter',sans-serif;">LLM-AS-JUDGE SCORING</div>
                    <div style="color:white;font-size:0.95rem;font-weight:700;margin-bottom:0.75rem;">Six dimensions, one trust score</div>
                    <div style="font-family:'Inter',sans-serif;">
                      <div style="display:flex;justify-content:space-between;margin-bottom:3px;">
                        <span style="color:rgba(255,255,255,0.4);font-size:0.72rem;">Truthfulness</span>
                        <span style="color:#E8290B;font-size:0.72rem;font-weight:700;">0.92</span>
                      </div>
                      <div style="background:rgba(255,255,255,0.06);height:2px;margin-bottom:6px;">
                        <div style="background:#E8290B;width:92%;height:100%;"></div></div>
                      <div style="display:flex;justify-content:space-between;margin-bottom:3px;">
                        <span style="color:rgba(255,255,255,0.4);font-size:0.72rem;">Safety</span>
                        <span style="color:rgba(255,255,255,0.5);font-size:0.72rem;font-weight:700;">0.88</span>
                      </div>
                      <div style="background:rgba(255,255,255,0.06);height:2px;margin-bottom:6px;">
                        <div style="background:rgba(255,255,255,0.25);width:88%;height:100%;"></div></div>
                      <div style="display:flex;justify-content:space-between;margin-bottom:3px;">
                        <span style="color:rgba(255,255,255,0.4);font-size:0.72rem;">Fairness</span>
                        <span style="color:rgba(255,255,255,0.5);font-size:0.72rem;font-weight:700;">0.74</span>
                      </div>
                      <div style="background:rgba(255,255,255,0.06);height:2px;margin-bottom:6px;">
                        <div style="background:rgba(255,255,255,0.25);width:74%;height:100%;"></div></div>
                      <div style="display:flex;justify-content:space-between;margin-bottom:3px;">
                        <span style="color:rgba(255,255,255,0.4);font-size:0.72rem;">Privacy</span>
                        <span style="color:rgba(255,255,255,0.5);font-size:0.72rem;font-weight:700;">0.81</span>
                      </div>
                      <div style="background:rgba(255,255,255,0.06);height:2px;margin-bottom:6px;">
                        <div style="background:rgba(255,255,255,0.25);width:81%;height:100%;"></div></div>
                      <div style="display:flex;justify-content:space-between;margin-bottom:3px;">
                        <span style="color:rgba(255,255,255,0.4);font-size:0.72rem;">Robustness</span>
                        <span style="color:rgba(255,255,255,0.5);font-size:0.72rem;font-weight:700;">0.69</span>
                      </div>
                      <div style="background:rgba(255,255,255,0.06);height:2px;margin-bottom:6px;">
                        <div style="background:rgba(255,255,255,0.25);width:69%;height:100%;"></div></div>
                      <div style="display:flex;justify-content:space-between;margin-bottom:3px;">
                        <span style="color:rgba(255,255,255,0.4);font-size:0.72rem;">Ethics</span>
                        <span style="color:rgba(255,255,255,0.5);font-size:0.72rem;font-weight:700;">0.85</span>
                      </div>
                      <div style="background:rgba(255,255,255,0.06);height:2px;margin-bottom:8px;">
                        <div style="background:rgba(255,255,255,0.25);width:85%;height:100%;"></div></div>
                      <div style="color:rgba(255,255,255,0.2);font-size:0.7rem;font-family:'Syne',sans-serif;font-weight:700;">
                        Trust Score = Σ(6 dims) / 6
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Step 05 -->
                <div style="display:flex;gap:1.25rem;">
                  <div style="flex-shrink:0;">
                    <div style="background:#E8290B;width:32px;height:32px;display:flex;align-items:center;
                                justify-content:center;font-size:10px;font-weight:800;color:white;letter-spacing:0.05em;">05</div>
                  </div>
                  <div style="border:1px solid rgba(255,255,255,0.08);padding:1rem 1.25rem;flex:1;">
                    <div style="color:rgba(255,255,255,0.3);font-size:8px;letter-spacing:0.15em;margin-bottom:0.4rem;font-family:'Inter',sans-serif;">RESULTS</div>
                    <div style="color:white;font-size:0.95rem;font-weight:700;margin-bottom:0.6rem;">Slice it however you ship</div>
                    <div style="display:flex;gap:0.5rem;flex-wrap:wrap;">
                      <span style="background:rgba(255,255,255,0.05);color:rgba(255,255,255,0.55);padding:0.25rem 0.6rem;
                                   font-size:0.72rem;font-family:'Inter',sans-serif;border:1px solid rgba(255,255,255,0.08);">📋 Per-Eval Breakdown</span>
                      <span style="background:rgba(255,255,255,0.05);color:rgba(255,255,255,0.55);padding:0.25rem 0.6rem;
                                   font-size:0.72rem;font-family:'Inter',sans-serif;border:1px solid rgba(255,255,255,0.08);">🕐 Session History</span>
                      <span style="background:rgba(255,255,255,0.05);color:rgba(255,255,255,0.55);padding:0.25rem 0.6rem;
                                   font-size:0.72rem;font-family:'Inter',sans-serif;border:1px solid rgba(255,255,255,0.08);">🏆 Leaderboard</span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- ════ DIVIDER ════ -->
              <div style="border-top:1px solid rgba(255,255,255,0.08);margin:3rem 0;"></div>

              <!-- ════ SECTION 3: TRUST DIMENSIONS ════ -->
              <div style="margin-bottom:0;">
                <div style="font-size:9px;color:#E8290B;letter-spacing:0.2em;margin-bottom:1.25rem;">— TRUST DIMENSIONS</div>
                <div style="color:white;font-size:2rem;font-weight:800;letter-spacing:-0.02em;line-height:1.1;margin-bottom:0.6rem;">
                  6 Dimensions of Trust.
                </div>
                <p style="color:rgba(255,255,255,0.35);font-size:0.85rem;font-family:'Inter',sans-serif;margin:0 0 2rem 0;line-height:1.6;">
                  Each independent, each scored 0–1, each surfaced in your final report.
                </p>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;">
                  <div style="border:1px solid rgba(255,255,255,0.08);padding:1.1rem;background:rgba(255,255,255,0.02);">
                    <div style="font-size:1.1rem;margin-bottom:0.5rem;">🔍</div>
                    <div style="color:white;font-size:0.88rem;font-weight:700;margin-bottom:0.4rem;">Truthfulness</div>
                    <div style="color:rgba(255,255,255,0.35);font-size:0.74rem;font-family:'Inter',sans-serif;line-height:1.5;">
                      Factual grounding measured against expected answers and retrieved context.
                    </div>
                  </div>
                  <div style="border:1px solid rgba(255,255,255,0.08);padding:1.1rem;background:rgba(255,255,255,0.02);">
                    <div style="font-size:1.1rem;margin-bottom:0.5rem;">🛡️</div>
                    <div style="color:white;font-size:0.88rem;font-weight:700;margin-bottom:0.4rem;">Safety</div>
                    <div style="color:rgba(255,255,255,0.35);font-size:0.74rem;font-family:'Inter',sans-serif;line-height:1.5;">
                      Jailbreak resistance, harmful content detection, and prompt-injection scoring.
                    </div>
                  </div>
                  <div style="border:1px solid rgba(255,255,255,0.08);padding:1.1rem;background:rgba(255,255,255,0.02);">
                    <div style="font-size:1.1rem;margin-bottom:0.5rem;">⚖️</div>
                    <div style="color:white;font-size:0.88rem;font-weight:700;margin-bottom:0.4rem;">Fairness</div>
                    <div style="color:rgba(255,255,255,0.35);font-size:0.74rem;font-family:'Inter',sans-serif;line-height:1.5;">
                      Demographic bias, group fairness, and toxicity across diverse prompts.
                    </div>
                  </div>
                  <div style="border:1px solid rgba(255,255,255,0.08);padding:1.1rem;background:rgba(255,255,255,0.02);">
                    <div style="font-size:1.1rem;margin-bottom:0.5rem;">🔒</div>
                    <div style="color:white;font-size:0.88rem;font-weight:700;margin-bottom:0.4rem;">Privacy</div>
                    <div style="color:rgba(255,255,255,0.35);font-size:0.74rem;font-family:'Inter',sans-serif;line-height:1.5;">
                      PII leakage detection, data exfiltration risk, and consent boundary checks.
                    </div>
                  </div>
                  <div style="border:1px solid rgba(255,255,255,0.08);padding:1.1rem;background:rgba(255,255,255,0.02);">
                    <div style="font-size:1.1rem;margin-bottom:0.5rem;">💪</div>
                    <div style="color:white;font-size:0.88rem;font-weight:700;margin-bottom:0.4rem;">Robustness</div>
                    <div style="color:rgba(255,255,255,0.35);font-size:0.74rem;font-family:'Inter',sans-serif;line-height:1.5;">
                      Behavior under adversarial inputs, paraphrasing, and edge-case stress tests.
                    </div>
                  </div>
                  <div style="border:1px solid rgba(255,255,255,0.08);padding:1.1rem;background:rgba(255,255,255,0.02);">
                    <div style="font-size:1.1rem;margin-bottom:0.5rem;">🧭</div>
                    <div style="color:white;font-size:0.88rem;font-weight:700;margin-bottom:0.4rem;">Ethics</div>
                    <div style="color:rgba(255,255,255,0.35);font-size:0.74rem;font-family:'Inter',sans-serif;line-height:1.5;">
                      Alignment with use-case norms, refusal quality, and decision-rationale clarity.
                    </div>
                  </div>
                </div>
              </div>

              <!-- ════ DIVIDER ════ -->
              <div style="border-top:1px solid rgba(255,255,255,0.08);margin:3rem 0;"></div>

              <!-- ════ SECTION 4: MODELS ════ -->
              <div style="margin-bottom:0;">
                <div style="font-size:9px;color:#E8290B;letter-spacing:0.2em;margin-bottom:1.25rem;">— MODELS</div>
                <div style="color:white;font-size:2rem;font-weight:800;letter-spacing:-0.02em;line-height:1.1;margin-bottom:0.6rem;">
                  12 Models. One Platform.
                </div>
                <p style="color:rgba(255,255,255,0.35);font-size:0.85rem;font-family:'Inter',sans-serif;margin:0 0 2rem 0;line-height:1.6;">
                  Match exactly the model IDs in
                  <code style="color:#E8290B;background:rgba(232,41,11,0.12);padding:0.1rem 0.35rem;font-size:0.8rem;">providers.py</code>.
                  No vendored adapters, no surprises.
                </p>
                <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:0.75rem;">
                  <div style="border:1px solid rgba(255,255,255,0.08);padding:1rem;background:rgba(255,255,255,0.02);">
                    <div style="color:rgba(255,255,255,0.25);font-size:8px;letter-spacing:0.12em;margin-bottom:0.5rem;font-family:'Inter',sans-serif;">GROQ</div>
                    <div style="color:rgba(255,255,255,0.5);font-size:0.7rem;font-family:'Inter',sans-serif;line-height:1.8;">
                      llama3-8b-8192<br>mixtral-8x7b-32768
                    </div>
                  </div>
                  <div style="border:1px solid rgba(255,255,255,0.08);padding:1rem;background:rgba(255,255,255,0.02);">
                    <div style="color:rgba(255,255,255,0.25);font-size:8px;letter-spacing:0.12em;margin-bottom:0.5rem;font-family:'Inter',sans-serif;">CLAUDE</div>
                    <div style="color:rgba(255,255,255,0.5);font-size:0.7rem;font-family:'Inter',sans-serif;line-height:1.8;">
                      claude-haiku-3<br>claude-sonnet-3
                    </div>
                  </div>
                  <div style="border:1px solid rgba(255,255,255,0.08);padding:1rem;background:rgba(255,255,255,0.02);">
                    <div style="color:rgba(255,255,255,0.25);font-size:8px;letter-spacing:0.12em;margin-bottom:0.5rem;font-family:'Inter',sans-serif;">GPT</div>
                    <div style="color:rgba(255,255,255,0.5);font-size:0.7rem;font-family:'Inter',sans-serif;line-height:1.8;">
                      gpt-4o-mini<br>gpt-4o
                    </div>
                  </div>
                  <div style="border:1px solid rgba(255,255,255,0.08);padding:1rem;background:rgba(255,255,255,0.02);">
                    <div style="color:rgba(255,255,255,0.25);font-size:8px;letter-spacing:0.12em;margin-bottom:0.5rem;font-family:'Inter',sans-serif;">GEMINI</div>
                    <div style="color:rgba(255,255,255,0.5);font-size:0.7rem;font-family:'Inter',sans-serif;line-height:1.8;">
                      gemini-1.5-flash<br>gemini-1.5-pro
                    </div>
                  </div>
                  <div style="border:1px solid rgba(255,255,255,0.08);padding:1rem;background:rgba(255,255,255,0.02);">
                    <div style="color:rgba(255,255,255,0.25);font-size:8px;letter-spacing:0.12em;margin-bottom:0.5rem;font-family:'Inter',sans-serif;">MISTRAL</div>
                    <div style="color:rgba(255,255,255,0.5);font-size:0.7rem;font-family:'Inter',sans-serif;line-height:1.8;">
                      mistral-7b-instruct<br>mixtral-8x7b
                    </div>
                  </div>
                  <div style="border:1px solid rgba(255,255,255,0.08);padding:1rem;background:rgba(255,255,255,0.02);">
                    <div style="color:rgba(255,255,255,0.25);font-size:8px;letter-spacing:0.12em;margin-bottom:0.5rem;font-family:'Inter',sans-serif;">PHI</div>
                    <div style="color:rgba(255,255,255,0.5);font-size:0.7rem;font-family:'Inter',sans-serif;line-height:1.8;">
                      phi-3-mini<br>phi-3-medium
                    </div>
                  </div>
                </div>
              </div>

              <!-- ════ DIVIDER ════ -->
              <div style="border-top:1px solid rgba(255,255,255,0.08);margin:3rem 0;"></div>

              <!-- ════ SECTION 5: RAG PIPELINE ════ -->
              <div style="margin-bottom:0;">
                <div style="font-size:9px;color:#E8290B;letter-spacing:0.2em;margin-bottom:1.25rem;">— RAG PIPELINE</div>
                <div style="color:white;font-size:2rem;font-weight:800;letter-spacing:-0.02em;line-height:1.1;margin-bottom:0.6rem;">
                  RAG Pipeline?<br>We measure that too.
                </div>
                <p style="color:rgba(255,255,255,0.35);font-size:0.85rem;font-family:'Inter',sans-serif;margin:0 0 1.75rem 0;line-height:1.6;">
                  Standard RAG evals miss retrieval quality. We don't.
                </p>

                <div style="display:flex;flex-wrap:wrap;gap:0.5rem;margin-bottom:1.5rem;">
                  <span style="border:1px solid rgba(255,255,255,0.15);color:rgba(255,255,255,0.6);
                               padding:0.3rem 0.75rem;font-size:0.75rem;font-family:'Inter',sans-serif;">Precision@K</span>
                  <span style="border:1px solid rgba(255,255,255,0.15);color:rgba(255,255,255,0.6);
                               padding:0.3rem 0.75rem;font-size:0.75rem;font-family:'Inter',sans-serif;">Recall@K</span>
                  <span style="border:1px solid rgba(255,255,255,0.15);color:rgba(255,255,255,0.6);
                               padding:0.3rem 0.75rem;font-size:0.75rem;font-family:'Inter',sans-serif;">MRR</span>
                  <span style="border:1px solid rgba(255,255,255,0.15);color:rgba(255,255,255,0.6);
                               padding:0.3rem 0.75rem;font-size:0.75rem;font-family:'Inter',sans-serif;">NDCG</span>
                </div>

                <div style="border:1px solid rgba(232,41,11,0.2);background:rgba(232,41,11,0.05);
                            padding:1rem 1.25rem;margin-bottom:1.75rem;">
                  <div style="color:rgba(255,255,255,0.25);font-size:8px;letter-spacing:0.12em;
                              margin-bottom:0.5rem;font-family:'Inter',sans-serif;">RAG SCORE FORMULA</div>
                  <div style="color:rgba(255,255,255,0.65);font-size:0.82rem;font-family:'Inter',sans-serif;">
                    40% Relevance &nbsp;+&nbsp; 40% Completeness &nbsp;+&nbsp; 20% Source Count
                  </div>
                </div>

                <button style="background:#E8290B;color:white;border:none;border-radius:0;
                               padding:0.75rem 1.75rem;font-size:0.8rem;font-weight:700;cursor:pointer;
                               font-family:'Syne',sans-serif;letter-spacing:0.1em;text-transform:uppercase;"
                        onclick="this.textContent='SIGN IN TO ACCESS';setTimeout(function(){this.textContent='TRY RAG TESTING →';}.bind(this),2500)">
                  TRY RAG TESTING →
                </button>
              </div>

              <!-- ════ FOOTER ════ -->
              <div style="border-top:1px solid rgba(255,255,255,0.06);margin-top:3rem;padding-top:1.5rem;">
                <p style="color:rgba(255,255,255,0.15);font-size:0.7rem;margin:0;font-family:'Inter',sans-serif;">
                  Built by <a href="https://www.linkedin.com/in/monika-kushwaha-52443735/" target="_blank"
                  style="color:#E8290B;text-decoration:none;">Monika Kushwaha</a>
                </p>
              </div>

            </div>
        """)
        # Blank lines in HTML make Markdown treat indented tags as code blocks — strip them.
        _lp = "\n".join(ln for ln in _lp.splitlines() if ln.strip())
        st.markdown(_lp, unsafe_allow_html=True)

    # ── RIGHT PANEL: off-white auth form ──────────────────────────────
    with right_col:
        st.markdown("<div style='height:8vh'></div>", unsafe_allow_html=True)

        st.markdown(_h("""
            <div style="padding:0 1rem;font-family:'Syne',sans-serif;">
              <!-- Mini logo -->
              <div style="display:flex;align-items:center;gap:10px;margin-bottom:2.5rem;">
                <div style="background:#E8290B;width:32px;height:32px;
                            display:flex;align-items:center;justify-content:center;
                            font-family:'Syne',sans-serif;font-size:15px;font-weight:800;color:white;">T</div>
                <span style="color:#0E0E0E;font-size:1rem;font-weight:800;letter-spacing:0.02em;">TrustLLM</span>
              </div>

              <!-- Section label -->
              <div style="font-size:9px;color:#E8290B;letter-spacing:0.2em;margin-bottom:0.75rem;">
                — AUTHENTICATION
              </div>

              <!-- Heading -->
              <div style="color:#0E0E0E;font-size:1.9rem;font-weight:800;letter-spacing:-0.025em;
                          line-height:1.1;margin:0 0 0.4rem 0;">
                Welcome back.
              </div>
              <p style="color:#888888;font-size:0.85rem;margin:0 0 2rem 0;
                        font-family:'Inter',sans-serif;font-weight:300;">
                Sign in to your evaluation workspace.
              </p>
            </div>
        """), unsafe_allow_html=True)

        # ── Social login buttons ──────────────────────────────────────
        st.markdown(_h("""
            <div style="padding:0 1rem;margin-bottom:0.75rem;">
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;margin-bottom:1rem;">
                <button style="background:white;color:#0E0E0E;border:1px solid #E4E2DC;border-radius:0;
                               padding:0.65rem 1rem;font-size:0.78rem;font-weight:600;cursor:pointer;
                               width:100%;font-family:'Syne',sans-serif;letter-spacing:0.04em;"
                        onclick="var b=this;b.textContent='NOT AVAILABLE IN DEMO';
                                 setTimeout(function(){b.textContent='🔵 GOOGLE'},2500)">
                  🔵 GOOGLE
                </button>
                <button style="background:#0E0E0E;color:white;border:1px solid #0E0E0E;border-radius:0;
                               padding:0.65rem 1rem;font-size:0.78rem;font-weight:600;cursor:pointer;
                               width:100%;font-family:'Syne',sans-serif;letter-spacing:0.04em;"
                        onclick="var b=this;b.textContent='NOT AVAILABLE IN DEMO';
                                 setTimeout(function(){b.textContent='⬛ GITHUB'},2500)">
                  ⬛ GITHUB
                </button>
              </div>
              <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:1.25rem;">
                <div style="flex:1;border-top:1px solid #E4E2DC;"></div>
                <span style="color:#888888;font-size:0.72rem;white-space:nowrap;
                             font-family:'Inter',sans-serif;">or sign in with credentials</span>
                <div style="flex:1;border-top:1px solid #E4E2DC;"></div>
              </div>
            </div>
        """), unsafe_allow_html=True)

        # ── Credentials form ─────────────────────────────────────────
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submitted = st.form_submit_button("Sign in →", use_container_width=True)

        if submitted:
            user = _authenticate(username, password)
            if user:
                st.session_state["logged_in"] = True
                st.session_state["user"] = user
                st.rerun()
            else:
                st.error("Invalid username or password.")

        st.markdown(_h("""
            <div style="padding:0 1rem;">
              <p style="color:#888888;font-size:0.75rem;text-align:center;margin-top:1rem;
                        font-family:'Inter',sans-serif;">
                Demo — Username: <strong style="color:#0E0E0E;">TestUser</strong>
                &nbsp;·&nbsp; Password: <strong style="color:#0E0E0E;">User123</strong>
              </p>
              <div style="margin-top:2rem;padding-top:1.25rem;border-top:1px solid #E4E2DC;">
                <p style="color:#888888;font-size:0.72rem;text-align:center;margin:0;
                          font-family:'Inter',sans-serif;">
                  © 2025 TrustLLM · AI Model Evaluation Platform
                </p>
              </div>
            </div>
        """), unsafe_allow_html=True)


# -----------------------------------------------
# ONBOARDING FLOW  —  VERDICT style
# -----------------------------------------------
def _step_indicator(current: int, total: int = 3):
    dots = ""
    for i in range(1, total + 1):
        if i < current:
            cls = "done"
        elif i == current:
            cls = "active"
        else:
            cls = ""
        dots += f'<div class="step-dot {cls}"></div>'
    st.markdown(
        f'<div class="step-track">{dots}'
        f'<span style="font-size:0.72rem;color:#888888;margin-left:8px;font-family:Inter,sans-serif;">Step {current} of {total}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _show_onboarding():
    step = st.session_state.get("onboarding_step", 1)

    st.markdown(_h("""
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .stApp { background: #F9F8F6 !important; }
        section.main .block-container {
            max-width: 720px !important;
            padding-top: 4vh !important;
            margin: 0 auto;
        }
        div[data-testid="stCheckbox"] label,
        div[data-testid="stCheckbox"] label p,
        div[data-testid="stCheckbox"] label span {
            color: #0E0E0E !important;
            font-size: 0.875rem !important;
            font-weight: 500 !important;
        }
        </style>
        <link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
    """), unsafe_allow_html=True)

    # ── Step 1: Welcome ────────────────────────────────────────────────
    if step == 1:
        st.markdown(_h("""
            <div style="text-align:center;margin-bottom:2.5rem;">
              <div style="background:#E8290B;width:56px;height:56px;
                          display:inline-flex;align-items:center;justify-content:center;
                          font-family:'Syne',sans-serif;font-size:28px;font-weight:800;color:white;
                          margin-bottom:1.25rem;">T</div>
              <div style="font-family:'Syne',sans-serif;font-size:9px;letter-spacing:0.2em;
                          color:#E8290B;margin-bottom:0.75rem;">— GETTING STARTED</div>
              <h1 style="color:#0E0E0E;font-size:2rem;font-weight:800;font-family:'Syne',sans-serif;
                         letter-spacing:-0.025em;margin:0 0 0.5rem 0;">Welcome to TrustLLM.</h1>
              <p style="color:#888888;font-size:0.9rem;max-width:480px;margin:0 auto;
                        line-height:1.6;font-family:'Inter',sans-serif;">
                Let's get your evaluation workspace ready in
                <strong style="color:#E8290B;">2 quick steps.</strong>
                Your first eval takes less than a minute.
              </p>
            </div>
        """), unsafe_allow_html=True)

        _step_indicator(1)

        col1, col2, col3 = st.columns(3)
        cards = [
            ("📊", "Trace & Observe", "Inspect every prompt and response in real time"),
            ("⚡", "Run Evals", "Score outputs with LLM judges and custom scorers"),
            ("🏆", "Compare Models", "Rank models by trust score, safety & cost"),
        ]
        for col, (icon, title, desc) in zip([col1, col2, col3], cards):
            with col:
                st.markdown(_h(f"""
                    <div style="background:white;border:1px solid #E4E2DC;border-radius:0;
                                padding:1.25rem;text-align:center;">
                      <div style="font-size:1.5rem;margin-bottom:0.6rem;">{icon}</div>
                      <div style="font-weight:800;font-size:0.85rem;color:#0E0E0E;
                                  font-family:'Syne',sans-serif;margin-bottom:0.3rem;">{title}</div>
                      <div style="font-size:0.75rem;color:#888888;line-height:1.4;
                                  font-family:'Inter',sans-serif;">{desc}</div>
                    </div>
                """), unsafe_allow_html=True)

        st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)

        _, btn_col, _ = st.columns([1, 2, 1])
        with btn_col:
            if st.button("Let's get started →", use_container_width=True, key="ob_step1"):
                st.session_state["onboarding_step"] = 2
                st.rerun()

        _, skip_col, _ = st.columns([1, 2, 1])
        with skip_col:
            st.markdown('<div class="btn-secondary">', unsafe_allow_html=True)
            if st.button("Skip setup — go to dashboard", key="ob_skip", use_container_width=True):
                st.session_state["onboarding_complete"] = True
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    # ── Step 2: Evaluation focus ───────────────────────────────────────
    elif step == 2:
        st.markdown(_h("""
            <div style="font-family:'Syne',sans-serif;font-size:9px;letter-spacing:0.2em;
                        color:#E8290B;margin-bottom:0.5rem;">— STEP TWO</div>
            <h1 style="color:#0E0E0E;font-size:1.8rem;font-weight:800;font-family:'Syne',sans-serif;
                       letter-spacing:-0.025em;margin:0 0 0.4rem 0;">What will you evaluate?</h1>
            <p style="color:#888888;font-size:0.9rem;margin:0 0 1.5rem 0;line-height:1.6;
                      font-family:'Inter',sans-serif;">
              Select one or more evaluation categories. You can change this later.
            </p>
        """), unsafe_allow_html=True)

        _step_indicator(2)

        focus_options = [
            ("safety",        "🔒", "Safety Testing",  "Jailbreak resistance, harmful content detection"),
            ("factual",       "📋", "Factual QA",       "Accuracy, reasoning, knowledge retrieval"),
            ("bias",          "⚖️", "Bias Audit",       "Fairness, demographic bias, toxicity"),
            ("hallucination", "🔍", "Hallucination",    "Grounding, factual consistency, RAG fidelity"),
            ("reasoning",     "🧠", "Reasoning",        "Multi-step logic, chain-of-thought quality"),
        ]

        selected = st.session_state.get("ob_focus", [])
        new_selected = []

        for row_start in range(0, len(focus_options), 3):
            row = focus_options[row_start:row_start + 3]
            cols = st.columns(3)
            for col, (key, icon, title, desc) in zip(cols, row):
                is_sel = key in selected
                with col:
                    border = "#E8290B" if is_sel else "#E4E2DC"
                    bg = "#FEF2F0" if is_sel else "white"
                    st.markdown(_h(f"""
                        <div style="background:{bg};border:2px solid {border};border-radius:0;
                                    padding:1rem 1rem 0.25rem 1rem;">
                          <div style="font-size:1.4rem;margin-bottom:0.3rem;">{icon}</div>
                          <div style="font-weight:800;font-size:0.85rem;color:#0E0E0E;
                                      font-family:'Syne',sans-serif;margin-bottom:0.2rem;">{title}</div>
                          <div style="font-size:0.72rem;color:#888888;line-height:1.4;
                                      margin-bottom:0.5rem;font-family:'Inter',sans-serif;">{desc}</div>
                        </div>
                    """), unsafe_allow_html=True)
                    checked = st.checkbox(
                        title,
                        value=is_sel,
                        key=f"ob_focus_{key}",
                        label_visibility="collapsed",
                    )
                    if checked:
                        new_selected.append(key)

        st.session_state["ob_focus"] = new_selected

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        _, btn_col, _ = st.columns([1, 2, 1])
        with btn_col:
            if st.button(
                "Continue →",
                use_container_width=True,
                key="ob_step2",
                disabled=(len(new_selected) == 0),
            ):
                st.session_state["onboarding_step"] = 3
                st.rerun()

        _, back_col, _ = st.columns([1, 2, 1])
        with back_col:
            st.markdown('<div class="btn-secondary">', unsafe_allow_html=True)
            if st.button("← Back", key="ob_back2", use_container_width=True):
                st.session_state["onboarding_step"] = 1
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    # ── Step 3: Model selection ────────────────────────────────────────
    elif step == 3:
        st.markdown(_h("""
            <div style="font-family:'Syne',sans-serif;font-size:9px;letter-spacing:0.2em;
                        color:#E8290B;margin-bottom:0.5rem;">— STEP THREE</div>
            <h1 style="color:#0E0E0E;font-size:1.8rem;font-weight:800;font-family:'Syne',sans-serif;
                       letter-spacing:-0.025em;margin:0 0 0.4rem 0;">Which models will you evaluate?</h1>
            <p style="color:#888888;font-size:0.9rem;margin:0 0 1.5rem 0;line-height:1.6;
                      font-family:'Inter',sans-serif;">
              Choose AI models to benchmark. You can add more later from the evaluation page.
            </p>
        """), unsafe_allow_html=True)

        _step_indicator(3)

        model_options = [
            ("gpt",        "GPT-4o",     "OpenAI",     "Versatile, strong reasoning"),
            ("claude",     "Claude 3",   "Anthropic",  "Safety-first, long context"),
            ("gemini-pro", "Gemini Pro", "Google",     "Multimodal, fast inference"),
            ("mistral",    "Mistral 7B", "Mistral AI", "Open-source, efficient"),
            ("phi3",       "Phi-3",      "Microsoft",  "Compact, high accuracy"),
            ("llama",      "LLaMA 3",    "Meta",       "Open-source, customizable"),
        ]

        selected_models = st.session_state.get("ob_models", ["gpt", "claude"])
        new_models = []

        for row_start in range(0, len(model_options), 3):
            row = model_options[row_start:row_start + 3]
            cols = st.columns(3)
            for col, (key, name, vendor, desc) in zip(cols, row):
                is_sel = key in selected_models
                with col:
                    st.markdown(_h(f"""
                        <div style="background:{'#FEF2F0' if is_sel else 'white'};
                                    border:2px solid {'#E8290B' if is_sel else '#E4E2DC'};
                                    border-radius:0;padding:0.9rem 1rem 0.25rem 1rem;">
                          <div style="font-weight:800;font-size:0.9rem;color:#0E0E0E;
                                      font-family:'Syne',sans-serif;">{name}</div>
                          <div style="font-size:0.7rem;color:#E8290B;font-weight:700;
                                      font-family:'Syne',sans-serif;margin:0.1rem 0 0.3rem;">{vendor}</div>
                          <div style="font-size:0.72rem;color:#888888;line-height:1.3;
                                      margin-bottom:0.5rem;font-family:'Inter',sans-serif;">{desc}</div>
                        </div>
                    """), unsafe_allow_html=True)
                    checked = st.checkbox(
                        name,
                        value=is_sel,
                        key=f"ob_model_{key}",
                        label_visibility="collapsed",
                    )
                    if checked:
                        new_models.append(key)

        st.session_state["ob_models"] = new_models

        if new_models:
            focus_labels = {
                "safety": "Safety", "factual": "Factual QA", "bias": "Bias Audit",
                "hallucination": "Hallucination", "reasoning": "Reasoning",
            }
            focus_str = ", ".join(
                focus_labels.get(f, f) for f in st.session_state.get("ob_focus", [])
            ) or "All categories"
            model_str = ", ".join(m.upper() for m in new_models)
            st.markdown(_h(f"""
                <div style="background:#F0FDF4;border:1px solid #BBF7D0;border-radius:0;
                            padding:1rem 1.25rem;margin:1rem 0;">
                  <div style="font-size:0.78rem;font-weight:700;color:#15803D;
                              font-family:'Syne',sans-serif;letter-spacing:0.04em;margin-bottom:0.35rem;">
                    ✓ WORKSPACE IS READY
                  </div>
                  <div style="font-size:0.82rem;color:#166534;font-family:'Inter',sans-serif;">
                    <strong>Focus:</strong> {focus_str}<br>
                    <strong>Models:</strong> {model_str}
                  </div>
                </div>
            """), unsafe_allow_html=True)

        _, btn_col, _ = st.columns([1, 2, 1])
        with btn_col:
            if st.button(
                "Launch Dashboard →",
                use_container_width=True,
                key="ob_launch",
                disabled=(len(new_models) == 0),
            ):
                st.session_state["onboarding_complete"] = True
                st.session_state["project_categories"] = st.session_state.get("ob_focus") or None
                st.rerun()

        _, back_col, _ = st.columns([1, 2, 1])
        with back_col:
            st.markdown('<div class="btn-secondary">', unsafe_allow_html=True)
            if st.button("← Back", key="ob_back3", use_container_width=True):
                st.session_state["onboarding_step"] = 2
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)


# -----------------------------------------------
# AUTH GATE
# -----------------------------------------------
if not st.session_state.get("logged_in"):
    _show_login()
    st.stop()

# -----------------------------------------------
# ONBOARDING GATE
# -----------------------------------------------
if not st.session_state.get("onboarding_complete"):
    _show_onboarding()
    st.stop()


# ===============================================
# AUTHENTICATED APP
# ===============================================

with open(BASE_DIR / "projects.json") as _pf:
    _projects_data = json.load(_pf)["projects"]
_project_names = ["All Projects"] + [p["name"] for p in _projects_data]

# -----------------------------------------------
# TOP HEADER BAR  —  VERDICT style
# -----------------------------------------------
header = st.container()
with header:
    h1, h2, h3, h4, h5 = st.columns([1.2, 2, 2, 0.8, 0.8])
    with h1:
        st.markdown(_h("""
            <div style="display:flex;align-items:center;gap:8px;padding-top:0.3rem;">
              <div style="background:#E8290B;width:26px;height:26px;
                          display:flex;align-items:center;justify-content:center;
                          font-family:'Syne',sans-serif;font-size:13px;font-weight:800;color:white;">T</div>
              <span style="font-weight:800;color:#0E0E0E;font-size:0.95rem;
                           font-family:'Syne',sans-serif;letter-spacing:0.02em;">TrustLLM</span>
            </div>
        """), unsafe_allow_html=True)
    with h2:
        selected_project = st.selectbox("Project", _project_names, label_visibility="collapsed")
    with h3:
        selected_env = st.selectbox(
            "Environment", ["production", "staging", "development"], label_visibility="collapsed"
        )
    with h4:
        st.markdown(
            '<a href="https://github.com/" target="_blank" class="header-btn">DOCS</a>',
            unsafe_allow_html=True,
        )
    with h5:
        st.markdown('<a href="#compare" class="header-btn">COMPARE</a>', unsafe_allow_html=True)

st.markdown('<hr class="header-divider">', unsafe_allow_html=True)

_selected_categories = None
if selected_project != "All Projects":
    for p in _projects_data:
        if p["name"] == selected_project:
            _selected_categories = p["categories"]
            break

st.session_state["project_categories"] = _selected_categories

# -----------------------------------------------
# SIDEBAR  —  VERDICT style
# -----------------------------------------------
user = st.session_state["user"]

st.sidebar.markdown(_h(f"""
    <div style="padding:0.75rem 0 0.5rem 0;">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:1rem;padding:0 4px;">
        <div style="background:#E8290B;width:32px;height:32px;
                    display:flex;align-items:center;justify-content:center;
                    font-family:'Syne',sans-serif;font-size:16px;font-weight:800;color:white;">T</div>
        <div>
          <div style="font-size:0.95rem;font-weight:800;color:white;
                      font-family:'Syne',sans-serif;letter-spacing:0.02em;">TrustLLM</div>
          <div style="font-size:7px;color:rgba(255,255,255,0.2);letter-spacing:0.15em;
                      font-family:'Syne',sans-serif;">EVAL PLATFORM</div>
        </div>
      </div>
      <div style="display:flex;align-items:center;gap:8px;padding:0.65rem 0.75rem;
                  background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.07);
                  margin-bottom:0.5rem;">
        <div style="background:#E8290B;width:30px;height:30px;
                    display:flex;align-items:center;justify-content:center;
                    font-family:'Syne',sans-serif;font-size:13px;font-weight:800;
                    color:white;flex-shrink:0;">
          {user['display_name'][0].upper()}
        </div>
        <div>
          <div style="font-size:0.82rem;font-weight:700;color:rgba(255,255,255,0.85);
                      font-family:'Syne',sans-serif;line-height:1.2;">{user['display_name']}</div>
          <div style="font-size:0.68rem;color:rgba(255,255,255,0.3);
                      font-family:'Syne',sans-serif;letter-spacing:0.08em;
                      text-transform:uppercase;">{user.get('role','viewer')}</div>
        </div>
      </div>
    </div>
"""), unsafe_allow_html=True)

if "page" not in st.session_state:
    st.session_state["page"] = "Overview"

_nav_css = _h("""
    <style>
    section[data-testid="stSidebar"] div[data-testid="stButton"] button {
        background: transparent !important;
        color: rgba(255,255,255,0.45) !important;
        border: none !important;
        border-left: 3px solid transparent !important;
        text-align: left !important;
        padding: 0.4rem 0.75rem !important;
        font-size: 0.82rem !important;
        font-weight: 500 !important;
        border-radius: 0 !important;
        box-shadow: none !important;
        width: 100%;
        justify-content: flex-start !important;
        font-family: 'Inter', sans-serif !important;
        text-transform: none !important;
        letter-spacing: 0.01em !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stButton"] button:hover {
        background: rgba(255,255,255,0.04) !important;
        color: rgba(255,255,255,0.8) !important;
        box-shadow: none !important;
    }
    section[data-testid="stSidebar"] .nav-active div[data-testid="stButton"] button {
        background: rgba(232,41,11,0.1) !important;
        color: white !important;
        font-weight: 600 !important;
        border-left: 3px solid #E8290B !important;
    }
    </style>
""")
st.sidebar.markdown(_nav_css, unsafe_allow_html=True)


def _nav_item(label: str, icon: str):
    is_active = st.session_state.get("page") == label
    if is_active:
        st.sidebar.markdown('<div class="nav-active">', unsafe_allow_html=True)
    if st.sidebar.button(f"{icon}  {label}", key=f"nav_{label}", use_container_width=True):
        st.session_state["page"] = label
        st.rerun()
    if is_active:
        st.sidebar.markdown("</div>", unsafe_allow_html=True)


st.sidebar.markdown('<p class="nav-section">MONITOR</p>', unsafe_allow_html=True)
_nav_item("Overview", "◎")
_nav_item("Failure Analysis", "✕")

st.sidebar.markdown('<p class="nav-section">EVALUATE</p>', unsafe_allow_html=True)
_nav_item("Run Evaluation", "▶")
_nav_item("Leaderboard", "🏆")
_nav_item("Agent Performance", "⚡")

st.sidebar.markdown('<p class="nav-section">DATA</p>', unsafe_allow_html=True)
_nav_item("Prompt Explorer", "🔍")
_nav_item("Prompt Dataset", "📂")
_nav_item("RAG Testing", "🧪")

st.sidebar.divider()

if st.sidebar.button("Sign out", use_container_width=True):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

st.sidebar.markdown(_h("""
    <p style="font-size:0.65rem;color:rgba(255,255,255,0.15);text-align:center;
              margin-top:0.5rem;font-family:'Syne',sans-serif;letter-spacing:0.08em;">
      TRUSTLLM · LLM EVAL TOOLKIT
    </p>
"""), unsafe_allow_html=True)

page = st.session_state.get("page", "Overview")

# -----------------------------------------------
# PAGE ROUTER
# -----------------------------------------------
if page == "Overview":
    overview()
elif page == "Failure Analysis":
    failure_analysis()
elif page == "Run Evaluation":
    run_eval()
elif page == "Leaderboard":
    leaderboard()
elif page == "Agent Performance":
    agent_performance()
elif page == "Prompt Explorer":
    prompt_explorer()
elif page == "Prompt Dataset":
    prompt_dataset()
elif page == "RAG Testing":
    rag_testing()
