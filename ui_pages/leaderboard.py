import streamlit as st
import json
import pandas as pd
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parents[1]


def _user_report_dir() -> Path:
    """Return (and create) the per-user reports directory."""
    user_id = st.session_state.get("user", {}).get("id", "default")
    safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in user_id)
    d = BASE_DIR / "reports" / safe_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _add_leaderboard_entry(model: str, dataset: str, accuracy: float, total: int, passed: int):
    """Add or update a leaderboard entry."""
    cache_path = _user_report_dir() / "dataset_leaderboard.json"
    try:
        with open(cache_path, "r") as f:
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

    with open(cache_path, "w") as f:
        json.dump(leaderboard_data, f, indent=2)


def render():
    st.title("Model Leaderboard")
    st.caption("Compare models side-by-side ranked by dataset accuracy.")
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    user_dir = _user_report_dir()
    batch_report_path = user_dir / "batch_eval_results.json"
    standard_report_path = user_dir / "results.json"
    cache_path = user_dir / "dataset_leaderboard.json"

    # Load batch evaluation results and update leaderboard
    if batch_report_path.exists():
        with open(batch_report_path, "r") as f:
            batch_data = json.load(f)

        dataset_name = st.session_state.get("current_dataset_name", "rag_eval")
        model_name = st.session_state.get("current_model", "unknown")

        if batch_data and model_name != "unknown":
            total = len(batch_data)
            passed = sum(1 for r in batch_data if r.get("passed", False))
            accuracy = passed / total if total > 0 else 0.0
            _add_leaderboard_entry(model_name, dataset_name, accuracy, total, passed)

    # Load leaderboard entries
    try:
        with open(cache_path, "r") as f:
            leaderboard_data = json.load(f)
        entries = leaderboard_data.get("entries", [])
    except (FileNotFoundError, json.JSONDecodeError):
        entries = []

    # Also include standard eval results
    if standard_report_path.exists() and entries:
        with open(standard_report_path, "r") as f:
            standard_data = json.load(f)
        
        df = pd.DataFrame(standard_data)
        if "model" in df.columns and "trust_score" in df.columns:
            for model in df["model"].unique():
                model_data = df[df["model"] == model]
                avg_trust = model_data["trust_score"].mean()
                # Check if this model already exists with standard dataset
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
        st.info("No leaderboard entries yet. Run a dataset evaluation in **Prompt Dataset** to see results here.")
        return
    
    # Create leaderboard dataframe
    leaderboard_df = pd.DataFrame(entries)
    # Sort by accuracy descending, then by timestamp (most recent first)
    leaderboard_df = leaderboard_df.sort_values(["accuracy", "timestamp"], ascending=[False, False])
    # Remove duplicates (keep the most recent entry for each model/dataset pair)
    leaderboard_df = leaderboard_df.drop_duplicates(subset=["model", "dataset"], keep="first")
    # Format for display with rank medals + color-coded accuracy
    display_df = leaderboard_df[["model", "dataset", "accuracy"]].copy()

    def _rank_label(idx: int) -> str:
        return {0: "🥇 #1", 1: "🥈 #2", 2: "🥉 #3"}.get(idx, f"#{idx + 1}")

    def _accuracy_with_color(acc: float) -> str:
        if acc >= 0.8:
            return f"🟢 {acc:.0%}"
        if acc >= 0.6:
            return f"🟡 {acc:.0%}"
        return f"🔴 {acc:.0%}"

    display_df.insert(0, "Rank", [_rank_label(i) for i in range(len(display_df))])
    display_df["accuracy"] = display_df["accuracy"].apply(_accuracy_with_color)
    display_df.columns = ["Rank", "Model", "Dataset", "Accuracy"]

    st.subheader("Dataset Accuracy Rankings")
    st.caption("🟢 ≥ 80% (production-ready) · 🟡 60–80% (acceptable) · 🔴 < 60% (failing)")
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # Clear leaderboard button
    if st.button("🗑 Clear Leaderboard"):
        cache_path = _user_report_dir() / "dataset_leaderboard.json"
        if cache_path.exists():
            cache_path.unlink()
        st.rerun()
