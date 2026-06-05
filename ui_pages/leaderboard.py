import streamlit as st
import json
import pandas as pd
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parents[1]
BATCH_REPORT_PATH = BASE_DIR / "reports" / "batch_eval_results.json"
STANDARD_REPORT_PATH = BASE_DIR / "reports" / "results.json"
LEADERBOARD_CACHE_PATH = BASE_DIR / "reports" / "dataset_leaderboard.json"


def _add_leaderboard_entry(model: str, dataset: str, accuracy: float, total: int, passed: int):
    try:
        with open(LEADERBOARD_CACHE_PATH, "r") as f:
            leaderboard_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        leaderboard_data = {"entries": []}

    for entry in leaderboard_data["entries"]:
        if entry["model"] == model and entry["dataset"] == dataset:
            entry["accuracy"] = accuracy
            entry["total"] = total
            entry["passed"] = passed
            entry["timestamp"] = datetime.now().isoformat()
            break
    else:
        leaderboard_data["entries"].append({
            "model": model,
            "dataset": dataset,
            "accuracy": accuracy,
            "total": total,
            "passed": passed,
            "timestamp": datetime.now().isoformat()
        })

    with open(LEADERBOARD_CACHE_PATH, "w") as f:
        json.dump(leaderboard_data, f, indent=2)


def _status_chip(accuracy: float) -> str:
    if accuracy >= 0.8:
        return '<span class="status-chip chip-pass">Passing</span>'
    elif accuracy >= 0.6:
        return '<span class="status-chip chip-warn">Review</span>'
    else:
        return '<span class="status-chip chip-fail">Failing</span>'


def _score_color(accuracy: float) -> str:
    if accuracy >= 0.8:
        return "#16A34A"
    elif accuracy >= 0.6:
        return "#D97706"
    return "#E8290B"


def render():
    st.markdown(
        '<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800'
        '&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="verdict-section-label">— EVALUATE · LEADERBOARD</div>'
        '<h1 style="font-family:\'Syne\',sans-serif;font-size:2rem;font-weight:800;'
        'letter-spacing:-0.02em;color:#0E0E0E;margin:0 0 4px 0;">Model Rankings.</h1>',
        unsafe_allow_html=True,
    )
    st.caption("Compare models side-by-side ranked by dataset accuracy.")
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    # ── Load and merge leaderboard data ────────────────────────────────
    if BATCH_REPORT_PATH.exists():
        with open(BATCH_REPORT_PATH, "r") as f:
            batch_data = json.load(f)

        dataset_name = st.session_state.get("current_dataset_name", "rag_eval")
        model_name = st.session_state.get("current_model", "unknown")

        if batch_data and model_name != "unknown":
            total = len(batch_data)
            passed = sum(1 for r in batch_data if r.get("passed", False))
            accuracy = passed / total if total > 0 else 0.0
            _add_leaderboard_entry(model_name, dataset_name, accuracy, total, passed)

    try:
        with open(LEADERBOARD_CACHE_PATH, "r") as f:
            leaderboard_data = json.load(f)
        entries = leaderboard_data.get("entries", [])
    except (FileNotFoundError, json.JSONDecodeError):
        entries = []

    if STANDARD_REPORT_PATH.exists() and entries:
        with open(STANDARD_REPORT_PATH, "r") as f:
            standard_data = json.load(f)

        df_std = pd.DataFrame(standard_data)
        if "model" in df_std.columns and "trust_score" in df_std.columns:
            for model in df_std["model"].unique():
                model_data = df_std[df_std["model"] == model]
                avg_trust = model_data["trust_score"].mean()
                existing = any(e["model"] == model and e["dataset"] == "standard" for e in entries)
                if not existing:
                    entries.append({
                        "model": model,
                        "dataset": "standard",
                        "accuracy": avg_trust,
                        "total": len(model_data),
                        "passed": 0,
                        "timestamp": datetime.now().isoformat()
                    })

    if not entries:
        st.markdown(
            '<div class="panel"><div class="panel-body" style="padding:2rem;text-align:center;">'
            '<div style="color:#888888;font-size:0.875rem;font-family:Inter,sans-serif;">'
            'No leaderboard entries yet. Run a dataset evaluation in <strong>Prompt Dataset</strong> '
            'to see results here.</div></div></div>',
            unsafe_allow_html=True,
        )
        return

    # ── Build sorted table ─────────────────────────────────────────────
    leaderboard_df = pd.DataFrame(entries)
    leaderboard_df = leaderboard_df.sort_values(
        ["accuracy", "timestamp"], ascending=[False, False]
    ).drop_duplicates(subset=["model", "dataset"], keep="first").reset_index(drop=True)

    # ── Render VERDICT-style HTML table ───────────────────────────────
    rows_html = ""
    for i, row in leaderboard_df.iterrows():
        rank = i + 1
        badge_cls = "red" if rank == 1 else ""
        acc = row["accuracy"]
        color = _score_color(acc)
        chip = _status_chip(acc)
        rows_html += f"""
<tr>
  <td><span class="rank-badge {badge_cls}">{rank}</span></td>
  <td class="model-nm">{row['model']}</td>
  <td style="font-size:11px;color:#888888;font-family:Inter,sans-serif;">{row['dataset']}</td>
  <td><span class="score-val" style="color:{color}">{acc:.0%}</span></td>
  <td>{chip}</td>
</tr>
"""

    table_html = f"""
<div class="panel">
  <div class="panel-head">
    <div class="panel-title">Dataset Accuracy Rankings</div>
    <div class="panel-tag">{len(leaderboard_df)} ENTRIES</div>
  </div>
  <table class="verdict-table">
    <thead>
      <tr>
        <th>#</th>
        <th>Model</th>
        <th>Dataset</th>
        <th>Accuracy</th>
        <th>Status</th>
      </tr>
    </thead>
    <tbody>
      {rows_html}
    </tbody>
  </table>
</div>
"""
    st.markdown(table_html, unsafe_allow_html=True)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    if st.button("Clear Leaderboard"):
        if LEADERBOARD_CACHE_PATH.exists():
            LEADERBOARD_CACHE_PATH.unlink()
        st.rerun()
