# TASKS.md

Ordered backlog. Each task is scoped to one Claude Code session. Invoke by ID:
`"Work on T-03. Read CLAUDE.md first."`

Status: `TODO` · `WIP` · `DONE` · `BLOCKED`

---

## Phase 1 — Corpus foundation (weeks 1–3)

### T-01 · Real-statement ingest and template classification — `TODO`
**Files:** `src/golden_dataset/extract/classify.py`, `src/golden_dataset/extract/pdf_structure.py`

Build the ingest path that turns a directory of real bank PDFs into `BaseDocument` objects.

- Classify each PDF: bank (from header text + producer string), text-layer vs scanned, page count, statement period.
- Extract the transaction table into `Txn` objects with `balance_bbox` and `amount_bbox` populated from `pdfplumber.extract_words()`.
- Assign `source_document_id` (sha256 of bytes) and `borrower_id_hash` (keyed HMAC of account number — key from env, never committed).
- Emit a coverage report: statements per bank, per format, text-layer ratio.

**Acceptance:** runs over `data/raw/`, produces `BaseDocument` for ≥90% of inputs, unparsed ones logged with a reason. Coverage report written to `data/reports/ingest_coverage.json`.

**Watch for:** bank statement tables are not uniform. Do not write one parser and assume it generalises — build per-template extractors behind a common interface, and make the fallback loud rather than silent.

---

### T-02 · Port `balance_reconcile_v2` from BSA into L2 — `WIP`
**Files:** `src/golden_dataset/layers/l2_arithmetic.py`, `src/golden_dataset/cli.py`

**Progress:** Reconciler implemented (row running-balance with re-anchor,
page-boundary continuity, date monotonicity, sequence gaps, structured
`{code,severity,evidence}` flags, Decimal throughout). Archive reporter
(`reconcile_archive`) + serialised-ledger loader + `gds reconcile` CLI wired.
Covered by `tests/test_l2_arithmetic.py`. **Still blocked:** the "run across the
entire authentic archive / first CTO finding" half needs T-01 ingest and the
real `data/raw/` archive, neither of which exists yet — the reporter runs and
honestly reports zero until then.

Port the anchored global solver from the BSA repo. This is the highest-precision layer in the system.

- Row-level running balance: `opening + Σcredits − Σdebits = closing`, checked at every row.
- Page-boundary continuity: closing of page *n* == opening of page *n+1*.
- Date monotonicity, transaction-sequence gaps.
- Re-anchor after a break so one error does not cascade into "every row is broken".
- Return structured flags with page, row, and the exact delta.

**Acceptance:** ≥0.98 precision on hard-fails. Run across the entire authentic archive and produce a report.

**This task produces the first CTO-visible finding.** Any *already-approved* statement that fails reconciliation as received is either a parser bug or a fraud that was already funded. Both are worth reporting. Do this before any model work.

---

### T-03 · Corpus generation at scale — `TODO`
**Files:** `src/golden_dataset/tamper/grid.py` (exists), `src/golden_dataset/cli.py`

Wire `CorpusGrid` to the T-01 ingest and run the full grid.

- CLI: `gds generate --input data/raw --out data/corpus --workers 8`
- Parallelise per base document. Deterministic seeding per document so runs are reproducible.
- Emit a manifest: `data/corpus/manifest.jsonl`, one label per line.
- Progress + failure summary. A failed base document must not abort the run.

**Acceptance:** 4,000 bases → ~84,000 samples. `summarise()` shows the expected difficulty distribution and a non-zero `no_expected_detector` count (those are the ADVERSARIAL cells — their presence is correct).

**Before generating at scale:** manually eyeball 200 masks overlaid on their images, and verify the `/Producer` string of 50 outputs by hand. These are the two failures that silently ruin a corpus. Write `scripts/qa_sample.py` to make this a one-liner.

---

### T-04 · True incremental-save generation — `TODO`
**Files:** `src/golden_dataset/tamper/incremental.py` (new)

pikepdf cannot emit incremental updates. Hand-roll it: original bytes + new objects + new xref carrying `/Prev <original_startxref>` + second `%%EOF`.

**Acceptance:** output opens cleanly in Acrobat and pdfplumber; `L0_INCREMENTAL_SAVE` and `L0_XREF_PREV_CHAIN` both fire; content edit is present. ~2 days.

**Why it matters:** without this, those two L0 features look worthless on synthetic evaluation and are highly informative in production. Do not let anyone drop them on synthetic evidence.

---

### T-05 · Leakage-safe splitting — `TODO`
**Files:** `src/golden_dataset/splits.py`

- Group by `source_document_id`, then by `borrower_id_hash`. Every sample derived from one base lands in the same split.
- Stratify on bank template and difficulty grade so no split is missing a slice.
- Near-duplicate detection across splits: perceptual hash on rendered pages + text shingling.
- Frozen eval set: separate directory, access-logged, hard query budget (default 20) tracked in a counter file.

**Acceptance:** a test proves that no `source_document_id` appears in two splits, and that exceeding the eval query budget raises.

---

## Phase 2 — Detection layers (weeks 4–10)

### T-06 · L0 hardening and benign calibration — `TODO`
**Files:** `src/golden_dataset/layers/l0_provenance.py`

Current L0 is a working prototype. Harden it:
- Digital signature validation (byte-range + chain) — an invalid signature is a hard reject.
- XMP `xmpMM:History` / `DocumentID` vs `InstanceID` mismatch.
- Text-object geometry: baseline offset and `Tz`/`Tc` inconsistency within a column.
- Object-level anomalies: orphaned objects, free-list gaps, generation-number mismatch.
- **Calibrate the threshold against the benign re-save controls.** Set the operating point where benign re-saves do not fire.

**Acceptance:** benign re-save FPR ≤ 0.01 while stealth-0 tamper recall ≥ 0.95.

---

### T-07 · AI-inpainting tamper slice — `TODO`
**Files:** `src/golden_dataset/tamper/ai_inpaint.py` (new)

Wire a diffusion inpainter into `CorpusGrid.ai_inpaint_fn`. Self-hosted only — never send real client documents to a third-party image API.

**Acceptance:** ≥2 AI-inpainted variants per base, masks pass sanity, human review of 50 samples confirms the edits are visually plausible.

**Priority note:** this is the slice that defeats current detectors (AUC 0.51–0.75). A corpus without it has a blind spot exactly where the market is heading. Not a v2 item.

---

### T-08 · L1 pixel forensics — `TODO`
**Files:** `src/golden_dataset/layers/l1_pixel/`

1. **Baseline first:** fine-tune TruFor on our corpus. Two days. This is the number to beat.
2. **Then:** two-stream Swin-T (RGB + SRM noise residual + DCT/quant-table) + FPN decoder + segmentation head, ~35M params.

Config in `docs/02-model-selection.md`. Loss must be `0.5·Dice + 0.3·Focal + 0.2·BCE(pos_weight≈50)` — plain BCE predicts all-zero at 1:1430 imbalance.

JPEG-quality randomisation (60–95) and quantisation-table sampling are the critical augmentations, more important than the architecture.

**Acceptance:** beats fine-tuned TruFor on per-difficulty Pixel-F1. **If it does not, ship TruFor.** Report per difficulty grade and per bank, never blended.

---

### T-09 · L3 cross-document entity matching — `TODO`
Name matching with Indian-name-aware fuzzy logic (initials, patronymics, transliteration variance, order swaps). Account/IFSC agreement with the cancelled cheque. Payslip vs salary credit. ITR/Form-16 vs inferred income. GST turnover vs current-account credits. UIDAI offline eKYC XML signature verification — deterministic, hard gate.

---

### T-10 · L4 behavioural features — `TODO`
Benford first-two-digit conformance, round-number density, salary-credit regularity (amount/day/narration/employer variance), balance velocity and pre-application window-dressing, circular transactions, mule signatures (dormancy→activation, structuring below thresholds).

**Strategic note:** L4 is the only layer that survives Account Aggregator adoption. AA makes forgery structurally impossible but a borrower can still manufacture *behaviour*. This is the durable moat — resource it accordingly.

---

### T-11 · L6 fusion, calibration, reason codes — `TODO`
LightGBM over all upstream features → isotonic calibration on a dedicated split → SHAP reason codes mapped to a versioned taxonomy.

**Acceptance:** ECE ≤ 0.05. 100% of RED_FLAG/REJECT decisions carry ≥1 human-readable reason code with structured evidence. Response includes `model_version` + `dataset_version`.

---

## Phase 3 — Serving (weeks 10–14)

### T-12 · FastAPI + Celery service — `TODO`
Reuse the BSA async job architecture. Three services on the existing EKS cluster: API (CPU), workers (CPU), inference (1× L4 shared by OCR + L1 + narrative LLM).

### T-13 · Shadow mode — `TODO`
Live traffic, decisions logged not enforced, analyst feedback loop. **Minimum 4 weeks before any automated rejection reaches a real borrower.** Non-negotiable.

### T-14 · Drift monitoring and retraining — `TODO`
Evidently on feature distributions. Parse-failure rate per bank as the template-churn alarm. Quarterly red-team refresh of the adversarial slice.

---

## Backlog / not scheduled

- Account Aggregator (L−1) integration via a TSP — Finvu / Setu / Anumati. Not an NBFC-AA licence.
- L5 external verification router with a hard monthly budget cap and circuit breaker.
- Reject-inference correction for the training-label bias.
- Fairness audit across bank type, region, loan size.
