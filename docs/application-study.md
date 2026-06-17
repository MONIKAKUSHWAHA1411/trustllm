# TrustLLM — Application Study (Pre-Automation)

> **Purpose:** Understand the application *before* writing a single test.
> This is the reconnaissance a QA does first: map every page, every control,
> every input, and the expected behavior. Automation comes *after* this.

---

## How this study was produced

The live site **https://trustllm.site** is a Streamlit app. It returns **HTTP 403**
to non-browser requests and renders its UI over a WebSocket inside a real browser,
so it cannot be scraped with a simple GET. This study is therefore derived from the
**deployed application source** (the same code that runs the site) — the authoritative
record of what each page shows and does.

## Two testable surfaces

TrustLLM exposes **two** surfaces a tester must cover:

| Surface | Tech | Local URL | How to test |
|---------|------|-----------|-------------|
| **UI** (web pages) | Streamlit | `http://localhost:8501` | Selenium |
| **API** (REST) | FastAPI | `http://localhost:8000` | Postman / pytest+requests |

**Access / credentials**
- UI login → Username: `TestUser` · Password: `User123`
- API base → `http://localhost:8000` · Interactive docs at `/docs` (Swagger)
- Start UI: `streamlit run app.py --server.port 8501`
- Start API: `uvicorn api.main:app --port 8000`

---

## Pages Found

1. Login
2. Leaderboard
3. Models
4. Evaluation
5. Results
6. Feedback

> ⚠️ **QA observation:** Of these six, only **Login, Leaderboard, Evaluation,**
> and **Results** are real Streamlit *pages*. **Models** and **Feedback** have
> **no dedicated UI page** — they are API-only surfaces (model selection merely
> *appears* inside other pages). This gap is itself a finding worth recording.
> A hidden gate also exists: a **3-step Onboarding wizard** sits between Login and
> the dashboard and must be passed (or skipped) before any nav page is reachable.

---

## 1. Login

**Surface:** UI — `app.py` → `_show_login()` · **Route:** `/` (shown when not authenticated)

**What is displayed?**
- Left panel: TrustLLM branding, headline "Evaluate LLMs you can actually trust",
  feature bullets, and a stats showcase (161 prompts evaluated, 6 models tested,
  0.76 avg trust score, per-model trust bars for phi3/gpt/gemini-pro/claude).
- Right panel: "Welcome back / Sign in to your account", two social-login buttons,
  a credentials form, and a demo-credentials hint.

**What can the user click?**
- **Continue with Google** button → demo only; text flips to "Not available in demo mode" for ~2.5s.
- **Continue with GitHub** button → demo only; same behavior.
- **Sign in →** form submit button.

**What input fields exist?**
- **Username** — text input (placeholder "Enter your username").
- **Password** — password input (masked, placeholder "Enter your password").

**Expected behavior?**
- Valid `TestUser` / `User123` → sets `logged_in = True`, reruns → **Onboarding** wizard.
- Invalid credentials → red error: **"Invalid username or password."**
- Empty username or password → treated as invalid → same error (no field-level validation).
- Social buttons never authenticate (demo stubs).

**Test hooks (for Selenium)**
- Username input: `[data-testid="stTextInput"]:nth-of-type(1) input`
- Password input: `[data-testid="stTextInput"]:nth-of-type(2) input`
- Submit: `[data-testid="stFormSubmitButton"] button`
- Error banner: `[data-testid="stAlert"]`

---

## 1a. Onboarding (gate between Login and Dashboard)

**Surface:** UI — `app.py` → `_show_onboarding()` · Not in the page list but **blocks** everything.

**What is displayed?** A 3-step wizard: Step 1 welcome (3 feature cards),
Step 2 "What will you evaluate?" (5 category cards w/ checkboxes),
Step 3 "Which models will you evaluate?" (6 model cards w/ checkboxes) + readiness summary.

**What can the user click?** "Let's get started →", "Skip setup — go to dashboard",
category/model checkboxes, "Continue →", "← Back", "🚀 Launch Dashboard".

**Input fields?** Checkboxes only (categories: safety/factual/bias/hallucination/reasoning;
models: gpt/claude/gemini-pro/mistral/phi3/llama).

**Expected behavior?**
- "Skip setup" → jumps straight to dashboard (fastest path for automation).
- Step 2 "Continue" is **disabled** until ≥1 category is checked.
- Step 3 "Launch Dashboard" is **disabled** until ≥1 model is checked.
- Completing/skipping sets `onboarding_complete = True` → authenticated app + sidebar nav.

---

## 2. Leaderboard

**Surface:** UI page — `ui_pages/leaderboard.py` · **+ API** — `GET /api/leaderboard`

**What is displayed?**
- Title **"Model Leaderboard"** + caption "Compare models side-by-side ranked by dataset accuracy."
- Subheader **"Dataset Accuracy Rankings"** and a table with columns **Model · Dataset · Accuracy** (accuracy shown as a percentage).
- If no data: info message **"No leaderboard entries yet. Run a dataset evaluation in Prompt Dataset to see results here."**

**What can the user click?**
- **🗑 Clear Leaderboard** button.
- Column headers of the table (Streamlit dataframes are click-to-sort).

**What input fields exist?**
- None (read-only view + one action button).

**Expected behavior?**
- Aggregates entries from `dataset_leaderboard.json` + standard `results.json`, sorts by accuracy desc, de-dupes per model/dataset.
- **Clear Leaderboard** deletes the cache file and reruns → table empties / info message returns.

**API equivalent — `GET /api/leaderboard`**
Returns per-model ranking computed from `results.json`:
```json
{ "leaderboard": [
  { "model": "phi3", "avg_trust_score": 0.874, "prompt_count": 5, "rank": 1 },
  { "model": "gpt",  "avg_trust_score": 0.761, "prompt_count": 68, "rank": 2 }
]}
```
- Sorted descending by `avg_trust_score`; ranks are sequential from 1.
- **Note:** UI ranks by *accuracy*; API ranks by *avg trust score* — different metrics, worth flagging.

---

## 3. Models

**Surface:** **API-only** — `GET /api/models`. **No dedicated UI page.**

**Where it appears in the UI instead?**
- Onboarding Step 3 (model selection cards).
- Run Evaluation page (model selectbox: phi, gpt, claude, mistral, gemini-pro).

**What is displayed? / clickable? / inputs?**
- As an API there is no UI; the response is the "display".
- In the UI, the only model control is a **dropdown** inside Run Evaluation (and checkboxes in onboarding).

**Expected behavior — `GET /api/models`**
```json
{ "models": ["claude","gemini-pro","gpt","mistral","phi","phi3"], "count": 6 }
```
- Returns the unique model names found in `results.json`, sorted alphabetically.
- **QA observation:** the API model list (`phi3`, `gemini-pro`) and the Run-Evaluation
  dropdown (`phi`, no `phi3`) are **not identical** — a real data-consistency finding.

---

## 4. Evaluation

**Surface:** UI page — `ui_pages/run_eval.py` (titled "Run Evaluation") · **+ API** — `POST /api/evaluate`

**What is displayed?**
- Title **"Run Evaluation"** + caption "Select a model and category, then run a new evaluation batch."
- Two dropdowns, a slider, a button. After running: a **progress bar** then a green **success** message.

**What can the user click?**
- **Select Model** dropdown → `phi, gpt, claude, mistral, gemini-pro`.
- **Category** dropdown → `factual, reasoning, bias, safety, jailbreak`.
- **Run Evaluation** button.

**What input fields exist?**
- Model dropdown, Category dropdown, **"Number of Prompts"** slider (range 1–50, default 10).

**Expected behavior?**
- Click **Run Evaluation** → "Running evaluation..." + progress bar fills 0→100%.
- On completion → **"Evaluation completed — N results saved for {model}"**.
- Results are *simulated* (random scores) and appended to `results.json`. No model API/Ollama call here.

**Test hooks (for Selenium)**
- Selectboxes: `[data-testid="stSelectbox"]` (1st = model, 2nd = category)
- Slider: `[data-testid="stSlider"]`
- Run button: `[data-testid="stButton"] button`
- Success: `[data-testid="stAlert"]` (success variant)

**API equivalent — `POST /api/evaluate`**
Request: `{ "prompt": str, "model": str, "category": str }`
Response (200): `prompt_type`, `hallucination`, `correctness`, `relevance`, `clarity`, `safety`, `trust_score`.
- Empty/whitespace prompt → **400**. Prompt > 2000 chars → **400**. Missing field → **422** (schema).
- Prompt containing e.g. *"ignore previous instructions"* → `prompt_type: "Injection"`.

---

## 5. Results

**Surface:** UI page — `ui_pages/prompt_explorer.py` (titled "Prompt Explorer") · **+ API** — `GET /api/results`

**What is displayed?**
- Title **"Prompt Explorer"** + caption "Browse and filter individual prompts, model responses, and per-prompt trust scores."
- A category filter, then a repeating block per record: **Prompt** heading, prompt text,
  a **"Model Response"** expander, **Trust Score**, **Category**, divider.

**What can the user click?**
- **Filter by Category** dropdown (`All` + each category).
- Each **"Model Response"** expander (collapsed by default) to reveal the full response.

**What input fields exist?**
- Category filter dropdown only.

**Expected behavior?**
- Selecting a category filters the list to matching records; `All` shows everything.
- Expanders toggle the response text open/closed.

**API equivalent — `GET /api/results`**
Query params: `page` (≥1), `limit` (1–100), `model`, `category`.
```json
{ "total": 161, "page": 1, "limit": 20, "pages": 9, "results": [ ... ] }
```
- `?model=gpt` / `?category=factual` filter; combine both freely.
- `page` beyond range → empty `results` array (not an error).
- Each record carries `id, category, prompt, response, model, trust_score, ...`.

---

## 6. Feedback

**Surface:** **API-only** — `POST /api/feedback`. **No dedicated UI page** (yet).

**What is displayed? / clickable? / inputs?**
- No UI page exists. There is currently **no way in the web app** to submit feedback —
  this is a **coverage gap** and a candidate for a future UI form.

**Expected behavior — `POST /api/feedback`**
Request: `{ "result_id": str, "rating": int (1–5), "comment": str? }`
```json
{ "status": "saved", "feedback_id": "<uuid>" }
```
- `rating` outside 1–5 (e.g. 0, 6, -1) → **400**.
- Missing `result_id` or `rating` → **422** (schema).
- `comment` is optional.
- Persists to `reports/feedback.json` (thread-safe append with a lock).

---

## Cross-cutting testability notes

- **Streamlit renders async over WebSocket.** After any click the DOM re-renders;
  Selenium must use **explicit waits** (`WebDriverWait` + `expected_conditions`), never `sleep()`.
- **Session persists server-side.** A reused browser session stays logged in;
  login tests must `delete_all_cookies()` + reload to force a fresh session.
- **No stable element IDs.** Streamlit emits `data-testid` attributes (e.g. `stTextInput`,
  `stButton`, `stSelectbox`) and custom CSS classes (`.metric-card`) — not the generic
  `id="model-select"` style locators a typical roadmap assumes. Locators above reflect reality.
- **422 vs 400 on the API.** 422 = Pydantic schema violation (missing/wrong-type field);
  400 = business-rule rejection (empty prompt, out-of-range rating). Tests should assert the *right* one.

## QA findings worth logging (before automation)

| # | Finding | Type |
|---|---------|------|
| F1 | "Models" and "Feedback" have **no UI page** — API-only surfaces | Coverage gap |
| F2 | Login has **no field-level validation** (empty fields → generic invalid error) | Usability |
| F3 | Model list differs: API has `phi3`, Run-Eval dropdown has `phi` | Data consistency |
| F4 | Leaderboard ranks by **accuracy** (UI) vs **avg trust score** (API) | Metric mismatch |
| F5 | Run Evaluation produces **random/simulated** scores, not real model output | Behavior to verify |
| F6 | Social login buttons are **non-functional** demo stubs | Known limitation |

---

*Next step: with the surface mapped, build the test suites — Postman/pytest against
the API (port 8000) and Selenium against the UI (port 8501), using the hooks above.*
