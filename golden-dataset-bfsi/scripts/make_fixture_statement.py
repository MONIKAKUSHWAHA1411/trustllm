"""Builds a synthetic HDFC-style statement used as a CI fixture.

This is NOT the corpus generator. It exists so tests never touch real client
data, and to cover banks where no authentic sample was received.
"""

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


TXNS = [
    ("01/04/2025", "OPENING BALANCE",             None,      None,   "112340.00"),
    ("03/04/2025", "UPI/DR/508812/GROCERY",       "2340.00", None,   "110000.00"),
    ("05/04/2025", "NEFT/CR/ACME PVT LTD/SALARY", None, "185000.00", "295000.00"),
    ("09/04/2025", "ACH/DR/HDFC HOME LOAN EMI",  "42500.00", None,   "252500.00"),
    ("12/04/2025", "UPI/DR/771203/FUEL",          "3800.00", None,   "248700.00"),
    ("18/04/2025", "IMPS/DR/RENT PAYMENT",       "35000.00", None,   "213700.00"),
    ("22/04/2025", "UPI/CR/442119/REFUND",        None,   "1250.00", "214950.00"),
    ("28/04/2025", "ATM/DR/CASH WDL",            "10000.00", None,   "204950.00"),
]


def build_base_statement(path: Path) -> None:
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setAuthor("HDFC Bank Ltd")
    c.setProducer("Finacle Statement Engine v11.2")
    c.setCreator("Finacle Statement Engine v11.2")
    c.setTitle("Statement of Account")

    w, h = A4
    c.setFont("Helvetica-Bold", 13)
    c.drawString(20 * mm, h - 22 * mm, "HDFC BANK LIMITED")
    c.setFont("Helvetica", 8.5)
    c.drawString(20 * mm, h - 27 * mm, "Statement of Account  |  01 Apr 2025 to 30 Apr 2025")
    c.drawString(20 * mm, h - 31 * mm, "A/C No: XXXXXXXX4471   IFSC: HDFC0001234   Branch: Gurgaon Sector 44")

    y = h - 42 * mm
    c.setFont("Helvetica-Bold", 8)
    for x, lab in ((20, "Date"), (42, "Narration"), (118, "Debit"), (142, "Credit"), (168, "Balance")):
        c.drawString(x * mm, y, lab)
    c.line(20 * mm, y - 2 * mm, 190 * mm, y - 2 * mm)

    y -= 8 * mm
    c.setFont("Helvetica", 7.5)
    for date, narr, dr, cr, bal in TXNS:
        c.drawString(20 * mm, y, date)
        c.drawString(42 * mm, y, narr)
        if dr:
            c.drawRightString(138 * mm, y, dr)
        if cr:
            c.drawRightString(164 * mm, y, cr)
        c.drawRightString(190 * mm, y, bal)
        y -= 6 * mm

    c.line(20 * mm, y - 1 * mm, 190 * mm, y - 1 * mm)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(20 * mm, y - 6 * mm, "CLOSING BALANCE")
    c.drawRightString(190 * mm, y - 6 * mm, "204950.00")
    c.showPage()
    c.save()



if __name__ == "__main__":
    out = Path("data/raw/fixture_hdfc_apr2025.pdf")
    out.parent.mkdir(parents=True, exist_ok=True)
    build_base_statement(out)
    print(f"wrote {out} ({out.stat().st_size:,} bytes)")
