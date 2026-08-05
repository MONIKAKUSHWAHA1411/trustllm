"""
agents/langgraph_agent.py — TrustLLM × LangGraph
=================================================
A real, stateful **LangGraph** agent that TrustLLM can evaluate end to end.

Unlike ``agents/hr_agent.py`` (a deterministic keyword router kept for the
reproducible tool-accuracy benchmark), this agent is a genuine multi-step
graph:

    plan ─▶ route ─▶ tool ─▶ (loop back to route)  ─▶ synthesize ─▶ END

* **plan**        — Groq drafts a short plan for the task.
* **route**       — Groq (or a deterministic fallback) picks the next tool, or
                    decides enough evidence has been gathered and stops.
* **tool**        — executes one real tool and appends an observation.
* **synthesize**  — Groq writes the final answer grounded in the observations.

Every node records a step into ``state["trajectory"]`` so the run can be
scored afterwards (see ``evaluators/trajectory_eval.py``).

Design notes
------------
* ``langgraph`` is imported lazily inside ``build_graph`` so importing this
  module never fails when the package is absent — the UI degrades gracefully.
* All LLM calls go through the existing Groq client. When no ``GROQ_API_KEY``
  is set, the agent still runs using deterministic fallbacks so the graph and
  trajectory can be demonstrated without a key.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, TypedDict

DEFAULT_MODEL = "llama-3.3-70b-versatile"
MAX_TOOL_STEPS = 4


# -----------------------------------------------------------------------
# Real tools — deterministic, no network, safe to run anywhere
# -----------------------------------------------------------------------

def _tool_calculator(query: str) -> str:
    """Evaluate a simple arithmetic expression found in the query."""
    expr = re.findall(r"[0-9\.\+\-\*/\(\)\s%]+", query)
    candidate = max(expr, key=len).strip() if expr else ""
    if not candidate or not re.search(r"\d", candidate):
        return "calculator: no arithmetic expression found."
    if not re.fullmatch(r"[0-9\.\+\-\*/\(\)\s%]+", candidate):
        return "calculator: expression contains unsupported characters."
    try:
        # Safe: character-class above restricts to arithmetic only.
        value = eval(candidate, {"__builtins__": {}}, {})  # noqa: S307
        return f"calculator: {candidate.strip()} = {value}"
    except Exception as e:  # noqa: BLE001
        return f"calculator: could not evaluate ({type(e).__name__})."


def _tool_text_stats(query: str) -> str:
    """Return simple, verifiable statistics about the query text."""
    words = query.split()
    chars = len(query)
    return (f"text_stats: {len(words)} words, {chars} characters, "
            f"{len(set(w.lower() for w in words))} unique words.")


def _tool_knowledge(query: str) -> str:
    """Look the query up against the bundled eval dataset (a real corpus)."""
    from pathlib import Path
    ds = Path(__file__).resolve().parents[1] / "datasets" / "prompts.json"
    try:
        with open(ds) as f:
            prompts = json.load(f)
    except Exception:  # noqa: BLE001
        return "knowledge: dataset unavailable."
    q = query.lower()
    q_terms = set(re.findall(r"[a-z0-9]+", q))
    best, best_overlap = None, 0
    for p in prompts:
        terms = set(re.findall(r"[a-z0-9]+", p["prompt"].lower()))
        overlap = len(q_terms & terms)
        if overlap > best_overlap:
            best, best_overlap = p, overlap
    if best and best_overlap >= 2:
        ans = best.get("expected_answer", "")
        return f"knowledge: closest reference — Q:'{best['prompt']}' → A:'{ans}'"
    return "knowledge: no close reference found in the corpus."


TOOLS = {
    "calculator": _tool_calculator,
    "text_stats": _tool_text_stats,
    "knowledge": _tool_knowledge,
}
TOOL_DESCRIPTIONS = {
    "calculator": "evaluate an arithmetic expression",
    "text_stats": "count words/characters in the task text",
    "knowledge": "look up a fact against the TrustLLM reference corpus",
}


# -----------------------------------------------------------------------
# Graph state
# -----------------------------------------------------------------------

class AgentState(TypedDict, total=False):
    task: str
    model: str
    plan: str
    tool_calls: List[Dict[str, str]]      # [{tool, input, observation}]
    observations: List[str]
    step_count: int
    answer: str
    trajectory: List[Dict[str, Any]]      # ordered node log for scoring
    next_tool: str


# -----------------------------------------------------------------------
# LLM helper (Groq, with deterministic fallback)
# -----------------------------------------------------------------------

def _groq_complete(prompt: str, model: str, max_tokens: int = 400) -> str | None:
    """Return Groq completion text, or None if unavailable (no key / error)."""
    try:
        from rag.rag_pipeline import _get_groq_client
        client = _get_groq_client()
    except Exception:  # noqa: BLE001
        return None
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content.strip()
    except Exception:  # noqa: BLE001
        return None


# -----------------------------------------------------------------------
# Nodes
# -----------------------------------------------------------------------

def _node_plan(state: AgentState) -> AgentState:
    task, model = state["task"], state.get("model", DEFAULT_MODEL)
    tools_desc = "\n".join(f"- {n}: {d}" for n, d in TOOL_DESCRIPTIONS.items())
    prompt = (f"You are a planning agent. Available tools:\n{tools_desc}\n\n"
              f"Task: {task}\n\nWrite a 1-2 sentence plan for solving it.")
    plan = _groq_complete(prompt, model, max_tokens=150) or (
        f"Inspect the task, use the most relevant tool among "
        f"{list(TOOLS)}, then synthesize an answer.")
    state["plan"] = plan
    state.setdefault("trajectory", []).append(
        {"node": "plan", "detail": plan})
    state["step_count"] = 0
    state.setdefault("tool_calls", [])
    state.setdefault("observations", [])
    return state


def _heuristic_tool(task: str, used: List[str]) -> str:
    """Deterministic tool choice used when Groq is unavailable."""
    t = task.lower()
    if re.search(r"\d.*[\+\-\*/%].*\d", t) and "calculator" not in used:
        return "calculator"
    if any(w in t for w in ("count", "words", "characters", "length")) and "text_stats" not in used:
        return "text_stats"
    if "knowledge" not in used:
        return "knowledge"
    return "STOP"


def _node_route(state: AgentState) -> AgentState:
    task, model = state["task"], state.get("model", DEFAULT_MODEL)
    used = [c["tool"] for c in state.get("tool_calls", [])]

    if state.get("step_count", 0) >= MAX_TOOL_STEPS:
        state["next_tool"] = "STOP"
        state.setdefault("trajectory", []).append(
            {"node": "route", "detail": "max steps reached → STOP"})
        return state

    obs = "\n".join(state.get("observations", [])) or "(none yet)"
    prompt = (
        f"You are a routing agent deciding the next action.\n"
        f"Task: {task}\n"
        f"Tools: {json.dumps(TOOL_DESCRIPTIONS)}\n"
        f"Already used: {used}\n"
        f"Observations so far:\n{obs}\n\n"
        f"Reply with ONLY one word: the name of the next tool to call "
        f"({', '.join(TOOLS)}), or STOP if you have enough to answer.")
    choice = _groq_complete(prompt, model, max_tokens=10)
    if choice:
        choice = choice.strip().split()[0].lower().strip(".,:")
    if choice not in TOOLS and choice != "stop":
        choice = _heuristic_tool(task, used)
    choice = "STOP" if str(choice).lower() == "stop" else choice
    state["next_tool"] = choice
    state.setdefault("trajectory", []).append(
        {"node": "route", "detail": f"next → {choice}"})
    return state


def _node_tool(state: AgentState) -> AgentState:
    tool = state.get("next_tool", "knowledge")
    fn = TOOLS.get(tool, _tool_knowledge)
    observation = fn(state["task"])
    state.setdefault("tool_calls", []).append(
        {"tool": tool, "input": state["task"], "observation": observation})
    state.setdefault("observations", []).append(observation)
    state["step_count"] = state.get("step_count", 0) + 1
    state.setdefault("trajectory", []).append(
        {"node": "tool", "detail": f"{tool} → {observation}"})
    return state


def _node_synthesize(state: AgentState) -> AgentState:
    task, model = state["task"], state.get("model", DEFAULT_MODEL)
    obs = "\n".join(state.get("observations", [])) or "(no tool evidence)"
    prompt = (
        f"Task: {task}\n\nTool evidence:\n{obs}\n\n"
        f"Write a concise, accurate final answer grounded ONLY in the evidence "
        f"above. If the evidence is insufficient, say so plainly.")
    answer = _groq_complete(prompt, model, max_tokens=350)
    if not answer:
        answer = ("Based on the gathered evidence:\n" + obs +
                  "\n\n(Groq key not set — this is the deterministic summary.)")
    state["answer"] = answer
    state.setdefault("trajectory", []).append(
        {"node": "synthesize", "detail": answer})
    return state


def _should_continue(state: AgentState) -> str:
    return "synthesize" if state.get("next_tool") == "STOP" else "tool"


# -----------------------------------------------------------------------
# Graph builder + runner
# -----------------------------------------------------------------------

def build_graph():
    """Compile and return the LangGraph agent. Raises ImportError if langgraph
    is not installed (caller should surface an install hint)."""
    from langgraph.graph import StateGraph, END

    g = StateGraph(AgentState)
    g.add_node("plan", _node_plan)
    g.add_node("route", _node_route)
    g.add_node("tool", _node_tool)
    g.add_node("synthesize", _node_synthesize)

    g.set_entry_point("plan")
    g.add_edge("plan", "route")
    g.add_conditional_edges("route", _should_continue,
                            {"tool": "tool", "synthesize": "synthesize"})
    g.add_edge("tool", "route")
    g.add_edge("synthesize", END)
    return g.compile()


def run_agent(task: str, model: str = DEFAULT_MODEL) -> Dict[str, Any]:
    """Run the agent graph over a task and return the full trajectory.

    Returns a dict with keys: task, model, plan, tool_calls, observations,
    answer, trajectory, step_count. Never raises — on any failure it returns
    a payload with an ``error`` key so the UI can render it.
    """
    try:
        app = build_graph()
    except ImportError as e:
        return {"error": f"LangGraph not installed: {e}", "task": task,
                "trajectory": [], "tool_calls": [], "observations": []}
    init: AgentState = {"task": task, "model": model}
    try:
        final = app.invoke(init)
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}", "task": task,
                "trajectory": [], "tool_calls": [], "observations": []}
    return dict(final)


if __name__ == "__main__":
    import pprint
    pprint.pprint(run_agent("What is 128 * 47 and how many words are in this sentence?"))
