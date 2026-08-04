# CLAUDE.md

Context for Claude Code working in this repository. Read this before making changes.

---

## What this is

A **golden dataset builder and layered document-fraud detection engine** for Indian BFSI lending, built at Timble Technologies. It ingests real bank statements supplied by partner banks, injects controlled tampering into them to create labelled training data, and runs a cascade of detection layers that returns a calibrated fraud probability plus machine-readable reason codes.

Owner: Monika Kushwaha, Tech Lead – AI.
Design docs live in `docs/`. Read `docs/02-model-selection.md` before touching any model code.

---

## Architecture in one screen

Detection runs as a **cost-ascending cascade**. Cheap deterministic layers first, expensive models last, short-circuit as early as possible.

| Layer | What it does | Model? | Cost |
|---|---|---|---|
| L−1 | Account Aggregator routing — signed bank data, forgery structurally impossible | no | ₹0 |
| **L0** | Provenance & file forensics (producer strings, xref chains, XMP, font subsets) | **no** | ₹0.002 |
| L1 | Pixel forensics on scans — two-stream Swin-T + FPN, outputs a tamper heat-map | yes | ₹0.05 |
| **L2** | Arithmetic reconciliation — running balance, page continuity, date monotonicity | **no** | ₹0.01 |
| L3 | Cross-document entity matching (statement ↔ PAN ↔ Aadhaar ↔ ITR ↔ payslip) | no | ₹0.02 |
| L4 | Behavioural & statistical (Benford, salary regularity, velocity, mule patterns) | no | ₹0.03 |
| L5 | External verification — only in the grey band | no | ₹5.00 |
| **L6** | Fusion: LightGBM + isotonic calibration + SHAP reason codes | yes | ₹0.001 |

L0 and L2 carry most of the precision. L1 is the weakest layer and the most likely to disappoint — treat its output as a feature into L6, never as a standalone verdict.

---

## Non-negotiable invariants

Breaking any of these silently destroys the dataset or the product. If a change appears to require breaking one, stop and ask.

### Corpus generation

1. **Benign re-save controls are mandatory.** `GridConfig.benign_resaves` must be ≥ 1. These are authentic documents re-saved through a non-bank producer with content unchanged. Measured: they score **1.00 on L0 — identical to real tampering.** Remove them and L0 becomes a producer-string classifier that rejects every statement legitimately re-saved by a mail gateway, DMS, or page-merge tool. `GridConfig.validate()` enforces this; do not weaken it.

2. **Authentic print-scan controls are mandatory.** Apply `print_scan()` to authentic samples at the same rate as tampered ones, or the model learns `scanned == fraud`. Catastrophic in Tier 2/3 markets where scanned submissions dominate.

3. **Every numeric tamper is emitted in both recompute variants.** `recompute=False` breaks the running balance and L2 catches it. `recompute=True` rewrites every downstream balance so the arithmetic still closes and L2 is blind. A corpus with only the former teaches the model that fraud means broken arithmetic.

4. **Mask failures fail loudly.** `mask_sanity()` raising in `grid._raster()` is intentional. A silently empty mask trains the localisation head on a tampered image labelled as having no tampered pixels. Never downgrade that to a warning.

5. **Split by `source_document_id` AND `borrower_id_hash`, never by sample.** If a base statement's authentic version lands in train and its tampered version in eval, the model has already seen the page.

6. **The frozen eval set has a query budget.** Confirmed-fraud real cases only, ~20 eval runs across the whole programme. Enforced in `splits.py`, not by policy.

### Code

7. **No PyMuPDF.** AGPL — licensing exposure for a commercial BFSI product. Use `pypdfium2` (Apache/BSD) for rendering, `pikepdf` for structure, `pdfplumber` for text geometry.

8. **`pikepdf.open_metadata()` stamps pikepdf into `/Producer`.** Always write `pdf.docinfo["/Producer"]` directly, or pass `set_pikepdf_as_editor=False`. Miss this and every generated sample carries a pikepdf producer string; the detector then learns to find our own generator, scores ~1.0 offline, and is useless in production.

9. **L6 must stay explainable.** LightGBM + SHAP. RBI's Master Directions on Fraud Risk Management require a show-cause notice and a *reasoned order* for fraud classification. No neural net, no LLM, in the decision path. An LLM may generate the analyst narrative *from* reason codes — never the codes themselves.

10. **No frontier VLM in the hot path.** ~₹8–11/page vs ₹0.20 self-hosted, and it ships client PII offshore. Self-hosted models only for anything touching real client data.

11. **Every API response carries `model_version` and `dataset_version`.** When a rejection is challenged twelve months later we must reconstruct which model and which data produced it.

---

## Known limitations — do not paper over these

**pikepdf cannot produce true incremental saves.** qpdf always does a full rewrite, so nothing this engine generates carries the multi-`%%EOF` / `/Prev`-chain signature a real Acrobat "Save" leaves. Consequence: `L0_INCREMENTAL_SAVE` and `L0_XREF_PREV_CHAIN` will look worthless on synthetic evaluation and be highly informative in production. **Do not drop those features based on synthetic evidence.** Fix is task T-04.

**L0 collapses against a competent forger.** Measured on the reference corpus:

| stealth | recompute | L0 score | catches it |
|---|---|---|---|
| 0 | No | 1.00 | L0 + L2 |
| 0 | Yes | 1.00 | L0 |
| 1 | No | 0.00 | L2 only |
| 1 | **Yes** | 0.00 | **nothing** |
| 2 | No | 0.00 | L2 only |
| 2 | **Yes** | 0.00 | **nothing** |

The two empty cells are why L1 cannot be descoped despite being the weakest layer.

**Pixel forensics generalises poorly.** Published detectors failed to reach Pixel-F1 ≥ 0.3 on six of eight document datasets zero-shot, and the dominant failure was calibration, not discrimination. On AI-inpainted forgeries, TruFor drops to AUC 0.751, DocTamper to 0.563, GPT-4o to 0.509 (chance). Calibrate on our own data; never adopt a published threshold.

**Pixel class imbalance is ~1:1430.** Tampered regions are ~0.07% of page pixels. Plain BCE converges to all-zero and reports 99.93% pixel accuracy. Use `0.5·Dice + 0.3·Focal(γ=2, α=0.75) + 0.2·BCE(pos_weight≈50)`.

---

## Conventions

- Python 3.11+, `src/` layout, absolute imports within the package.
- Type hints on all public functions. `from __future__ import annotations` at the top of every module.
- Money is `Decimal`, never `float`. A float running-balance reconciler will produce spurious breaks and you will chase them for days.
- Dataclasses for schema objects, not dicts.
- Every detection flag returns structured `evidence`, because a RED_FLAG an analyst cannot justify in writing is useless.
- No new dependency without a licence check. Permissive only (MIT/BSD/Apache). Note it in `pyproject.toml` with a one-line rationale.
- Tests use the synthetic fixture in `scripts/make_fixture_statement.py`. **Tests must never touch `data/raw/`** — that is real client data.

## Commands

```bash
make install      # editable install + dev deps
make fixture      # build the synthetic CI statement
make test         # pytest
make lint         # ruff + mypy
make demo         # generate one corpus slice from the fixture, print the summary
```

## Do not commit

`data/raw/` (real client statements), `data/corpus/`, `*.pdf`, `*.jpg`, `.env`, model weights. See `.gitignore`. If you find real client data staged, stop and flag it.

---

## Metrics that matter

Never report accuracy. At a ~12% fraud base rate, predicting "authentic" for everything scores 88%.

1. **ADVERSARIAL-grade recall @ 2% FPR** — the (stealth≥1, recompute=True) cells. What the system is worth against a competent forger.
2. **Benign re-save false-positive rate** — must be near zero. Decides whether this is deployable at all.
3. **Precision @ fixed 2% FPR**, PR-AUC (not ROC-AUC), expected calibration error ≤ 0.05.
4. Always break metrics down **per difficulty grade and per bank template**. A blended number hides the failure modes.
