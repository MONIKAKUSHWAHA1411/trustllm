"""Generate one corpus slice from the CI fixture and print the summary.

This is the smoke test for the whole generation path. Run `make demo`.
"""
from decimal import Decimal
from pathlib import Path

from golden_dataset.ledger import Ledger, Txn
from golden_dataset.layers.l0_provenance import l0_provenance
from golden_dataset.tamper.grid import BaseDocument, CorpusGrid, summarise

FIXTURE = Path("data/raw/fixture_hdfc_apr2025.pdf")

ROWS = [
    (1, "03/04/2025", "UPI/DR/508812/GROCERY",       "2340.00",      "0", "110000.00"),
    (2, "05/04/2025", "NEFT/CR/ACME PVT LTD/SALARY",      "0", "185000.00", "295000.00"),
    (3, "09/04/2025", "ACH/DR/HDFC HOME LOAN EMI",  "42500.00",      "0", "252500.00"),
    (4, "12/04/2025", "UPI/DR/771203/FUEL",          "3800.00",      "0", "248700.00"),
    (5, "18/04/2025", "IMPS/DR/RENT PAYMENT",       "35000.00",      "0", "213700.00"),
    (6, "22/04/2025", "UPI/CR/442119/REFUND",              "0",  "1250.00", "214950.00"),
    (7, "28/04/2025", "ATM/DR/CASH WDL",           "10000.00",      "0", "204950.00"),
]


def main() -> None:
    if not FIXTURE.exists():
        raise SystemExit("run `make fixture` first")

    ledger = Ledger(
        [Txn(row=r, page=0, date=d, narration=n,
             debit=Decimal(dr), credit=Decimal(cr), balance=Decimal(b))
         for r, d, n, dr, cr, b in ROWS],
        opening_balance=Decimal("112340.00"),
    )
    ok, breaks = ledger.verify()
    print(f"L2 on authentic fixture: ok={ok} breaks={breaks}")
    assert ok, "fixture ledger must reconcile before it can be used as a base"

    base = BaseDocument(
        pdf_path=FIXTURE,
        bank="HDFC",
        borrower_id_hash="fixture-not-a-real-borrower",
        ledger=ledger,
        page_heights_pt=[841.89],
        editable_fields={"salary_credit": (0, "185000.00")},
    )

    grid = CorpusGrid(
        out_dir=Path("data/corpus"),
        mask_dir=Path("data/masks"),
        dataset_version="0.1.0-dev",
    )
    samples = grid.generate(
        base, target_field="salary_credit", target_row=2,
        delta=Decimal("100000.00"),
        raster_bbox=[440.0, 631.0, 468.0, 640.0],
    )

    print(f"\ngenerated {len(samples)} samples")
    print(summarise(samples))

    print(f"\n{'sample':<20} {'difficulty':<13} {'L0':>5}  expected detectors")
    print("-" * 78)
    for s in samples:
        if s.artifact_path.suffix != ".pdf":
            continue
        score = l0_provenance(s.artifact_path)["l0_score"]
        kind = "AUTHENTIC" if s.label.is_authentic else "tampered"
        print(f"{kind:<20} {s.label.difficulty.value:<13} {score:>5}  "
              f"{s.label.expected_detecting_layers}")

    print("\nNote: benign re-saves score as high as real tampering on L0.")
    print("That is why they are mandatory - see CLAUDE.md invariant 1.")


if __name__ == "__main__":
    main()
