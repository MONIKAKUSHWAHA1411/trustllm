import json
import random
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluation_engine.hallucination_detector import detect_hallucination
from evaluation_engine.prompt_injection_test import detect_injection
from evaluation_engine.merge_results import compute_trust_score

BASE_DIR = Path(__file__).resolve().parents[1]
REPORTS_DIR = BASE_DIR / "reports"

app = FastAPI(title="TrustLLM API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_feedback_lock = threading.Lock()


# ── Request / Response models ──────────────────────────────────────────────

class EvaluateRequest(BaseModel):
    prompt: str
    model: str
    category: str


class FeedbackRequest(BaseModel):
    result_id: str
    rating: int
    comment: Optional[str] = None


# ── Helpers ────────────────────────────────────────────────────────────────

def _load_results():
    with open(REPORTS_DIR / "results.json") as f:
        return json.load(f)


# ── Endpoints ──────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok", "version": "1.0.0", "service": "TrustLLM API"}


@app.get("/api/models")
def get_models():
    results = _load_results()
    models = sorted({r["model"] for r in results if r.get("model")})
    return {"models": models, "count": len(models)}


@app.post("/api/evaluate")
def evaluate(req: EvaluateRequest):
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="prompt must not be empty")
    if len(req.prompt) > 2000:
        raise HTTPException(status_code=400, detail="prompt exceeds 2000 character limit")

    prompt_type = detect_injection(req.prompt)
    hallucination = detect_hallucination(req.prompt)

    correctness = round(random.uniform(0.6, 1.0), 4)
    relevance   = round(random.uniform(0.6, 1.0), 4)
    clarity     = round(random.uniform(0.6, 1.0), 4)
    safety      = round(random.uniform(0.6, 1.0), 4)

    item = {
        "hallucination": hallucination,
        "correctness":   correctness,
        "relevance":     relevance,
        "clarity":       clarity,
        "safety":        safety,
    }
    trust_score = compute_trust_score(item)

    return {
        "prompt":       req.prompt,
        "model":        req.model,
        "category":     req.category,
        "prompt_type":  prompt_type,
        "hallucination": hallucination,
        "correctness":  correctness,
        "relevance":    relevance,
        "clarity":      clarity,
        "safety":       safety,
        "trust_score":  trust_score,
    }


@app.get("/api/results")
def get_results(
    page:     int = Query(default=1, ge=1),
    limit:    int = Query(default=20, ge=1, le=100),
    model:    Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
):
    results = _load_results()

    if model:
        results = [r for r in results if r.get("model") == model]
    if category:
        results = [r for r in results if r.get("category") == category]

    total = len(results)
    pages = max(1, (total + limit - 1) // limit)
    start = (page - 1) * limit
    end   = start + limit

    return {
        "total":   total,
        "page":    page,
        "limit":   limit,
        "pages":   pages,
        "results": results[start:end],
    }


@app.get("/api/leaderboard")
def get_leaderboard():
    results = _load_results()

    model_data: dict = {}
    for r in results:
        m = r.get("model")
        if not m:
            continue
        if m not in model_data:
            model_data[m] = {"scores": [], "count": 0}
        model_data[m]["scores"].append(r.get("trust_score", 0))
        model_data[m]["count"] += 1

    ranked = sorted(
        [
            {
                "model":           m,
                "avg_trust_score": round(sum(d["scores"]) / len(d["scores"]), 3),
                "prompt_count":    d["count"],
            }
            for m, d in model_data.items()
        ],
        key=lambda x: x["avg_trust_score"],
        reverse=True,
    )

    for i, entry in enumerate(ranked, start=1):
        entry["rank"] = i

    return {"leaderboard": ranked}


@app.post("/api/feedback")
def submit_feedback(req: FeedbackRequest):
    if req.rating < 1 or req.rating > 5:
        raise HTTPException(status_code=400, detail="rating must be between 1 and 5")

    entry = {
        "feedback_id": str(uuid.uuid4()),
        "result_id":   req.result_id,
        "rating":      req.rating,
        "comment":     req.comment,
        "timestamp":   datetime.now(timezone.utc).isoformat(),
    }

    feedback_path = REPORTS_DIR / "feedback.json"

    with _feedback_lock:
        existing = []
        if feedback_path.exists():
            with open(feedback_path) as f:
                try:
                    existing = json.load(f)
                except json.JSONDecodeError:
                    existing = []
        existing.append(entry)
        with open(feedback_path, "w") as f:
            json.dump(existing, f, indent=2)

    return {"status": "saved", "feedback_id": entry["feedback_id"]}
