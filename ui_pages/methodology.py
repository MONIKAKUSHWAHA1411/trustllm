import streamlit as st


def render():
    st.title("TrustLLM Methodology")
    st.caption("How TrustLLM evaluates, scores, and benchmarks language models.")
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    # ── intro blurb ──────────────────────────────────────────────────────────
    st.markdown("""
<div style="background:white;border:1px solid #e5e7eb;border-radius:12px;
            padding:1.5rem;margin-bottom:1.5rem;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
  <p style="color:#374151;font-size:0.95rem;line-height:1.75;margin:0;">
    TrustLLM measures how much you can <strong>rely</strong> on an LLM's outputs — not just
    whether they sound good, but whether they are truthful, safe, fair, private, robust,
    and ethical. This page explains exactly how evaluations work, how scores are calculated,
    and what TrustLLM does <em>not</em> measure.
  </p>
</div>
""", unsafe_allow_html=True)

    # ── Section 1: What TrustLLM Measures ───────────────────────────────────
    st.subheader("1. What TrustLLM Measures")
    st.markdown(
        "TrustLLM evaluates model outputs across **six trust dimensions**. "
        "Each dimension probes a distinct failure mode that matters in production AI systems."
    )

    dimensions = [
        (
            "🔍", "Truthfulness / Hallucination Detection",
            "Measures whether the model's factual claims are grounded in its context or "
            "verified knowledge. Responses are classified as *Grounded* or "
            "*Possible Hallucination* using pattern-matching and semantic-similarity checks "
            "against expected answers.",
        ),
        (
            "🔒", "Safety",
            "Scores the model's resistance to generating harmful, violent, or dangerous "
            "content and its ability to refuse jailbreak attempts. Evaluated via keyword "
            "detection and a dedicated safety sub-score from the LLM judge.",
        ),
        (
            "⚖️", "Fairness & Bias",
            "Detects demographic bias, toxic language, and unfair differential treatment "
            "across groups. Prompts are drawn from bias audit datasets and flagged "
            "when `bias_violation` is detected.",
        ),
        (
            "🔐", "Privacy",
            "Checks whether the model inappropriately reveals, infers, or requests "
            "personally identifiable information (PII). Privacy-sensitive prompts are "
            "included in evaluation datasets and responses are audited for leakage.",
        ),
        (
            "🛡️", "Robustness",
            "Tests how consistent the model's outputs are when prompts are paraphrased, "
            "when noise is injected, or when adversarial rephrasing is used. "
            "Consistency across variants is factored into the composite Trust Score.",
        ),
        (
            "🧭", "Ethics",
            "Evaluates whether responses adhere to broadly accepted ethical norms — "
            "avoiding manipulation, deception, and morally problematic guidance. "
            "Assessed by the LLM-as-Judge scorer with ethics-focused rubrics.",
        ),
    ]

    for icon, title, desc in dimensions:
        st.markdown(f"""
<div style="display:flex;gap:1rem;align-items:flex-start;
            background:white;border:1px solid #e5e7eb;border-radius:10px;
            padding:1rem 1.25rem;margin-bottom:0.75rem;
            box-shadow:0 1px 3px rgba(0,0,0,0.04);">
  <div style="font-size:1.5rem;flex-shrink:0;line-height:1.4;">{icon}</div>
  <div>
    <div style="font-weight:700;font-size:0.9rem;color:#111827;margin-bottom:0.25rem;">{title}</div>
    <div style="font-size:0.84rem;color:#6b7280;line-height:1.6;">{desc}</div>
  </div>
</div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Section 2: How Scoring Works ─────────────────────────────────────────
    st.subheader("2. How Scoring Works")

    st.markdown("""
**Evaluation approach — LLM-as-Judge**

Each prompt/response pair is scored by a separate judge model that applies structured
rubrics for correctness, relevance, clarity, and safety. The judge is distinct from the
model under evaluation, which reduces self-serving bias.
""")

    st.markdown("""
<div style="background:white;border:1px solid #e5e7eb;border-radius:12px;
            padding:1.25rem 1.5rem;margin-bottom:1rem;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
  <div style="font-size:0.75rem;font-weight:700;color:#6b7280;text-transform:uppercase;
              letter-spacing:0.06em;margin-bottom:0.875rem;">Composite Trust Score Formula</div>

  <div style="display:flex;align-items:center;gap:0.5rem;flex-wrap:wrap;margin-bottom:1rem;">
    <div style="background:#4f46e5;color:white;border-radius:8px;padding:0.5rem 1rem;
                font-weight:700;font-size:0.875rem;white-space:nowrap;">Trust Score</div>
    <span style="font-size:1.1rem;color:#9ca3af;">=</span>
    <div style="background:#ede9fe;color:#6d28d9;border-radius:8px;padding:0.5rem 1rem;
                font-weight:600;font-size:0.8rem;white-space:nowrap;">Hallucination (20%)</div>
    <span style="color:#9ca3af;">+</span>
    <div style="background:#ede9fe;color:#6d28d9;border-radius:8px;padding:0.5rem 1rem;
                font-weight:600;font-size:0.8rem;white-space:nowrap;">Correctness (20%)</div>
    <span style="color:#9ca3af;">+</span>
    <div style="background:#ede9fe;color:#6d28d9;border-radius:8px;padding:0.5rem 1rem;
                font-weight:600;font-size:0.8rem;white-space:nowrap;">Relevance (20%)</div>
    <span style="color:#9ca3af;">+</span>
    <div style="background:#ede9fe;color:#6d28d9;border-radius:8px;padding:0.5rem 1rem;
                font-weight:600;font-size:0.8rem;white-space:nowrap;">Clarity (20%)</div>
    <span style="color:#9ca3af;">+</span>
    <div style="background:#ede9fe;color:#6d28d9;border-radius:8px;padding:0.5rem 1rem;
                font-weight:600;font-size:0.8rem;white-space:nowrap;">Safety (20%)</div>
  </div>

  <div style="background:#f8fafc;border-radius:8px;padding:0.875rem 1rem;">
    <div style="font-size:0.78rem;font-weight:600;color:#374151;margin-bottom:0.5rem;">
      Confidence Score (per-response quality signal)
    </div>
    <div style="display:flex;gap:0.5rem;flex-wrap:wrap;">
      <div style="background:white;border:1px solid #e5e7eb;border-radius:6px;
                  padding:0.35rem 0.75rem;font-size:0.75rem;color:#374151;">
        40% — Response Quality
      </div>
      <div style="background:white;border:1px solid #e5e7eb;border-radius:6px;
                  padding:0.35rem 0.75rem;font-size:0.75rem;color:#374151;">
        40% — Consistency (cross-variant)
      </div>
      <div style="background:white;border:1px solid #e5e7eb;border-radius:6px;
                  padding:0.35rem 0.75rem;font-size:0.75rem;color:#374151;">
        20% — Calibration
      </div>
    </div>
  </div>

  <p style="font-size:0.78rem;color:#9ca3af;margin:0.75rem 0 0 0;">
    All sub-scores are on a 0–1 scale. A Trust Score ≥ 0.8 is green, ≥ 0.6 is amber, &lt; 0.6 is red.
    For agent evaluations a different formula applies:
    <code style="font-size:0.75rem;">0.35 × semantic_avg + 0.35 × hallucination_score + 0.30 × tool_accuracy</code>.
  </p>
</div>
""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Section 3: RAG Evaluation ─────────────────────────────────────────────
    st.subheader("3. How RAG Evaluation Works")

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("""
<div style="background:white;border:1px solid #e5e7eb;border-radius:10px;
            padding:1.1rem 1.25rem;height:100%;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
  <div style="font-weight:700;font-size:0.875rem;color:#111827;margin-bottom:0.5rem;">
    📄 What RAG Evaluation Tests
  </div>
  <ul style="color:#6b7280;font-size:0.82rem;line-height:1.7;margin:0;padding-left:1.2rem;">
    <li>Retrieval accuracy — does the pipeline surface the right document chunks?</li>
    <li>Answer grounding — is the final answer supported by retrieved context?</li>
    <li>Faithfulness — does the answer stay within retrieved facts?</li>
    <li>Context relevance — how well do retrieved chunks match the query?</li>
    <li>Hallucination risk — semantic distance between answer and source chunks</li>
  </ul>
</div>
""", unsafe_allow_html=True)

    with col_b:
        st.markdown("""
<div style="background:white;border:1px solid #e5e7eb;border-radius:10px;
            padding:1.1rem 1.25rem;height:100%;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
  <div style="font-weight:700;font-size:0.875rem;color:#111827;margin-bottom:0.5rem;">
    🔬 How It Differs from Standard Evals
  </div>
  <ul style="color:#6b7280;font-size:0.82rem;line-height:1.7;margin:0;padding-left:1.2rem;">
    <li>Uses cosine similarity between embeddings — no external LLM judge required</li>
    <li>Embeddings use <code>all-MiniLM-L6-v2</code> via ChromaDB's ONNX runtime</li>
    <li>Pass threshold: cosine similarity ≥ 0.55 vs expected answer</li>
    <li>Batch evaluation accepts CSV/JSON datasets for systematic pipeline testing</li>
    <li>Source chunks are captured per-response for full retrieval transparency</li>
  </ul>
</div>
""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Section 4: Capability Benchmarks (AA) ────────────────────────────────
    st.subheader("4. Capability Benchmarks")

    st.markdown("""
<div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:12px;
            padding:1.5rem;margin-bottom:1rem;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
  <div style="display:flex;align-items:flex-start;gap:1rem;">
    <div style="font-size:1.75rem;flex-shrink:0;">⚡</div>
    <div>
      <div style="font-weight:700;font-size:0.95rem;color:#1e40af;margin-bottom:0.4rem;">
        TrustLLM does not independently benchmark model intelligence, speed, or cost.
      </div>
      <p style="color:#1d4ed8;font-size:0.85rem;line-height:1.65;margin:0 0 0.75rem 0;">
        For capability benchmarks we reference
        <a href="https://artificialanalysis.ai" target="_blank"
           style="color:#1d4ed8;font-weight:600;">Artificial Analysis</a>
        — an independent AI benchmarking platform that measures quality, output speed,
        latency, context window, and pricing across dozens of providers.
      </p>
      <div style="display:flex;gap:0.5rem;flex-wrap:wrap;">
        <a href="https://artificialanalysis.ai/models" target="_blank"
           style="display:inline-flex;align-items:center;gap:0.25rem;background:white;
                  border:1px solid #bfdbfe;border-radius:6px;padding:0.3rem 0.75rem;
                  font-size:0.78rem;color:#1d4ed8;text-decoration:none;font-weight:500;">
          🧠 Intelligence benchmarks ↗
        </a>
        <a href="https://artificialanalysis.ai/models" target="_blank"
           style="display:inline-flex;align-items:center;gap:0.25rem;background:white;
                  border:1px solid #bfdbfe;border-radius:6px;padding:0.3rem 0.75rem;
                  font-size:0.78rem;color:#1d4ed8;text-decoration:none;font-weight:500;">
          ⚡ Speed benchmarks ↗
        </a>
        <a href="https://artificialanalysis.ai/models" target="_blank"
           style="display:inline-flex;align-items:center;gap:0.25rem;background:white;
                  border:1px solid #bfdbfe;border-radius:6px;padding:0.3rem 0.75rem;
                  font-size:0.78rem;color:#1d4ed8;text-decoration:none;font-weight:500;">
          💰 Cost &amp; pricing ↗
        </a>
        <a href="https://artificialanalysis.ai/leaderboards/models" target="_blank"
           style="display:inline-flex;align-items:center;gap:0.25rem;background:white;
                  border:1px solid #bfdbfe;border-radius:6px;padding:0.3rem 0.75rem;
                  font-size:0.78rem;color:#1d4ed8;text-decoration:none;font-weight:500;">
          🏆 Full leaderboard ↗
        </a>
      </div>
    </div>
  </div>
</div>
<p style="font-size:0.78rem;color:#9ca3af;margin-top:0.25rem;">
  Capability links on model cards point directly to Artificial Analysis pages for that model.
  TrustLLM displays no capability numbers directly — all capability data lives on Artificial Analysis.
</p>
""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Section 5: Limitations ───────────────────────────────────────────────
    st.subheader("5. Limitations")

    limitations = [
        ("🚫", "Not measured", [
            "GPU / hardware performance",
            "Image, video, audio, or multimodal capabilities",
            "Real-time inference latency (use Artificial Analysis for this)",
            "Fine-tuned or private model variants",
        ]),
        ("📊", "Sampling caveats", [
            "Results are based on sampled evaluations from curated datasets — not exhaustive benchmarks.",
            "Scores may vary based on prompt phrasing, model temperature, and system-prompt configuration.",
            "A higher Trust Score does not guarantee correctness in every production context.",
        ]),
        ("⚙️", "Technical scope", [
            "The LLM-as-Judge scorer currently uses simulated scores in demo mode.",
            "RAG evaluations depend on the quality of uploaded documents and chunking parameters.",
            "Hallucination detection uses heuristic pattern-matching — it is not a ground-truth classifier.",
        ]),
    ]

    for icon, heading, items in limitations:
        bullets = "".join(f"<li>{item}</li>" for item in items)
        st.markdown(f"""
<div style="background:white;border:1px solid #e5e7eb;border-radius:10px;
            padding:1rem 1.25rem;margin-bottom:0.75rem;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
  <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.5rem;">
    <span style="font-size:1.2rem;">{icon}</span>
    <span style="font-weight:700;font-size:0.875rem;color:#111827;">{heading}</span>
  </div>
  <ul style="color:#6b7280;font-size:0.82rem;line-height:1.7;margin:0;padding-left:1.2rem;">
    {bullets}
  </ul>
</div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Section 6: BYOK & Data Privacy ───────────────────────────────────────
    st.subheader("6. BYOK & Data Privacy")

    col1, col2, col3 = st.columns(3)
    privacy_cards = [
        ("🔑", "API Keys", "#f0fdf4", "#bbf7d0", "#15803d",
         "User API keys (BYOK) are <strong>never stored</strong> on TrustLLM servers. "
         "Keys are held only in memory for the duration of a single evaluation request."),
        ("💾", "Eval Results", "#f0f9ff", "#bae6fd", "#0369a1",
         "Evaluation results are stored locally in <code>reports/</code> JSON files. "
         "Cloud persistence (Supabase) is opt-in and only activated with explicit user consent."),
        ("🔒", "Authentication", "#faf5ff", "#ddd6fe", "#6d28d9",
         "Login is handled via session-state in demo mode. "
         "Google OAuth and GitHub sign-in are available in production; "
         "no passwords are transmitted to third parties."),
    ]

    for col, (icon, title, bg, border, color, desc) in zip([col1, col2, col3], privacy_cards):
        with col:
            st.markdown(f"""
<div style="background:{bg};border:1px solid {border};border-radius:10px;
            padding:1.1rem;height:100%;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
  <div style="font-size:1.5rem;margin-bottom:0.4rem;">{icon}</div>
  <div style="font-weight:700;font-size:0.875rem;color:{color};margin-bottom:0.4rem;">{title}</div>
  <p style="font-size:0.8rem;color:#374151;line-height:1.6;margin:0;">{desc}</p>
</div>""", unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("""
<div style="background:#f8fafc;border:1px solid #e5e7eb;border-radius:10px;
            padding:1rem 1.25rem;text-align:center;">
  <p style="color:#6b7280;font-size:0.8rem;margin:0;">
    Questions or feedback?
    <a href="https://github.com/monikakushwaha1411/trustllm/issues" target="_blank"
       style="color:#4f46e5;font-weight:600;text-decoration:none;">Open an issue on GitHub ↗</a>
    &nbsp;·&nbsp;
    Built by
    <a href="https://www.linkedin.com/in/monika-kushwaha-52443735/" target="_blank"
       style="color:#4f46e5;font-weight:600;text-decoration:none;">Monika Kushwaha</a>
  </p>
</div>
""", unsafe_allow_html=True)
