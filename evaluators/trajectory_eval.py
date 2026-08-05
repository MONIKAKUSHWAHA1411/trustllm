"""
evaluators/trajectory_eval.py — score a LangGraph agent trajectory
===================================================================
Turns a raw agent run (from ``agents/langgraph_agent.run_agent``) into
trust metrics, in the spirit of LangGraph/AI-eval trajectory evaluation:

    * tool_efficiency  — did the agent avoid redundant / wasted tool calls?
    * groundedness     — is the final answer supported by the observations?
                         (LLM-judged, falls back to lexical overlap)
    * step_coherence   — did each routing decision lead to a useful step?
    * final_trust      — the six-dimension trust score of the final answer
                         (reuses evaluation_engine.judge)

Every metric is in [0, 1]; ``trajectory_score`` is their mean. All LLM calls
degrade gracefully to deterministic proxies when no GROQ_API_KEY is set.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List


def _lexical_overlap(answer: str, observations: List[str]) -> float:
    """Fraction of answer content-words that appear in the observations."""
    a = set(re.findall(r"[a-z0-9]+", answer.lower()))
    a = {w for w in a if len(w) > 3}
    if not a:
        return 0.0
    obs = set(re.findall(r"[a-z0-9]+", " ".join(observations).lower()))
    return round(len(a & obs) / len(a), 3)


def _judge_groundedness(answer: str, observations: List[str]) -> float | None:
    """LLM-judge whether the answer is grounded in the observations."""
    try:
        from rag.rag_pipeline import _get_groq_client
        client = _get_groq_client()
    except Exception:  # noqa: BLE001
        return None
    obs = "\n".join(observations) or "(none)"
    prompt = (
        "Score from 0.0 to 1.0 how well the ANSWER is supported by the "
        "EVIDENCE (1.0 = fully grounded, 0.0 = fabricated). Reply with ONLY "
        f"a number.\n\nEVIDENCE:\n{obs}\n\nANSWER:\n{answer}\n\nScore:")
    try:
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0, max_tokens=8,
        )
        m = re.search(r"[01](?:\.\d+)?", resp.choices[0].message.content)
        return round(min(1.0, max(0.0, float(m.group()))), 3) if m else None
    except Exception:  # noqa: BLE001
        return None


def _tool_efficiency(tool_calls: List[Dict[str, str]]) -> float:
    """1.0 when every tool call is unique and productive; penalise repeats and
    observations that reported 'no ...found'."""
    if not tool_calls:
        return 0.0
    tools = [c["tool"] for c in tool_calls]
    uniq_ratio = len(set(tools)) / len(tools)
    productive = sum(
        1 for c in tool_calls
        if "no " not in c["observation"].lower()
        and "could not" not in c["observation"].lower())
    prod_ratio = productive / len(tool_calls)
    return round(0.5 * uniq_ratio + 0.5 * prod_ratio, 3)


def _step_coherence(trajectory: List[Dict[str, Any]]) -> float:
    """Reward runs that plan, route, use ≥1 tool, and synthesize."""
    nodes = [t.get("node") for t in trajectory]
    have = {n for n in nodes}
    expected = {"plan", "route", "tool", "synthesize"}
    return round(len(have & expected) / len(expected), 3)


def evaluate_trajectory(run: Dict[str, Any]) -> Dict[str, Any]:
    """Score an agent run. Returns metrics + an overall trajectory_score."""
    if run.get("error"):
        return {"error": run["error"], "trajectory_score": None}

    answer = run.get("answer", "")
    observations = run.get("observations", [])
    tool_calls = run.get("tool_calls", [])
    trajectory = run.get("trajectory", [])

    grounded = _judge_groundedness(answer, observations)
    grounded_source = "llm-judge"
    if grounded is None:
        grounded = _lexical_overlap(answer, observations)
        grounded_source = "lexical-overlap (no GROQ_API_KEY)"

    tool_eff = _tool_efficiency(tool_calls)
    coherence = _step_coherence(trajectory)

    # Final-answer trust via the shared six-dimension judge (graceful).
    final_trust, trust_dims = None, None
    try:
        from evaluation_engine.judge import judge_response
        trust_dims = judge_response(run.get("task", ""), answer)
        final_trust = round(sum(trust_dims.values()) / len(trust_dims), 3)
    except Exception:  # noqa: BLE001
        pass

    parts = [grounded, tool_eff, coherence]
    if final_trust is not None:
        parts.append(final_trust)
    trajectory_score = round(sum(parts) / len(parts), 3)

    return {
        "groundedness": grounded,
        "groundedness_source": grounded_source,
        "tool_efficiency": tool_eff,
        "step_coherence": coherence,
        "final_trust": final_trust,
        "trust_dimensions": trust_dims,
        "trajectory_score": trajectory_score,
        "num_tool_calls": len(tool_calls),
        "num_steps": len(trajectory),
    }
