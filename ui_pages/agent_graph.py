"""
ui_pages/agent_graph.py — LangGraph Agent (Trajectory Eval)
============================================================
Runs the real LangGraph agent (agents/langgraph_agent.py) over a task and
scores the resulting trajectory (evaluators/trajectory_eval.py). Every heavy
import is deferred into render() so a missing langgraph never breaks the app.
"""

import streamlit as st


_EXAMPLES = [
    "What is 128 * 47, and how many words are in this question?",
    "Who wrote the play 'Hamlet'? Verify against the reference corpus.",
    "What is the capital of Australia and how many characters are in this task?",
]


def render():
    st.title("LangGraph Agent")
    st.caption("A real multi-step LangGraph agent — plan → route → tool → "
               "synthesize — with its trajectory scored for trust.")
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    # -- langgraph availability check (graceful) --------------------------
    try:
        import langgraph  # noqa: F401
        _lg_ok = True
    except Exception:  # noqa: BLE001
        _lg_ok = False

    if not _lg_ok:
        st.warning(
            "**LangGraph isn't installed in this environment.** The agent "
            "page needs the `langgraph` package.\n\n"
            "```bash\npip install langgraph\n```\n\n"
            "It's in `requirements.txt`, so the deployed app has it — this "
            "message only appears in trimmed local installs."
        )
        return

    # -- key status note --------------------------------------------------
    try:
        from rag.rag_pipeline import _get_groq_client
        _get_groq_client()
        st.caption("✓ Groq key detected — the agent reasons with "
                   "`llama-3.3-70b-versatile`.")
    except Exception:  # noqa: BLE001
        st.info("ℹ️ No `GROQ_API_KEY` set — the agent still runs using its "
                "deterministic planner/router fallbacks so you can see the "
                "graph and trajectory. Add a key for LLM-driven reasoning.")

    with st.form("agent_graph_form"):
        task = st.text_area(
            "Task for the agent",
            value=_EXAMPLES[0],
            height=80,
            help="The agent will plan, call tools, and synthesize an answer.")
        c1, c2 = st.columns([3, 1])
        with c1:
            model = st.selectbox(
                "Reasoning model (Groq)",
                ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"])
        with c2:
            st.write("")
            st.write("")
            run = st.form_submit_button("Run agent", type="primary",
                                        use_container_width=True)

    st.caption("Tools available to the agent: **calculator**, **text_stats**, "
               "**knowledge** (looks up the bundled reference corpus).")

    if not run:
        return
    if not task.strip():
        st.error("Enter a task for the agent.")
        return

    from agents.langgraph_agent import run_agent
    from evaluators.trajectory_eval import evaluate_trajectory

    with st.spinner("Agent is planning, calling tools, and synthesizing…"):
        run_result = run_agent(task.strip(), model=model)

    if run_result.get("error"):
        st.error(f"Agent run failed: {run_result['error']}")
        return

    scores = evaluate_trajectory(run_result)

    # -- Final answer -----------------------------------------------------
    st.subheader("Final answer")
    st.markdown(
        f'<div style="background:white;border:1px solid #e5e7eb;border-radius:12px;'
        f'padding:1.1rem 1.25rem;font-size:0.95rem;line-height:1.6;color:#111827;">'
        f'{run_result.get("answer","(no answer)")}</div>',
        unsafe_allow_html=True)

    # -- Trajectory scores ------------------------------------------------
    st.subheader("Trajectory scores")
    ts = scores.get("trajectory_score")
    m = st.columns(5)
    m[0].metric("Trajectory Score", f"{ts:.0%}" if ts is not None else "—")
    g = scores.get("groundedness")
    m[1].metric("Groundedness", f"{g:.0%}" if g is not None else "—")
    m[2].metric("Tool Efficiency", f"{scores.get('tool_efficiency', 0):.0%}")
    m[3].metric("Step Coherence", f"{scores.get('step_coherence', 0):.0%}")
    ft = scores.get("final_trust")
    m[4].metric("Final Trust", f"{ft:.0%}" if ft is not None else "—")
    st.caption(f"Groundedness source: {scores.get('groundedness_source','—')} · "
               f"{scores.get('num_tool_calls',0)} tool calls · "
               f"{scores.get('num_steps',0)} trajectory steps")

    if scores.get("trust_dimensions"):
        with st.expander("Six-dimension trust breakdown of the final answer"):
            dims = scores["trust_dimensions"]
            dcols = st.columns(len(dims))
            for col, (dim, val) in zip(dcols, dims.items()):
                col.metric(dim.title(), f"{val:.0%}")

    # -- Plan -------------------------------------------------------------
    st.subheader("Plan")
    st.info(run_result.get("plan", "(no plan)"))

    # -- Trajectory (step-by-step) ---------------------------------------
    st.subheader("Trajectory")
    _icons = {"plan": "🧭", "route": "🔀", "tool": "🛠️", "synthesize": "✍️"}
    for i, step in enumerate(run_result.get("trajectory", []), 1):
        node = step.get("node", "?")
        icon = _icons.get(node, "•")
        detail = str(step.get("detail", ""))
        if len(detail) > 400:
            detail = detail[:400] + "…"
        st.markdown(
            f'<div style="display:flex;gap:0.75rem;padding:0.6rem 0.9rem;'
            f'border-left:3px solid #E8290B;background:#FEF2F0;border-radius:6px;'
            f'margin-bottom:0.4rem;">'
            f'<div style="font-weight:700;color:#E8290B;min-width:26px;">{i:02d}</div>'
            f'<div><span style="font-weight:600;color:#0A0A0A;">{icon} {node}</span>'
            f'<div style="font-size:0.83rem;color:#374151;margin-top:2px;">{detail}</div>'
            f'</div></div>',
            unsafe_allow_html=True)

    # -- Tool calls table -------------------------------------------------
    tool_calls = run_result.get("tool_calls", [])
    if tool_calls:
        st.subheader("Tool calls")
        import pandas as pd
        df = pd.DataFrame([{"Tool": c["tool"], "Observation": c["observation"]}
                           for c in tool_calls])
        st.dataframe(df, use_container_width=True, hide_index=True)
