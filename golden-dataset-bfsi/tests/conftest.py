from decimal import Decimal
from pathlib import Path

import pytest

from golden_dataset.ledger import Ledger, Txn

ROWS = [
    (1, "03/04/2025", "UPI/DR/508812/GROCERY",       "2340.00",      "0", "110000.00"),
    (2, "05/04/2025", "NEFT/CR/ACME PVT LTD/SALARY",      "0", "185000.00", "295000.00"),
    (3, "09/04/2025", "ACH/DR/HDFC HOME LOAN EMI",  "42500.00",      "0", "252500.00"),
    (4, "12/04/2025", "UPI/DR/771203/FUEL",          "3800.00",      "0", "248700.00"),
    (5, "18/04/2025", "IMPS/DR/RENT PAYMENT",       "35000.00",      "0", "213700.00"),
    (6, "22/04/2025", "UPI/CR/442119/REFUND",              "0",  "1250.00", "214950.00"),
    (7, "28/04/2025", "ATM/DR/CASH WDL",           "10000.00",      "0", "204950.00"),
]


@pytest.fixture
def ledger() -> Ledger:
    return Ledger(
        [Txn(row=r, page=0, date=d, narration=n, debit=Decimal(dr),
             credit=Decimal(cr), balance=Decimal(b)) for r, d, n, dr, cr, b in ROWS],
        opening_balance=Decimal("112340.00"),
    )


@pytest.fixture(scope="session")
def fixture_pdf(tmp_path_factory) -> Path:
    """Synthetic statement. Tests must NEVER touch data/raw/ (real client data)."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
    from make_fixture_statement import build_base_statement

    out = tmp_path_factory.mktemp("fixture") / "stmt.pdf"
    build_base_statement(out)
    return out
