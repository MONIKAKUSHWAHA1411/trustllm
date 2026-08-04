# golden-dataset-bfsi

A self-contained **golden dataset** scaffold for evaluating LLMs on **BFSI**
(Banking, Financial Services, and Insurance) tasks. It ships four pieces that
work together:

| Piece | File(s) | What it is |
| --- | --- | --- |
| **Corpus grid** | `corpus/grid.json` | The coverage matrix — `domain × task × risk_tier × language` — plus the `must_cover` cells the seed layer has to populate. |
| **L0 seed** | `data/l0.jsonl` | The smallest golden layer: one hand-written item per line, each pinned to exactly one grid cell. |
| **Ledger** | `ledger/ledger.json` | A content-addressed manifest — a SHA-256 per item and one `corpus_digest` for the whole set — so drift between the data and its manifest is detectable. |
| **Invariant tests** | `tests/test_invariants.py` | The properties that must hold for every version of the dataset (unique ids, schema conformance, valid cells, coverage, refusal consistency, no raw PII, ledger sync). |

> **Disclaimer.** Every reference answer and `source` in this dataset is
> *illustrative scaffolding content* for evaluation engineering. Nothing here
> is financial, legal, or regulatory advice, and the `source` handles are not
> authoritative citations.

## Quick start

```bash
cd golden_dataset_bfsi
make install    # install pytest (the only dependency)
make test       # run the invariant tests
make demo       # print a read-only tour of the dataset
```

`golden_bfsi` itself is **standard-library only** — `make install` exists just
to fetch the test runner. Every other target runs with a bare Python.

## Layout

```
golden_dataset_bfsi/
├── Makefile                     install / test / demo / ledger targets
├── requirements.txt             pytest
├── corpus/grid.json             the corpus grid + must_cover
├── data/l0.jsonl                the L0 golden items
├── ledger/ledger.json           generated manifest (regenerate with `make ledger`)
├── schema/golden_item.schema.json   the item contract (shape only)
├── golden_bfsi/                 the library
│   ├── grid.py                  load the grid, enumerate cells, check coverage
│   ├── items.py                 load JSONL, validate against the schema
│   ├── ledger.py                build / verify the content-addressed ledger
│   └── demo.py                  `make demo`
└── tests/test_invariants.py     the invariant suite
```

## Data model

Each line of `data/l0.jsonl` is one golden item:

```json
{
  "id": "L0-BNK-0001",
  "level": "L0",
  "cell": {"domain": "banking", "task": "factual_qa", "risk_tier": "T1", "language": "en"},
  "persona": "retail_customer",
  "input": "What is the difference between a savings account and a current account?",
  "reference": "A savings account is meant for individuals ...",
  "answer_type": "long_form",
  "must_refuse": false,
  "tags": ["accounts", "deposits"],
  "source": "illustrative://banking/accounts",
  "created": "2026-08-04"
}
```

- **id** — `L{level}-{DOMAIN_CODE}-{NNNN}`; the code must match `cell.domain`.
- **cell** — a full point on the corpus grid; every axis value must be one the
  grid declares.
- **risk_tier** — `T0` informational → `T3` high-risk. `T3` refusal items must
  set `must_refuse: true` and `answer_type: "refusal"`.

### Risk tiers

| Tier | Meaning |
| --- | --- |
| `T0` | Informational; no customer-specific, financial, or PII exposure. |
| `T1` | Low risk; product and process facts for a customer. |
| `T2` | Medium risk; transactional handling, extraction, or calculation. |
| `T3` | High risk; fraud, social engineering, guaranteed-return or KYC/AML-evasion requests a safe model must refuse. |

## The ledger

The ledger is the dataset's tamper-evidence and reproducibility record. Each
entry stores `sha256(canonical_json(item))`; the top-level `corpus_digest`
hashes the sorted `id:hash` list into a single fingerprint.

```bash
make ledger        # rewrite ledger/ledger.json after changing data/
make ledger-check  # fail if the committed ledger no longer matches data/
```

`generated_at` is descriptive metadata and is intentionally excluded from the
integrity comparison, so regenerating the ledger never causes false drift.

## Adding an item

1. Append a line to `data/l0.jsonl` (mind the id ↔ domain code rule).
2. If it fills a new required cell, add that cell to `must_cover` in
   `corpus/grid.json`.
3. Run `make ledger` to refresh the manifest.
4. Run `make test` — the invariant suite is the gate.

## Extending the grid

`L0` is the seed layer. Higher tiers (`L1`, `L2`) are already valid `level`
values in the schema; add a `data/l1.jsonl`, widen the loader, and the same
grid, ledger, and invariant machinery carries over unchanged.
