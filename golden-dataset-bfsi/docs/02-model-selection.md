# Model Selection & Build Architecture
### Golden Dataset + Fraud Detection — Implementation Spec

Companion to the CTO brief. This answers two questions concretely: **which models**, and **how the golden dataset gets built now that real bank statements are available under legal cover.**

---

## 0. What changed now that you have real statements

Last iteration assumed a synthetic-first corpus for legal reasons. With real bank PDFs cleared for use, **the strategy inverts and gets significantly better**:

| | Old plan (synthetic-first) | New plan (real-base injection) |
|---|---|---|
| Authentic class | Generated from 40 templates | **Real bank statements, unchanged** |
| Tampered class | Generated statement + generated tamper | **Real statement + injected tamper** |
| Domain gap | Large — model learns the generator | **Small — only the tampered region is synthetic** |
| Template coverage | Whatever you build | Whatever the banks actually sent |
| Timeline to corpus v1 | 6 weeks | **3 weeks** |

The template generator still has one job: covering banks where you received no authentic sample, and providing CI test fixtures that never touch real data. Everything else is injection into real documents.

> One thing worth confirming in writing since it's cheap: bank sign-off and borrower consent are different instruments under DPDP. The data subject is the borrower, not the bank. If the bank's own consent notice names model development as a purpose you're clear — just get that on paper in the file, because it's the first thing an auditor asks for.

---

## 1. Model Selection

### 1.1 The short answer

| Layer | Model | Params | Train time (1×L4) | Serving |
|---|---|---|---|---|
| L0 Provenance | **No model.** pikepdf + rules | — | — | CPU, ~5ms |
| L2 Arithmetic | **No model.** Anchored solver | — | — | CPU, ~50ms |
| OCR (scanned only) | **PaddleOCR-VL** or **dots.ocr** | 0.9B / 3B | Off-the-shelf | 1× L4, shared |
| L1 Pixel forensics | **Two-stream Swin-T + FPN** | ~35M | 8–12 hrs | Shares the L4 |
| L3 Entity matching | RapidFuzz + rules | — | — | CPU |
| L4 Behavioural | Feature engineering, no model | — | — | CPU |
| L6 Fusion | **LightGBM** + isotonic + SHAP | ~1MB | 4 min | CPU, <10ms |
| Narrative | Qwen3-8B-Instruct, self-hosted | 8B | — | Shares the L4, async |

**Total GPU requirement: one L4 (24GB) or A10G.** Nothing here needs a cluster. Anyone proposing multi-GPU has misread the problem.

### 1.2 L1 — the only model choice that requires real thought

**Recommendation: two-stream Swin-Tiny + FPN decoder, segmentation head.**

```
                    ┌─ RGB stream ──────────┐
input 512×512 ──────┼─ SRM noise residual ──┼── Swin-T (shared) ── FPN ── seg head ── mask
                    └─ DCT / quant-table ───┘                              └─ pooled ── image score
```

Why each piece:

- **Swin-T over ViT-B** — 28M vs 86M params, windowed attention suits localised tampering better than global attention, trains ~3× faster. On a corpus this size, ViT-B overfits.
- **SRM noise-residual stream** — tampered regions break the sensor/compression noise pattern. This is the single strongest handcrafted prior in document forensics and it's nearly free to add.
- **DCT / quantisation-table stream** — the double-compression signature. DocQT showed that detectors trained on a narrow range of quantisation tables collapse on unseen ones, so both the corpus and the model need explicit quantisation diversity.
- **Segmentation head, not classification** — analysts need a heat-map showing *where*. A bare score is unusable in a show-cause notice.

**Baseline to beat: TruFor fine-tuned on your corpus.** In the DOCFORGE-BENCH zero-shot evaluation, TruFor was the strongest general forensics method across document datasets. Run it first as a two-day baseline, then justify your own model against it. If your Swin-T doesn't beat a fine-tuned TruFor, ship TruFor.

**Loss function — this is where most implementations fail.** Measured on the reference sample, the tampered region is **0.07% of page pixels — a 1:1430 imbalance.** Plain BCE converges to predicting all-zero and reports 99.93% pixel accuracy. Use:

```
L = 0.5 · Dice + 0.3 · Focal(γ=2, α=0.75) + 0.2 · BCE(pos_weight≈50)
```

**Training config:**
```yaml
input:        512×512 crops, stride 384 sliding window at inference
batch_size:   16 (AMP, ~9GB VRAM on L4)
optimiser:    AdamW, lr 3e-4, cosine decay, 5-epoch warmup
epochs:       40 (early stop on val Dice, patience 6)
augmentation:
  jpeg_quality: uniform random 60–95   # THE critical augmentation
  quant_table:  randomly sampled from a bank of 12 real tables
  rotation:     ±0.8°
  brightness:   ±12%
  resize:       0.8–1.2×
```

The JPEG quality randomisation matters more than the architecture. A model trained at fixed QF learns the compression signature of your generator, not the forgery.

### 1.3 Why LightGBM and not a neural net for L6

At ~50k feature rows with mixed types, gradient boosting matches or beats deep tabular models and trains in four minutes. More importantly, **RBI's Master Directions require a show-cause notice and a reasoned order** for fraud classification. SHAP values over LightGBM map directly onto reason codes an analyst can put in writing. A neural net cannot do that, and an LLM making the decision is a compliance liability.

Calibrate with isotonic regression on a dedicated split — not on train, not on eval.

### 1.4 What NOT to use

| Tempting | Why not |
|---|---|
| GPT-5/Claude/Gemini as fraud judge | Scored ~0.509 AUC (chance) on AI-forged documents in the AIForge-Doc benchmark. Also unexplainable and ships client PII offshore. |
| PyMuPDF | AGPL. Licensing exposure for a commercial BFSI product. Use **pypdfium2** (Apache/BSD) for rendering, pikepdf for structure. |
| Off-the-shelf forensics weights, unfine-tuned | Published methods failed to reach Pixel-F1 ≥ 0.3 on six of eight document datasets zero-shot. |
| Frontier VLM per page in the hot path | ~₹8–11/page against ₹0.20 self-hosted. |

---

## 2. Corpus Generation — the actual grid

The engine is built and tested (`golden_dataset/tamper/`). What you generate is a **grid**, not a pile.

### 2.1 The two axes that decide difficulty

**Axis 1 — stealth** (how much of the edit trail the forger cleans up)
**Axis 2 — recompute** (whether the forger fixed the downstream running balance)

Measured on the reference corpus with the shipped L0 detector:

| stealth | recompute | L0 score | Which layer catches it | Grade |
|---|---|---|---|---|
| 0 | No | **1.00** | L0 + L2 | EASY |
| 0 | Yes | **1.00** | L0 | MEDIUM |
| 1 | No | **0.00** | L2 only | MEDIUM |
| 1 | **Yes** | **0.00** | **nothing** | **ADVERSARIAL** |
| 2 | No | **0.00** | L2 only | MEDIUM |
| 2 | **Yes** | **0.00** | **nothing** | **ADVERSARIAL** |

**Read the two empty cells carefully.** A forger who restores the producer string *and* recomputes the ledger defeats both deterministic layers completely. Roughly thirty seconds of extra effort. Those cases are exactly what L1 pixel forensics exists for, and they're why L1 can't be descoped even though it's the weakest layer.

This is a correction to what I told you last session. I said L0 catches "the bulk of casual tampering" — true for *casual*, and it collapses to zero against anything else. Build the corpus so you measure that honestly instead of discovering it in production.

### 2.2 Generation matrix per authentic base document

For every real bank statement you hold, emit:

| Slice | Variants per base | Notes |
|---|---|---|
| Authentic (unchanged) | 1 | Negative class |
| **Benign re-save** | **3** | Different producer strings, content unchanged. **Mandatory.** |
| Authentic print-scan | 1 | Or the model learns scanned == fraud |
| PDF-native tamper | 6 | 3 stealth × 2 recompute |
| Raster inpaint | 4 | 2 fields × 2 JPEG QF |
| Copy-move | 2 | Cloned salary credit |
| AI inpaint | 2 | Diffusion edit on the amount field |
| Print-scan tamper | 2 | Physical loop simulation |
| **Total** | **21 samples per base** | ~4 authentic-class, ~17 tampered |

4,000 real base statements → **~84,000 samples**, of which ~16,000 are authentic-class. That's the corpus, and it's reachable in three weeks of compute.

### 2.3 The three controls people skip, and what happens

| Control | If you skip it |
|---|---|
| **Benign re-save** | L0 becomes a producer-string classifier. False-positives on every statement legitimately re-saved by an email gateway, DMS, or the borrower merging pages. Measured: benign re-saves score **1.00 on L0 — identical to real tampering.** |
| **Authentic print-scan** | Model learns "scanned == fraud". Catastrophic in Tier 2/3 where scanned submissions dominate. |
| **Recomputed-ledger variants** | Model learns "fraud == broken arithmetic". Misses every competent forger. |

### 2.4 Split discipline

Split by **`source_document_id` and `borrower_id_hash`**, never by sample. If a base statement's authentic version lands in train and its tampered version in eval, the model has already seen the page and your eval is meaningless. The label schema carries both keys for exactly this reason.

Frozen eval set: confirmed-fraud real cases only, physically separate bucket, access-logged, query budget of ~20 runs across the whole programme.

### 2.5 Known generator limitation — do not paper over this

pikepdf (qpdf) always performs a **full rewrite**. It cannot emit a true incremental update, so nothing this engine produces carries the multi-`%%EOF` / `/Prev`-chain signature that a real Acrobat "Save" leaves behind.

**Consequence:** `L0_INCREMENTAL_SAVE` and `L0_XREF_PREV_CHAIN` will look worthless when evaluated on synthetic data and will be highly informative in production. Do not drop those features on synthetic evidence.

To fix properly, either drive a real editor headlessly, or hand-append the update: original bytes + new objects + new xref with `/Prev <original_startxref>` + second `%%EOF`. Budget two days. Treat it as required, not optional.

---

## 3. Repo & Service Architecture

```
fraud-engine/
├── golden_dataset/
│   ├── extract/          # pdf_structure.py, classify.py, template_id.py
│   ├── tamper/
│   │   ├── core.py       # schema, Ledger, PdfNativeTamper, BenignResave  [BUILT]
│   │   └── raster.py     # inpaint, copy-move, print-scan, masks          [BUILT]
│   ├── pipeline.py       # orchestrator: base → 21 variants
│   └── splits.py         # leakage-safe splitting on doc + borrower keys
├── layers/
│   ├── l0_provenance.py  # deterministic                                 [BUILT]
│   ├── l1_pixel/         # Swin-T two-stream, train.py, infer.py
│   ├── l2_arithmetic.py  # port balance_reconcile_v2 from BSA
│   ├── l3_entity.py      # cross-document matching
│   ├── l4_behavioural.py # Benford, velocity, salary regularity, mule patterns
│   ├── l5_external.py    # AA, penny-drop, PAN — grey band only
│   └── l6_fusion.py      # LightGBM + isotonic + SHAP
├── serving/              # FastAPI + Celery, reuses BSA's async job layer
└── eval/                 # per-difficulty, per-bank, per-layer metrics
```

**Runtime:** three services on the existing EKS cluster — API (CPU), worker pool (CPU), inference (1× L4, shared by OCR + L1 + narrative LLM). No new operational surface beyond the GPU node.

---

## 4. Build Order

| Week | Deliverable | Why this order |
|---|---|---|
| 1 | Ingest real statements, template classification, `source_document_id` + `borrower_id_hash` assignment | Splits must exist before any sample is generated |
| 1–2 | Port `balance_reconcile_v2` into L2, run on the full authentic corpus | Any statement that fails reconciliation *as received* is either a parser bug or an already-fraudulent sample. Both are findings. |
| 2–3 | Run the generation grid → ~84k samples | Engine is built; this is compute, not development |
| 3 | Mask QA on a manual sample of 200; verify producer strings by hand | The two failure modes that silently destroy a corpus |
| 3–4 | L0 hardened + benign-control calibration | Set the threshold where benign re-saves don't fire |
| 4–7 | L1 training: TruFor baseline first, then two-stream Swin-T | Baseline before bespoke |
| 6–8 | L3 + L4 features | Independent of L1, can run parallel |
| 8–10 | L6 fusion, isotonic calibration, SHAP reason codes | Needs all upstream features |
| 10–14 | Shadow mode on live traffic | Logged, not enforced |

**First measurable value: Week 2.** Running L2 across the historical statement archive will surface reconciliation failures in documents already approved. That is a finding you can show the CTO before any model exists.

---

## 5. The Three Numbers to Track

1. **ADVERSARIAL-grade recall @ 2% FPR.** The (stealth≥1, recompute=True) cells. This is what the system is worth against a competent forger — everything else is measuring how well you catch amateurs.
2. **Benign re-save false-positive rate.** Must be near zero. It is the number that decides whether the system is deployable.
3. **Human review rate.** 67% of run cost. Every point matters more than any model improvement.
