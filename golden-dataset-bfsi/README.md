# golden-dataset-bfsi

Golden dataset builder and layered document-fraud detection engine for Indian BFSI lending.

Ingests real bank statements supplied by partner banks, injects controlled tampering to create labelled training data, and runs a cost-ascending cascade of detection layers returning a calibrated fraud probability plus machine-readable reason codes.

**Read [`CLAUDE.md`](CLAUDE.md) before contributing.** It documents invariants that silently destroy the dataset if broken.
Work is tracked in [`TASKS.md`](TASKS.md).

## Quick start

```bash
make install
make fixture     # synthetic CI statement - tests never touch real data
make test
make demo        # generate one corpus slice, print the summary
```

## What works today

| Component | Status |
|---|---|
| Label schema + expected-detecting-layer map | working |
| Ledger with recompute-aware tamper propagation | working |
| Method A — PDF-native content-stream edit, 3 stealth levels | working |
| Benign re-save controls | working |
| Method B — raster inpaint + pixel masks | working |
| Method C — copy-move | working |
| Method E — print-scan simulation | working |
| L0 provenance forensics | working (prototype) |
| Corpus grid orchestrator | working |
| Ingest / template classification | T-01 |
| L2 arithmetic (port from BSA) | T-02 |
| L1 pixel forensics | T-08 |
| L3 / L4 / L6 | T-09 / T-10 / T-11 |

## The finding that shapes the architecture

Measured with the shipped L0 detector on the reference corpus:

| stealth | recompute | L0 score | catches it |
|---|---|---|---|
| 0 | No | 1.00 | L0 + L2 |
| 0 | Yes | 1.00 | L0 |
| 1 | No | 0.00 | L2 only |
| 1 | **Yes** | 0.00 | **nothing** |
| 2 | No | 0.00 | L2 only |
| 2 | **Yes** | 0.00 | **nothing** |

Restoring the producer string takes a forger about thirty seconds and zeroes L0 completely. Add a recomputed ledger and both deterministic layers go silent. Those two cells are the ADVERSARIAL slice, and their recall is the only number that says what the system is worth against someone competent.

Separately: a **benign re-save** — an authentic statement re-saved by a mail gateway or page-merge tool, content unchanged — also scores **1.00 on L0**, identical to real tampering. Benign controls are therefore mandatory in the corpus, not optional.

## Data handling

`data/raw/` holds real client statements and is gitignored. Tests use only the synthetic fixture. If you find real client data staged for commit, stop and flag it.
