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
    """Add or update a leaderboard entry."""
    try:
        with open(LEADERBOARD_CACHE_PATH, "r") as f:
            leaderboard_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        leaderboard_data = {"entries": []}
    
    # Check if this model+dataset combination already exists
    for entry in leaderboard_data["entries"]:
        if entry["model"] == model and entry["dataset"] == dataset:
            # Update existing entry with the new accuracy
            entry["accuracy"] = accuracy
            entry["total"] = total
            entry["passed"] = passed
            entry["timestamp"] = datetime.now().isoformat()
            break
    else:
        # Add new entry
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


def render():
    st.title("Model Leaderboard")
    st.caption("Compare models side-by-side ranked by dataset accuracy.")
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    # Load batch evaluation results and update leaderboard
    if BATCH_REPORT_PATH.exists():
        with open(BATCH_REPORT_PATH, "r") as f:
            batch_data = json.load(f)
        
        # Use dataset name from session state or default
        dataset_name = st.session_state.get("current_dataset_name", "rag_eval")
        model_name = st.session_state.get("current_model", "unknown")
        
        if batch_data and model_name != "unknown":
            total = len(batch_data)
            passed = sum(1 for r in batch_data if r.get("passed", False))
            accuracy = passed / total if total > 0 else 0.0
            
            _add_leaderboard_entry(model_name, dataset_name, accuracy, total, passed)
    
    # Load leaderboard entries
    try:
        with open(LEADERBOARD_CACHE_PATH, "r") as f:
            leaderboard_data = json.load(f)
        entries = leaderboard_data.get("entries", [])
    except (FileNotFoundError, json.JSONDecodeError):
        entries = []
    
    # Also include standard eval results
    if STANDARD_REPORT_PATH.exists() and entries:
        with open(STANDARD_REPORT_PATH, "r") as f:
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
    # Format for display
    display_df = leaderboard_df[["model", "dataset", "accuracy"]].copy()
    display_df["accuracy"] = display_df["accuracy"].apply(lambda x: f"{x:.0%}")
    display_df.columns = ["Model", "Dataset", "Accuracy"]
    
    st.subheader("Dataset Accuracy Rankings")
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # Clear leaderboard button
    if st.button("🗑 Clear Leaderboard"):
        if LEADERBOARD_CACHE_PATH.exists():
            LEADERBOARD_CACHE_PATH.unlink()
        st.rerun()
